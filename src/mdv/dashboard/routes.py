"""
Worklog dashboard routes.
Registered onto the main App when --worklog <file> is given.
"""

import json
from pathlib import Path

from mdv.dashboard.parser import parse, to_json


class WorklogRoutes:
    """Mixin-style handler provider; attached to the main App instance."""

    def __init__(self, worklog_path: str):
        self._worklog_path = Path(worklog_path).expanduser().resolve()

    def _get_data(self) -> dict:
        wl = parse(self._worklog_path)
        return to_json(wl)

    def on_worklog(self, request):
        from jinja2 import Environment, PackageLoader, select_autoescape
        from werkzeug.wrappers import Response

        data = self._get_data()
        env = Environment(
            loader=PackageLoader("mdv", "templates"),
            autoescape=select_autoescape(),
        )
        html = env.get_template("worklog.html").render(**data)
        return Response(html, mimetype="text/html")

    def on_worklog_data(self, request):
        from werkzeug.wrappers import Response
        data = self._get_data()
        return Response(json.dumps(data), mimetype="application/json")
