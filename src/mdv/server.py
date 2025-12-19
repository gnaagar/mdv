#!/usr/bin/env python3

import argparse
import json
import mimetypes
import os
from importlib.resources import files
from pathlib import Path

from mdv.logger import get_logger
from mdv.mdparser import MarkdownParser
from mdv.sv_state import MdViewerState

from jinja2 import Environment, PackageLoader, select_autoescape
from werkzeug.serving import run_simple
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
    parts = [p for p in path.split("/") if p]

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
])


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

class App:
    def __init__(self, config):
        self.url_map = url_map
        self.state = MdViewerState(config)

        # ---- Static files (package-safe) ----
        static_dir = files("mdv").joinpath("static")

        self.wsgi_app = SharedDataMiddleware(
            self.wsgi_app,
            {
                "/static": str(static_dir)
            }
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
        html = env.get_template(template).render(content=content)
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
        return Response(status=302, headers={"Location": "/v"})

    def on_index(self, request):
        self.state.refresh()
        tree = self.state.get_tree()
        tree_md = env.get_template("tree.md").render(
            tree=tree,
            path="v",
            root="/"
        )
        html = env.get_template("viewer.html").render(
            content=MarkdownParser.parse(tree_md)
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
            content=MarkdownParser.parse(tree_md)
        )
        return Response(html, mimetype="text/html")

    # JSON
    def on_dirtree(self, request):
        return Response(
            json.dumps(self.state.get_tree()),
            mimetype="application/json"
        )

    def on_search(self, request):
        query = request.args.get("query")
        result = self.state.search(query)
        return Response(json.dumps(result), mimetype="application/json")

    def on_mdplain(self, request, filename):
        return self.handle_common(filename, template="plain.html", prefix="m")

    def on_view(self, request, filename):
        return self.handle_common(filename, template="viewer.html", prefix="v")

    def on_mdtext(self, request, filename):
        raw_text = self.state.get_content(filename, raw=True)
        return Response(raw_text, mimetype="text/plain")

    # NOTE:
    # on_static REMOVED — handled by SharedDataMiddleware

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
    parser.add_argument("--port", "-p", type=int, default=5000)
    parser.add_argument("--host", "-H", default="localhost")
    args = parser.parse_args()

    app = App(config={"dir": os.getcwd()})
    run_simple(args.host, args.port, app, use_reloader=True)
