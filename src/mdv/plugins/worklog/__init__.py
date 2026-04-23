from werkzeug.routing import Rule
from werkzeug.wrappers import Response
from .routes import WorklogRoutes

def setup_plugin(app):
    _wl = WorklogRoutes(state=app.state)

    app.on_worklog      = lambda req, **kw: _wl.on_worklog(req)
    app.on_worklog_data = lambda req, **kw: _wl.on_worklog_data(req)

    app.url_map.add(Rule("/worklog", endpoint="worklog"))
    app.url_map.add(Rule("/worklog/data", endpoint="worklog_data"))
