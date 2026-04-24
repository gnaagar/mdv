import os
import json
from werkzeug.wrappers import Response
from werkzeug.routing import Rule

from mdv.server import env
from .db import get_csv_db
from mdv.logger import get_logger

logger = get_logger(__name__)

def setup_plugin(app):
    original_on_view = app.on_view
    
    def on_view(request, filename):
        if app.config.get("csv_mode"):
            workspace_name = os.path.basename(app.state._root_dir) if hasattr(app.state, '_root_dir') else "Workspace"
            html = env.get_template("csvviewer.html").render(
                theme=app.theme, 
                filename=filename,
                workspace_name=workspace_name
            )
            return Response(html, mimetype="text/html")
        else:
            return original_on_view(request, filename)
            
    setattr(app, 'on_view', on_view)
    
    app.url_map.add(Rule("/api/csv/query", endpoint="csv_query", methods=["POST"]))
    
    def on_csv_query(request):
        try:
            payload = json.loads(request.get_data(as_text=True))
            filename = payload.get("filename")
            query = payload.get("query", "SELECT * FROM data LIMIT 10")
            
            q_upper = query.strip().upper()
            if not q_upper.startswith("SELECT") and not q_upper.startswith("WITH") and not q_upper.startswith("EXPLAIN"):
                raise ValueError("Only SELECT or WITH queries are allowed.")
                
            import re
            forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "ATTACH"}
            tokens = set(re.findall(r'[A-Z]+', q_upper))
            if tokens.intersection(forbidden):
                raise ValueError(f"Query blocked for security. Forbidden keywords used: {', '.join(tokens.intersection(forbidden))}")
            
            full_path = os.path.join(app.state._root_dir, os.path.normpath(filename))
            
            conn = get_csv_db(full_path)
            cursor = conn.cursor()
            cursor.execute(query)
            
            rows = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description] if cursor.description else []
            data = [dict(row) for row in rows]
            
            return Response(
                json.dumps({"success": True, "headers": headers, "data": data}), 
                mimetype="application/json"
            )
        except Exception as e:
            logger.error(f"CSV Query error: {e}")
            return Response(
                json.dumps({"success": False, "error": str(e)}), 
                mimetype="application/json", 
                status=400
            )
            
    setattr(app, 'on_csv_query', on_csv_query)
