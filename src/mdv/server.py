#!/usr/bin/env python3

import argparse
import json
import threading
import webbrowser
from importlib.resources import files
from pathlib import Path
from typing import List, Dict, Any, Optional

from mdv.logger import get_logger
from mdv.mdparser import MarkdownParser
from mdv.sv_state import MdViewerState

from jinja2 import Environment, PackageLoader, select_autoescape
from werkzeug.serving import run_simple, make_server
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware


def get_available_themes() -> List[str]:
    themes_dir = files("mdv").joinpath("static", "themes")
    themes: List[str] = []
    if themes_dir.is_dir():
        for f in sorted(themes_dir.iterdir()):
            if f.suffix == ".css" and f.stem != "base":
                themes.append(f.stem)
    return themes or ["sans"]


# ---------------------------------------------------------
# Jinja environment (package-safe)
# ---------------------------------------------------------

env = Environment(
    loader=PackageLoader("mdv", "templates"), autoescape=select_autoescape()
)

logger = get_logger(__name__)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def get_children(
    tree: List[Dict[str, Any]], path: str
) -> Optional[List[Dict[str, Any]]]:
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

url_map = Map(
    [
        Rule("/", endpoint="home"),
        Rule("/static/<path:filename>", endpoint="static"),  # handled by middleware
        Rule("/_/", endpoint="index"),
        Rule("/_/<path:filename>", endpoint="view"),
        Rule("/d/<doc_id>", endpoint="view_by_id"),
        Rule("/api/tree", endpoint="dirtree"),
        Rule("/api/search", endpoint="search"),
        Rule("/api/themes", endpoint="themes"),
        Rule("/api/render", endpoint="api_render", methods=["POST"]),
        Rule("/live", endpoint="live"),
        Rule("/favicon.ico", endpoint="favicon"),
    ]
)


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------


class App:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.url_map = url_map
        self.config = config
        self.state = MdViewerState(config)
        self.themes = get_available_themes()
        initial = config.get("theme", "sans")
        self.theme = initial if initial in self.themes else "sans"

        # ---- Static files (package-safe) ----
        static_dir = files("mdv").joinpath("static")

        self.wsgi_app = SharedDataMiddleware(
            self.wsgi_app,
            {"/static": str(static_dir)},
            cache_timeout=86400,
        )

    # Dispatcher
    def dispatch(self, request: Request) -> Response | HTTPException:
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            handler = getattr(self, f"on_{endpoint}")
            return handler(request, **values)
        except NotFound:
            return Response("Not found", status=404, mimetype="text/plain")
        except FileNotFoundError as e:
            logger.warning(f"File not found: {e}")
            return Response(f"Not found: {e}", status=404, mimetype="text/plain")
        except HTTPException as e:
            return e
        except Exception:
            logger.exception("Internal server error")
            return Response("Internal server error", status=500, mimetype="text/plain")

    # -----------------------------------------------------
    # Render helpers
    # -----------------------------------------------------

    def render_markdown(self, template: str, content: str) -> Response:
        doc_map = self.state.get_doc_id_map()
        content = MarkdownParser.rewrite_doc_id_links(content, doc_map)
        html = env.get_template(template).render(
            content=content, theme=self.theme, themes=self.themes
        )
        return Response(html, mimetype="text/html")

    def render_tree(self, template: str, prefix: str, filename: str) -> Response:
        tree = get_children(self.state.get_tree(), filename)
        if tree is None:
            return Response("Not found", status=404, mimetype="text/plain")

        tree_md = env.get_template("tree.md").render(
            tree=tree, path=prefix, root="/" + filename
        )
        parsed = MarkdownParser.parse(tree_md)
        return self.render_markdown(template, parsed)

    def render_file(self, template: str, filename: str) -> Response:
        # Always read fresh in lite_mode to avoid caching delays
        md_html = self.state.get_content(filename)
        return self.render_markdown(template, md_html)

    def handle_common(self, filename: str, template: str, prefix: str) -> Response:
        if self.state.is_file(filename):
            return self.render_file(template, filename)
        return self.render_tree(template, prefix, filename)

    # -----------------------------------------------------
    # Handlers
    # -----------------------------------------------------

    def on_home(self, request: Request) -> Response:
        # In lite mode, go directly to the file view
        lite_file = self.config.get("lite_file")
        if lite_file:
            return Response(status=302, headers={"Location": f"/_/{lite_file}"})
        return Response(status=302, headers={"Location": "/_/"})

    def on_index(self, request: Request) -> Response:
        self.state.refresh()
        data = self.state.get_dashboard_data()
        html = env.get_template("dashboard.html").render(
            theme=self.theme, themes=self.themes, **data
        )
        return Response(html, mimetype="text/html")

    # JSON
    def on_dirtree(self, request: Request) -> Response:
        self.state.refresh()
        return Response(json.dumps(self.state.get_tree()), mimetype="application/json")

    def on_search(self, request: Request) -> Response:
        query = request.args.get("query", "")
        types = request.args.get("types")  # comma-separated category filter
        self.state.refresh()
        type_list = (
            [t.strip() for t in types.split(",") if t.strip()] if types else None
        )
        result = self.state.search(query, types=type_list)
        return Response(json.dumps(result), mimetype="application/json")

    def on_themes(self, request: Request) -> Response:
        return Response(json.dumps(self.themes), mimetype="application/json")

    def on_view(self, request: Request, filename: str) -> Response:
        return self.handle_common(filename, template="viewer.html", prefix="_")

    def on_view_by_id(self, request: Request, doc_id: str) -> Response:
        doc_map = self.state.get_doc_id_map()
        if doc_id in doc_map:
            return Response(status=302, headers={"Location": f"/_/{doc_map[doc_id]}"})
        return Response(f"Document with ID '{doc_id}' not found", status=404, mimetype="text/plain")

    def on_api_render(self, request: Request) -> Response:
        raw_md = request.get_data(as_text=True)
        html = MarkdownParser.parse(raw_md)
        doc_map = self.state.get_doc_id_map()
        html = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        return Response(html, mimetype="text/html")

    def on_live(self, request: Request) -> Response:
        html = env.get_template("live.html").render(
            theme=self.theme, themes=self.themes
        )
        return Response(html, mimetype="text/html")

    def on_favicon(self, request: Request) -> Response:
        # Redirect explicit browser requests for /favicon.ico correctly to new internal svg
        return Response(status=302, headers={"Location": "/static/favicon.svg"})

    def on_static(self, request: Request, filename: str) -> Response:
        # Graceful fallback, will usually be intercepted by SharedDataMiddleware successfully
        return Response("Not found", status=404, mimetype="text/plain")

    # -----------------------------------------------------
    # WSGI plumbing
    # -----------------------------------------------------

    def wsgi_app(self, environ: Dict[str, Any], start_response: Any) -> Any:
        request = Request(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> Any:
        return self.wsgi_app(environ, start_response)


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown viewer")
    parser.add_argument(
        "target", nargs="?", default=".", help="Target directory or file to view"
    )
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--host", "-H", default="localhost")
    parser.add_argument(
        "--theme",
        "-t",
        default="sans",
        help="Theme name (e.g., sans, sans-dark)",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        nargs="*",
        default=[],
        help="Additional directory names to ignore (dot-directories are always ignored)",
    )
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    lite_mode = target_path.is_file()

    config = {
        "dir": str(target_path.parent) if lite_mode else str(target_path),
        "theme": args.theme,
        "ignore_dirs": args.ignore,
        "lite_file": target_path.name if lite_mode else None,
    }

    app = App(config=config)

    if lite_mode:
        port = 0
        srv = make_server(args.host, port, app, threaded=True)
        actual_port = srv.port
        url = f"http://{args.host}:{actual_port}/_/{config['lite_file']}"
        print(f"Lite mode: serving {target_path} on {url}")
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        srv.serve_forever()
    else:
        run_simple(args.host, args.port, app, use_reloader=True, threaded=True)
