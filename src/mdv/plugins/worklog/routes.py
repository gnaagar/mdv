"""
Worklog dashboard routes.
Registered onto the main App when --worklog <file> is given.
"""

import json
from pathlib import Path

from mdv.plugins.worklog.parser import parse, to_json


class WorklogRoutes:
    """Mixin-style handler provider; attached to the main App instance."""

    def __init__(self, state=None):
        self._state = state

    def _find_worklog(self):
        if self._state:
            for node in list(self._state._node_map.values()):
                raw = self._state.get_content(node.id, raw=True)
                if raw and raw.startswith("<!-- worklog=true"):
                    import os
                    return Path(os.path.join(self._state._root_dir, node.id)).resolve()
        return None

    def _get_data(self) -> dict:
        target = self._find_worklog()
        if not target:
            return {}
        wl = parse(target)
        return to_json(wl)

    def on_worklog(self, request):
        from jinja2 import Environment, PackageLoader, select_autoescape
        from werkzeug.wrappers import Response

        target = self._find_worklog()
        if not target:
            return Response("Worklog not found. Create a markdown file and start it exactly with '<!-- worklog=true -->'.", status=404, mimetype="text/plain")

        data = self._get_data()
        env = Environment(
            loader=PackageLoader("mdv", "templates"),
            autoescape=select_autoescape(),
        )
        html = env.get_template("worklog.html").render(**data)
        return Response(html, mimetype="text/html")

    def on_worklog_data(self, request):
        from werkzeug.wrappers import Response
        target = self._find_worklog()
        if not target:
            return Response("{}", mimetype="application/json")
        data = self._get_data()
        return Response(json.dumps(data), mimetype="application/json")
