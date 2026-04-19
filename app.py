from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from routes.autenticar import autenticar_route
from routes.home import home_route
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta_para_dev")
BASE_DIR = Path(__file__).resolve().parent

app.register_blueprint(home_route)
app.register_blueprint(autenticar_route)

MAP_DIR = BASE_DIR / "Server_py" / "public" / "map"
DB_MANAGER = None

try:
    from Server_py.core.config import ServerConfig
    from Server_py.core.database import DatabaseManager

    server_cfg = ServerConfig()
    DB_MANAGER = DatabaseManager(server_cfg.db_path, merge_distance_meters=server_cfg.merge_distance_meters)
except Exception as e:
    print(f"[App] Mapa/API indisponivel: {e}")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(BASE_DIR / "templates" / "css", filename)


@app.route("/server-map/")
def server_map_index():
    return send_from_directory(MAP_DIR, "index.html")


@app.route("/server-map/<path:filename>")
def server_map_assets(filename):
    return send_from_directory(MAP_DIR, filename)


@app.get("/api/categorias")
def api_categorias():
    if DB_MANAGER is None:
        return jsonify([])
    since = request.args.get("since")
    try:
        return jsonify(DB_MANAGER.list_categories(since=since))
    except Exception:
        return jsonify([]), 503


@app.get("/api/pontos")
def api_pontos():
    if DB_MANAGER is None:
        return jsonify({"meta": {"has_more": False}, "data": []})

    try:
        limit = int(request.args.get("limit", 1000))
        offset = int(request.args.get("offset", 0))
        since = request.args.get("since")
    except ValueError:
        return jsonify({"meta": {"has_more": False}, "data": []}), 400

    try:
        return jsonify(DB_MANAGER.list_points_api(limit=max(1, limit), offset=max(0, offset), since=since))
    except Exception:
        return jsonify({"meta": {"has_more": False}, "data": []}), 503

if __name__ == "__main__":
    app.run(debug=True)