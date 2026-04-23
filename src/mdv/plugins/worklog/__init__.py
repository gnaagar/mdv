from werkzeug.routing import Rule
from werkzeug.wrappers import Response
from .routes import WorklogRoutes

def setup_plugin(app):
    worklog_file = app.config.get("worklog")
    
    if worklog_file:
        _wl = WorklogRoutes(worklog_file)
        app.on_worklog      = lambda req, **kw: _wl.on_worklog(req)
        app.on_worklog_data = lambda req, **kw: _wl.on_worklog_data(req)
    else:
        app.on_worklog      = lambda req, **kw: Response("Worklog not configured. Pass --worklog <file>", status=404, mimetype="text/plain")
        app.on_worklog_data = app.on_worklog

    app.url_map.add(Rule("/worklog", endpoint="worklog"))
    app.url_map.add(Rule("/worklog/data", endpoint="worklog_data"))
