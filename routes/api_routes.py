from flask import Blueprint, jsonify, request, make_response

api_route = Blueprint("api", __name__, url_prefix="/api")


@api_route.get("/sync/status")
def api_sync_status():
    db = request.app.config["DB_MANAGER"]
    all_sources = ["overpass", "dadosabertos", "eureciclo"]
    status_map = {}
    for source in all_sources:
        state = db.get_sync_state(source)
        status_map[source] = {
            "status": state.get("last_status", "unknown") if state else "unknown",
            "last_sync": state.get("last_sync_at") if state else None,
        }
    return jsonify({"sources": status_map})


@api_route.get("/categorias")
def api_categorias():
    db = request.app.config["DB_MANAGER"]
    since = request.args.get("since")
    try:
        data = db.list_categories(since=since)
        return jsonify(data)
    except Exception as e:
        print(f"[API] Erro categorias: {e}", flush=True)
        return jsonify([]), 503


@api_route.get("/cache-info")
def api_cache_info():
    """Retorna timestamp de última atualização do cache"""
    db = request.app.config["DB_MANAGER"]
    try:
        last_update = db.get_last_update_time()
        response = make_response("", 204)
        if last_update:
            response.headers['Last-Modified'] = last_update.strftime("%a, %d %b %Y %H:%M:%S GMT")
        return response
    except Exception as e:
        print(f"[API] Erro cache-info: {e}", flush=True)
        return "", 503


@api_route.get("/pontos")
def api_pontos():
    db = request.app.config["DB_MANAGER"]
    try:
        limit = int(request.args.get("limit", 1000))
        offset = int(request.args.get("offset", 0))
        since = request.args.get("since")
    except ValueError:
        return jsonify({"meta": {"has_more": False}, "data": []}), 400

    limit = max(1, limit)
    offset = max(0, offset)

    try:
        payload = db.list_points_api(limit=limit, offset=offset, since=since)
        return jsonify(payload)
    except Exception as e:
        print(f"[API] Erro pontos: {e}", flush=True)
        return jsonify({"meta": {"has_more": False}, "data": []}), 503
