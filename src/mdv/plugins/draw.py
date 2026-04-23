from werkzeug.wrappers import Response
from werkzeug.routing import Rule
from mdv.server import env

def setup_plugin(app):
    def on_draw(request):
        html = env.get_template("draw.html").render(theme=app.theme)
        return Response(html, mimetype="text/html")
        
    setattr(app, 'on_draw', on_draw)
    app.url_map.add(Rule("/draw", endpoint="draw"))

