from __future__ import annotations

import os
from dataclasses import dataclass

# Bbox para fetch do Overpass - abrange todo Portugal (Continental + Açores + Madeira)
# Formato: (south, west, north, east)
PORTUGAL_BBOX = (30.03, -31.27, 42.15, -6.19)


@dataclass
class ServerConfig:
    host: str = os.getenv("SERVER_PY_HOST", "127.0.0.1")
    port: int = int(os.getenv("SERVER_PY_PORT", "5050"))
    debug: bool = os.getenv("SERVER_PY_DEBUG", "false").lower() == "true"
    db_path: str = os.getenv("SERVER_PY_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "server.db"))
    sync_interval_days: int = int(os.getenv("SERVER_PY_SYNC_DAYS", "7"))
    sync_check_seconds: int = int(os.getenv("SERVER_PY_SYNC_CHECK_SECONDS", "3600"))
    merge_distance_meters: float = float(os.getenv("SERVER_PY_MERGE_DISTANCE_METERS", "5"))