from __future__ import annotations

import sys
import json
from pathlib import Path

from flask import Flask, jsonify, request, redirect, send_from_directory, render_template, make_response, session
from routes.autenticar import autenticar_route
from routes.home import home_route
from routes.api_routes import api_route
from routes.relatos import relatos_route
from routes.admin import admin_route

import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import ServerConfig
from core.database import DatabaseManager
from core.sync_service import WeeklySyncService
from core.cache_manager import CacheManager
from core.scheduled_tasks import task_manager


def create_app(fast_mode: bool = False) -> Flask:
    config = ServerConfig()
    db = DatabaseManager(config.db_path)
    
    db_file_exists = Path(config.db_path).exists()
    sync_service = WeeklySyncService(
        db_manager=db,
        interval_days=1,
        check_interval_seconds=86400,
    )
    cache_manager = CacheManager(Path(config.db_path).parent / "cache")

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta_para_dev")
    app.config["SERVER_CONFIG"] = config
    app.config["DB_MANAGER"] = db
    app.config["SYNC_SERVICE"] = sync_service
    app.config["CACHE_MANAGER"] = cache_manager
    
    # Iniciar o gestor de tarefas agendadas (verifica pontos alterados)
    task_manager.iniciar()
    print("[App] Gestor de tarefas agendadas iniciado", flush=True)

    # Registra blueprints de autenticação
    app.register_blueprint(home_route)
    app.register_blueprint(autenticar_route)
    app.register_blueprint(api_route)
    app.register_blueprint(admin_route)
    app.register_blueprint(relatos_route)

    # Caminho da pasta de recursos do mapa
    static_folder = PROJECT_ROOT / "templates" / "Map"
    static_folder.mkdir(parents=True, exist_ok=True)

    data_folder = static_folder / "data"
    data_folder.mkdir(parents=True, exist_ok=True)
    # Inicializa dados
    _init_data(db, sync_service, db_file_exists, data_folder, fast_mode)
    
    # Registra rotas
    _register_routes(app, static_folder)

    return app


def _init_data(db, sync_service, db_file_exists, data_folder, fast_mode: bool = False):
    sources = ["overpass", "dadosabertos", "eureciclo"]
    
    if fast_mode:
        print("[App] Modo FAST ativado - carregando apenas de JSONs filtrados locais", flush=True)
        if db.count_points() == 0:
            _load_from_filtered_jsons(db)
        else:
            print(f"[App] Banco já tem {db.count_points()} pontos", flush=True)
    else:
        if not db_file_exists or db.count_points() == 0:
            print("[App] Sincronizando dados inicialmente...", flush=True)
            try:
                sync_service.run_sync(force=True)
                print("[App] Sincronização concluída", flush=True)
            except Exception as e:
                print(f"[App] Erro na sincronização: {e}", flush=True)
                print("[App] Tentando carregar de JSONs filtrados locais...", flush=True)
                _load_from_filtered_jsons(db)
        
        print("[App] Status de sincronizações:", flush=True)
        failed = []
        for source in sources:
            state = db.get_sync_state(source)
            status = state.get("last_status", "unknown") if state else "unknown"
            print(f"[App]   {source}: {status}", flush=True)
            if status == "error":
                failed.append(source)
        
        if failed:
            print(f"[App] Tentando retry em {len(failed)} fonte(s)...", flush=True)
            try:
                sync_service.run_sync(force=True)
                print("[App] Retry concluído", flush=True)
            except Exception as e:
                print(f"[App] Erro no retry: {e}", flush=True)
    
    print("[App] Garantindo snapshot.json...", flush=True)
    try:
        snapshot_path = data_folder / "snapshot.json"
        if not snapshot_path.exists() or snapshot_path.stat().st_size == 0:
            snapshot = db.export_snapshot()
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            print(f"[App] Snapshot: {len(snapshot['categories'])} categorias, {len(snapshot['points'])} pontos")
    except Exception as e:
        print(f"[App] Erro ao criar snapshot: {e}", flush=True)


def _load_from_filtered_jsons(db):
    sources = ["overpass", "dadosabertos", "eureciclo"]
    
    for source in sources:
        filtered_path = PROJECT_ROOT / "api" / source / "data" / f"{source}_filtered.json"
        
        if not filtered_path.exists():
            print(f"[App] Ficheiro {source}_filtered.json não encontrado em {filtered_path}", flush=True)
            continue
        
        try:
            with open(filtered_path, "r", encoding="utf-8") as f:
                points = json.load(f)
            
            if not isinstance(points, list):
                print(f"[App] Aviso: {source}_filtered.json não é uma lista válida", flush=True)
                continue
            
            if not points:
                print(f"[App] {source}_filtered.json está vazio", flush=True)
                continue
            
            # Inserir pontos no banco
            inserted = db.insert_points(points)
            print(f"[App] Carregados {inserted} pontos de {source}_filtered.json", flush=True)
            
            # Marcar fonte como sincronizada
            db.set_sync_state(source, "success", None)
            
        except Exception as e:
            print(f"[App] Erro ao carregar {source}_filtered.json: {e}", flush=True)

def _register_routes(app, static_folder):
    @app.get("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(PROJECT_ROOT / "templates" / "css", filename)
    
    @app.get("/imagens/<path:filename>")
    def serve_imagens(filename):
        return send_from_directory(PROJECT_ROOT / "templates" / "imagens", filename)
    
    @app.get("/404")
    def page_404():
        return render_template("404.html"), 404
    
    @app.get("/map/")
    def serve_map_index():
        return send_from_directory(static_folder, "index.html")
    
    @app.get("/map/<path:filename>")
    def serve_map_assets(filename):
        return send_from_directory(static_folder, filename)
    
    @app.errorhandler(404)
    def page_not_found(error):
        return redirect("/404")

# Detectar modo fast e criar app apenas se main
if __name__ == "__main__":
    fast_mode = "-fast" in sys.argv
    if fast_mode:
        sys.argv.remove("-fast")
    
    app = create_app(fast_mode=fast_mode)
    cfg = app.config["SERVER_CONFIG"]
    try:
        app.run(host=cfg.host, port=cfg.port, debug=cfg.debug)
    except KeyboardInterrupt:
        print("\n[App] Encerrando...", flush=True)
    finally:
        print("[App] Encerrado", flush=True)
else:
    app = create_app(fast_mode=False)