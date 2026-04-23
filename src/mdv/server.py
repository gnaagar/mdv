#!/usr/bin/env python3

import argparse
import json
import mimetypes
import os
import threading
import webbrowser
from importlib.resources import files
from pathlib import Path

from mdv.logger import get_logger
from mdv.mdparser import MarkdownParser
from mdv.sv_state import MdViewerState
from mdv.plugins import load_plugins

from jinja2 import Environment, PackageLoader, select_autoescape
from werkzeug.serving import run_simple, make_server
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware


# ---------------------------------------------------------
# Jinja environment (package-safe)
# ---------------------------------------------------------

env = Environment(
    loader=PackageLoader("mdv", "templates"),
    autoescape=select_autoescape()
)

logger = get_logger(__name__)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_children(tree, path):
    parts = [p for p in path.split('/') if p]

    if not parts:
        return tree

    nodes = tree
    for part in parts:
        found = None
        for node in nodes:
            if node["type"] == "directory" and node["name"] == part:
                found = node
                break

        if not found:
            return None

        nodes = found.get("children", [])

    return nodes or []


# ---------------------------------------------------------
# URL map
# ---------------------------------------------------------

url_map = Map([
    Rule("/", endpoint="home"),
    Rule("/static/<path:filename>", endpoint="static"),  # handled by middleware
    Rule("/v/", endpoint="index"),
    Rule("/v/<path:filename>", endpoint="view"),
    Rule("/m/", endpoint="index_mdplain"),
    Rule("/m/<path:filename>", endpoint="mdplain"),
    Rule("/t/<path:filename>", endpoint="mdtext"),
    Rule("/api/tree", endpoint="dirtree"),
    Rule("/api/search", endpoint="search"),
    Rule("/api/render", endpoint="api_render", methods=["POST"]),
    Rule("/live", endpoint="live"),
])


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

class App:
    def __init__(self, config):
        self.url_map = url_map
        self.config = config
        self.state = MdViewerState(config)
        self.theme = config.get("theme", "light")

        # Load plugins
        load_plugins(self, config.get("plugins"))

        # ---- Static files (package-safe) ----
        static_dir = files("mdv").joinpath("static")

        self.wsgi_app = SharedDataMiddleware(
            self.wsgi_app,
            {
                "/static": str(static_dir)
            },
            cache_timeout=86400,
        )

    # Dispatcher
    def dispatch(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            handler = getattr(self, f"on_{endpoint}")
            return handler(request, **values)
        except NotFound:
            return Response("Not found", status=404, mimetype="text/plain")
        except HTTPException as e:
            return e

    # -----------------------------------------------------
    # Render helpers
    # -----------------------------------------------------

    def render_markdown(self, template, content):
        html = env.get_template(template).render(content=content, theme=self.theme)
        return Response(html, mimetype="text/html")

    def render_tree(self, template, prefix, filename):
        tree = get_children(self.state.get_tree(), filename)
        if tree is None:
            return Response("Not found", status=404, mimetype="text/plain")

        tree_md = env.get_template("tree.md").render(
            tree=tree,
            path=prefix,
            root="/" + filename
        )
        parsed = MarkdownParser.parse(tree_md)
        return self.render_markdown(template, parsed)

    def render_file(self, template, filename):
        # Always read fresh in lite_mode to avoid caching delays
        md_html = self.state.get_content(filename)
        return self.render_markdown(template, md_html)

    def handle_common(self, filename, template, prefix):
        if self.state.is_file(filename):
            return self.render_file(template, filename)
        return self.render_tree(template, prefix, filename)

    # -----------------------------------------------------
    # Handlers
    # -----------------------------------------------------

    def on_home(self, request):
        # In lite mode, go directly to the file view
        lite_file = self.config.get("lite_file")
        if lite_file:
            return Response(status=302, headers={"Location": f"/v/{lite_file}"})
        return Response(status=302, headers={"Location": "/v"})

    def on_index(self, request):
        self.state.refresh()
        data = self.state.get_dashboard_data()
        html = env.get_template("dashboard.html").render(
            theme=self.theme,
            **data
        )
        return Response(html, mimetype="text/html")

    def on_index_mdplain(self, request):
        self.state.refresh()
        tree = self.state.get_tree()
        tree_md = env.get_template("tree.md").render(
            tree=tree,
            path="m",
            root="/"
        )
        html = env.get_template("plain.html").render(
            content=MarkdownParser.parse(tree_md),
            theme=self.theme
        )
        return Response(html, mimetype="text/html")

    # JSON
    def on_dirtree(self, request):
        self.state.refresh()
        return Response(
            json.dumps(self.state.get_tree()),
            mimetype="application/json"
        )

    def on_search(self, request):
        query = request.args.get("query")
        types = request.args.get("types")  # comma-separated category filter
        self.state.refresh()
        type_list = [t.strip() for t in types.split(",") if t.strip()] if types else None
        result = self.state.search(query, types=type_list)
        return Response(json.dumps(result), mimetype="application/json")

    def on_mdplain(self, request, filename):
        return self.handle_common(filename, template="plain.html", prefix="m")

    def on_view(self, request, filename):
        return self.handle_common(filename, template="viewer.html", prefix="v")

    def on_mdtext(self, request, filename):
        raw_text = self.state.get_content(filename, raw=True)
        return Response(raw_text, mimetype="text/plain")

    def on_api_render(self, request):
        raw_md = request.get_data(as_text=True)
        html = MarkdownParser.parse(raw_md)
        return Response(html, mimetype="text/html")

    def on_live(self, request):
        html = env.get_template("live.html").render(theme=self.theme)
        return Response(html, mimetype="text/html")

    # -----------------------------------------------------
    # WSGI plumbing
    # -----------------------------------------------------

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Markdown viewer")
    parser.add_argument("target", nargs="?", default=".", help="Target directory or file to view")
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--host", "-H", default="localhost")
    parser.add_argument("--theme", "-t", choices=["light", "dark"], default="light", help="Color theme (light or dark)")
    parser.add_argument("--ignore", "-i", nargs="*", default=[], help="Additional directory names to ignore (dot-directories are always ignored)")
    parser.add_argument("--worklog", "-w", default=None, help="Path to worklog markdown file (enables /worklog dashboard)")
    parser.add_argument("--plugins", default="draw,worklog", help="Comma-separated list of plugins to load")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    lite_mode = target_path.is_file()

    config = {
        "dir": str(target_path.parent) if lite_mode else str(target_path),
        "theme": args.theme,
        "ignore_dirs": args.ignore,
        "worklog": args.worklog,
        "plugins": args.plugins,
        "lite_file": target_path.name if lite_mode else None
    }

    app = App(config=config)

    if lite_mode:
        port = 0
        srv = make_server(args.host, port, app, threaded=True)
        actual_port = srv.port
        url = f"http://{args.host}:{actual_port}/v/{config['lite_file']}"
        print(f"Lite mode: serving {target_path} on {url}")
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        srv.serve_forever()
    else:
        run_simple(args.host, args.port, app, use_reloader=True, threaded=True)
