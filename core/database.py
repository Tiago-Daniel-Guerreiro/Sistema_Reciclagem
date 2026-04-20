from __future__ import annotations
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from core.category_catalog import category_metadata, known_categories
from core.point_filters import remove_points_without_categories_sql, remove_points_outside_portugal_sql

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

class DatabaseManager:
    def __init__(self, db_path: str, merge_distance_meters: float = 50.0):
        self.db_path = os.path.abspath(db_path)
        self.merge_distance_meters = max(float(merge_distance_meters), 0.0)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        with self.connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fontes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ponto_merges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL
                )
                """
            )
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pontos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    fonte_id INTEGER NOT NULL,
                    source_id TEXT,
                    is_removed INTEGER NOT NULL DEFAULT 0,
                    merged_into_id INTEGER,
                    nome TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (fonte_id) REFERENCES fontes(id),
                    FOREIGN KEY (merged_into_id) REFERENCES ponto_merges(id)
                )
                """
            )
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY,
                    nome_exibicao TEXT NOT NULL DEFAULT '',
                    eletronico INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ponto_categorias (
                    ponto_id INTEGER NOT NULL,
                    categoria_id INTEGER NOT NULL,
                    PRIMARY KEY (ponto_id, categoria_id),
                    FOREIGN KEY (ponto_id) REFERENCES pontos(id) ON DELETE CASCADE,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                )
                """
            )
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (
                    source TEXT PRIMARY KEY,
                    last_sync_at TEXT,
                    last_status TEXT,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            
            # Tabelas de autenticação e usuários
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS utilizadores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK (tipo IN ('admin','utilizador')),
                    regiao TEXT NOT NULL,
                    receber_notificacoes INTEGER NOT NULL DEFAULT 1 CHECK (receber_notificacoes IN (0,1)),
                    email_verificado INTEGER NOT NULL DEFAULT 0,
                    codigo_verificacao TEXT,
                    codigo_verificacao_criado_em TEXT,
                    data_registo DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Migração: adicionar coluna se não existir (para instâncias antigas)
            try:
                conn.execute("ALTER TABLE utilizadores ADD COLUMN codigo_verificacao_criado_em TEXT")
            except Exception:
                pass  # Coluna já existe
                        
            now = now_iso()
            for cat in known_categories():
                conn.execute(
                    """
                    INSERT INTO categorias (id, nome_exibicao, eletronico, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        nome_exibicao = excluded.nome_exibicao,
                        eletronico = excluded.eletronico,
                        updated_at = excluded.updated_at
                    """,
                    (
                        int(cat["id"]),
                        cat["display_name"],
                        1 if cat["eletronico"] else 0,
                        now,
                        now,
                    ),
                )
            
            remove_points_without_categories_sql(conn, now)
            remove_points_outside_portugal_sql(conn, now)
            conn.execute("PRAGMA foreign_keys = ON")

    def _get_or_create_fonte_id(self, conn: sqlite3.Connection, fonte_nome: str, now: str) -> int:
        row = conn.execute("SELECT id FROM fontes WHERE nome = ?", (fonte_nome,)).fetchone()
        if row:
            return int(row["id"])
        
        cursor = conn.cursor()
        cursor.execute("INSERT INTO fontes (nome, created_at) VALUES (?, ?)", (fonte_nome, now))
        last_id = cursor.lastrowid
        return int(last_id) if last_id is not None else 1

    def _distance_meters(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        avg_lat_rad = math.radians((lat1 + lat2) / 2.0)
        lat_m = (lat2 - lat1) * 111_320.0
        lng_m = (lng2 - lng1) * 111_320.0 * math.cos(avg_lat_rad)
        return math.sqrt(lat_m * lat_m + lng_m * lng_m)

    def apply_point_merges(self, conn: sqlite3.Connection) -> dict:
        if self.merge_distance_meters <= 0:
            return {"pairs": 0, "removed": 0}

        now = now_iso()
        
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH candidates AS (
                SELECT p1.id AS p1_id,  p2.id AS p2_id,
                       (CAST(p1.lat - p2.lat AS REAL) * 111320) * 
                       (CAST(p1.lat - p2.lat AS REAL) * 111320) +
                       (CAST((p1.lng - p2.lng) * COS(p1.lat * 3.14159 / 180) * 111320 AS REAL)) *
                       (CAST((p1.lng - p2.lng) * COS(p1.lat * 3.14159 / 180) * 111320 AS REAL)) as dist_sq
                FROM pontos p1, pontos p2
                WHERE p1.is_removed = 0 AND p2.is_removed = 0 AND p1.id < p2.id
            ),
            within_distance AS (
                SELECT p1_id, p2_id FROM candidates 
                WHERE SQRT(dist_sq) <= ?
            ),
            merge_groups AS (
                SELECT p1_id as pid, p2_id as group_id FROM within_distance
                UNION ALL
                SELECT p2_id, p2_id FROM within_distance
                UNION ALL
                SELECT id, id FROM pontos WHERE is_removed = 0
            )
            INSERT INTO ponto_merges (created_at) VALUES (?)
            """,
            (self.merge_distance_meters, now),
        )
        
        merge_record_id = cursor.lastrowid
        
        conn.execute(
            """
            WITH merge_groups AS (
                SELECT p1.id AS canonical,
                       GROUP_CONCAT(p2.id, ',') AS merged_ids,
                       AVG(p1.lat) as avg_lat,
                       AVG(p1.lng) as avg_lng
                FROM pontos p1
                JOIN pontos p2 ON (
                    (p2.lat BETWEEN p1.lat - ? AND p1.lat + ?
                     AND p2.lng BETWEEN p1.lng - ? AND p1.lng + ?)
                    AND p1.is_removed = 0 AND p2.is_removed = 0
                )
                WHERE p1.id <= p2.id
                GROUP BY p1.id
                HAVING COUNT(*) > 1
            )
            UPDATE pontos
            SET lat = (SELECT AVG(lat) FROM pontos WHERE id IN (
                       SELECT canonical FROM merge_groups)),
                lng = (SELECT AVG(lng) FROM pontos WHERE id IN (
                       SELECT canonical FROM merge_groups)),
                merged_into_id = ?,
                updated_at = ?
            WHERE id IN (SELECT canonical FROM merge_groups)
            """,
            (self.merge_distance_meters / 111_320.0, self.merge_distance_meters / 111_320.0,
             self.merge_distance_meters / 80_000.0, self.merge_distance_meters / 80_000.0,
             merge_record_id, now),
        )
        
        merged_count = conn.execute(
            """
            UPDATE pontos
            SET is_removed = 1, merged_into_id = ?, updated_at = ?
            WHERE id != (
                SELECT MIN(id) FROM pontos WHERE merged_into_id = ?
            ) AND merged_into_id = ?
            """,
            (merge_record_id, now, merge_record_id, merge_record_id),
        ).rowcount
        
        return {
            "pairs": merged_count,
            "removed": merged_count,
        }

    def insert_points(self, points: list[dict]) -> int:
        created = 0
        now = now_iso()

        with self.connection() as conn:            
            for point in points:
                ponto_nome = point.get("nome", "Ponto de Recolha")
                categorias = point.get("categorias", [])
                fontes = point.get("fontes", [])
                fonte_principal = fontes[0] if fontes else "desconhecida"
                fonte_value = self._get_or_create_fonte_id(conn, fonte_principal, now)
                
                lat = float(point["lat"])
                lng = float(point["lng"])
                
                # Check dedup: same source + coords = skip
                existing = conn.execute(
                    "SELECT id FROM pontos WHERE source_id = ? AND ABS(lat - ?) < 0.0001 AND ABS(lng - ?) < 0.0001 LIMIT 1",
                    (fonte_principal, lat, lng)
                ).fetchone()
                
                if existing:
                    continue  # Skip duplicate

                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO pontos (lat, lng, fonte_id, source_id, is_removed, nome, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
                    (lat, lng, fonte_value, fonte_principal, ponto_nome, now, now),
                )
                ponto_id = cursor.lastrowid
                created += 1

                for cat_key in categorias:
                    meta = category_metadata(cat_key)
                    cat_id = int(meta["id"]) if meta.get("id") is not None else 999
                    
                    conn.execute(
                        "INSERT OR IGNORE INTO ponto_categorias (ponto_id, categoria_id) VALUES (?, ?)",
                        (ponto_id, cat_id),
                    )

        return created

    def get_sync_state(self, source: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM sync_state WHERE source = ?", (source,)).fetchone()
        return dict(row) if row else None

    def set_sync_state(self, source: str, status: str, error: str | None = None):
        now = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO sync_state (source, last_sync_at, last_status, last_error, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    last_sync_at = excluded.last_sync_at,
                    last_status = excluded.last_status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (source, now, status, error, now),
            )

    def get_last_change_timestamp(self) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT MAX(ts) as last_ts FROM (SELECT MAX(updated_at) as ts FROM pontos UNION ALL SELECT MAX(updated_at) as ts FROM categorias)"
            ).fetchone()
        return row["last_ts"] if row else None

    def get_sync_check(self, since: str | None = None) -> dict:
        with self.connection() as conn:
            if since:
                mod_cat_row = conn.execute("SELECT COUNT(*) as c FROM categorias WHERE updated_at > ?", (since,)).fetchone()
                mod_pts_row = conn.execute("SELECT COUNT(*) as c FROM pontos WHERE is_removed = 0 AND updated_at > ?", (since,)).fetchone()
                categories_modified = int(mod_cat_row["c"] if mod_cat_row else 0)
                points_modified = int(mod_pts_row["c"] if mod_pts_row else 0)
            else:
                categories_modified = int(conn.execute("SELECT COUNT(*) as c FROM categorias").fetchone()["c"])
                points_modified = int(conn.execute("SELECT COUNT(*) as c FROM pontos WHERE is_removed = 0").fetchone()["c"])

        return {
            "categories_modified": categories_modified,
            "points_modified": points_modified,
            "last_sync": self.get_last_change_timestamp(),
        }

    def list_categories(self, since: str | None = None) -> list[dict]:
        params = []
        where_clause = ""
        if since:
            where_clause = "WHERE c.updated_at > ?"
            params.append(since)

        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT c.id,
                       c.nome_exibicao,
                       c.eletronico,
                       COUNT(DISTINCT pc.ponto_id) as pontos
                FROM categorias c
                LEFT JOIN ponto_categorias pc ON pc.categoria_id = c.id
                LEFT JOIN pontos p ON p.id = pc.ponto_id
                {where_clause}
                GROUP BY c.id
                HAVING COUNT(DISTINCT CASE WHEN p.is_removed = 0 THEN pc.ponto_id END) > 0
                ORDER BY pontos DESC, c.id ASC
                """,
                tuple(params),
            ).fetchall()

            return [
                {
                    "id": int(row["id"]),
                    "nome": row["nome_exibicao"],
                    "pontos": int(row["pontos"] or 0),
                    "eletronico": bool(int(row["eletronico"] or 0)),
                }
                for row in rows
            ]

    def list_points_api(self, limit: int = 1000, offset: int = 0, since: str | None = None) -> dict:
        with self.connection() as conn:
            where_clause = f"""
            WHERE p.is_removed = 0 AND (
                p.merged_into_id IS NULL 
                OR p.id IN (SELECT DISTINCT merged_into_id FROM pontos WHERE merged_into_id IS NOT NULL AND is_removed = 0)
            )
            """
            params = []
            if since:
                where_clause += " AND p.updated_at > ?"
                params.append(since)
            
            rows = conn.execute(
                f"""
                SELECT p.id, p.lat, p.lng, p.updated_at, p.nome, p.merged_into_id,
                       CASE 
                         WHEN p.merged_into_id IS NOT NULL THEN (
                           SELECT GROUP_CONCAT(COALESCE(f2.nome, 'desconhecida'), ',')
                           FROM pontos p2
                           LEFT JOIN fontes f2 ON p2.fonte_id = f2.id
                           WHERE p2.merged_into_id = p.merged_into_id AND p2.is_removed = 0
                         )
                         ELSE COALESCE(f.nome, 'desconhecida')
                       END as fontes,
                       GROUP_CONCAT(pc.categoria_id, ',') as cat_csv
                FROM pontos p
                LEFT JOIN fontes f ON p.fonte_id = f.id
                LEFT JOIN ponto_categorias pc ON pc.ponto_id = p.id
                {where_clause}
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        
            data = []
            for row in rows:
                cat_ids = [int(c) for c in row["cat_csv"].split(",") if c.strip()] if row["cat_csv"] else []
                data.append({
                    "id": int(row["id"]),
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"]),
                    "fontes": row["fontes"],
                    "categorias": cat_ids,
                    "nome": row["nome"] or "Ponto de Recolha",
                    "updated_at": row["updated_at"],
                })

            return {
                "meta": {
                    "offset": offset,
                    "limit": limit,
                    "count": len(data),
                    "has_more": len(data) == limit,
                },
                "data": data,
            }

    def count_points(self) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM pontos WHERE is_removed = 0").fetchone()
        return int(row["c"] if row else 0)

    def export_snapshot(self) -> dict:
        with self.connection() as conn:
            categories = conn.execute(
                """
                SELECT id, nome_exibicao, eletronico
                FROM categorias
                ORDER BY id
                """
            ).fetchall()
            
            points = conn.execute(
                """
                SELECT p.id, p.lat, p.lng, p.nome,
                       CASE 
                         WHEN p.merged_into_id IS NOT NULL THEN (
                           SELECT GROUP_CONCAT(f2.nome, ',')
                           FROM pontos p2
                           LEFT JOIN fontes f2 ON p2.fonte_id = f2.id
                           WHERE p2.merged_into_id = p.merged_into_id AND p2.is_removed = 0
                         )
                         ELSE COALESCE(f.nome, 'desconhecida')
                       END as fontes,
                       GROUP_CONCAT(pc.categoria_id, ',') as cat_csv
                FROM pontos p
                LEFT JOIN fontes f ON p.fonte_id = f.id
                LEFT JOIN ponto_categorias pc ON pc.ponto_id = p.id
                WHERE p.is_removed = 0 AND (
                    p.merged_into_id IS NULL 
                    OR p.id IN (SELECT DISTINCT merged_into_id FROM pontos WHERE merged_into_id IS NOT NULL AND is_removed = 0)
                )
                GROUP BY p.id
                ORDER BY p.id
                """
            ).fetchall()
        
        cat_list = [
            {
                "id": int(c["id"]),
                "nome": c["nome_exibicao"] or "Categoria",
                "eletronico": bool(c["eletronico"]),
            }
            for c in categories
        ]
        
        pts_list = [
            {
                "id": int(p["id"]),
                "lat": float(p["lat"]),
                "lng": float(p["lng"]),
                "nome": p["nome"] or "Ponto de Recolha",
                "fontes": p["fontes"],
                "categorias": list(set(int(c) for c in p["cat_csv"].split(",") if c.strip())) if p["cat_csv"] else [],
            }
            for p in points
        ]
        
        return {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "categories": cat_list,
            "points": pts_list,
        }

    def get_last_update_time(self) -> datetime | None:
        """Retorna a data de última atualização de pontos ou categorias"""
        with self.connection() as conn:
            # Obter a data mais recente entre pontos e categorias
            row = conn.execute(
                """
                SELECT MAX(updated_at) as last_update
                FROM (
                    SELECT updated_at FROM pontos WHERE is_removed = 0
                    UNION ALL
                    SELECT updated_at FROM categorias
                )
                """
            ).fetchone()
            
            if row and row["last_update"]:
                return datetime.fromisoformat(row["last_update"])
            
            return None