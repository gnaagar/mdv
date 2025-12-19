#!/usr/bin/env python3

import os
import argparse
import json
import mimetypes
from logger import get_logger
from mdparser import MarkdownParser
from sv_state import MdViewerState
from jinja2 import Environment, FileSystemLoader
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound

env = Environment(loader=FileSystemLoader("templates"))
logger = get_logger(__name__)


def get_children(tree, path):
    # split path into parts, skip empty parts
    parts = [p for p in path.split("/") if p]

    # if path is empty, the "children" are the root nodes
    if not parts:
        return tree

    # start from the virtual root
    nodes = tree

    for part in parts:
        found = None
        # look for the directory with the matching name
        for node in nodes:
            if node["type"] == "directory" and node["name"] == part:
                found = node
                break

        if not found:
            return None   # directory doesn't exist

        nodes = found.get("children", [])

    return nodes or []


# ---------------------------------------------------------
# URL map
# ---------------------------------------------------------

url_map = Map([
    Rule("/", endpoint="home"),
    Rule("/static/<path:filename>", endpoint="static"),
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
        self.static_dir = "static"
        self.state = MdViewerState(config)

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

    # Helpers
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

    # HANDLERS
    def on_home(self, request):
        return Response(status=302, headers={"Location": "/v"})

    # HTML
    def on_index(self, request):
        self.state.refresh()
        tree = self.state.get_tree()
        tree_md = env.get_template("tree.md").render(tree=tree,path="v",root="/")
        html = env.get_template("viewer.html").render(content=MarkdownParser.parse(tree_md))
        return Response(html, mimetype="text/html")

    def on_index_mdplain(self, request):
        self.state.refresh()
        tree = self.state.get_tree()
        tree_md = env.get_template("tree.md").render(tree=tree,path="m",root="/")
        html = env.get_template("plain.html").render(content=MarkdownParser.parse(tree_md))
        return Response(html, mimetype="text/html")

    # JSON
    def on_dirtree(self, request):
        tree = self.state.get_tree()
        return Response(json.dumps(tree), mimetype="application/json")
    
    def on_search(self, request):
        # Access query parameters
        query = request.args.get("query", None)  # default if missing
        result = self.state.search(query)
        return Response(json.dumps(result), mimetype="application/json")

    def on_mdplain(self, request, filename):
        return self.handle_common(filename, template="plain.html", prefix="m")

    def on_view(self, request, filename):
        return self.handle_common(filename, template="viewer.html", prefix="v")

    # Plain markdown
    def on_mdtext(self, request, filename):
        raw_text = self.state.get_content(filename,raw=True)
        return Response(raw_text, mimetype="text/plain")

    # Static file
    def on_static(self, request, filename):
        path = os.path.join(self.static_dir, filename)
        if not os.path.isfile(path):
            return Response("Not found", status=404, mimetype="text/plain")
        
        with open(path, "rb") as f:
            data = f.read()
        
        # Guess MIME type
        mimetype, _ = mimetypes.guess_type(path)
        if not mimetype:
            mimetype = "application/octet-stream"
        
        return Response(data, mimetype=mimetype)

    # WSGI wrapper
    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

    # Callable wrapper
    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Markdown viewer")
    parser.add_argument("--dir", "-d", required=True, help="Directory to serve")
    parser.add_argument("--port", "-p", type=int,default=5000, help="Port to serve on")
    parser.add_argument("--host", "-H", default="localhost", help="Host to bind to")
    args = parser.parse_args()
    app = App(config={'dir':args.dir})
    run_simple(args.host, args.port, app, use_reloader=True)

if __name__ == "__main__":
    main()
