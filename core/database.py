from __future__ import annotations
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, ContextManager
from core.category_catalog import category_metadata, known_categories
from core.point_filters import remove_points_without_categories_sql, remove_points_outside_portugal_sql

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    @contextmanager
    def connection(self) -> ContextManager[sqlite3.Connection]:
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

                CREATE TABLE IF NOT EXISTS pontos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    fonte_id INTEGER NOT NULL,
                    source_id TEXT,
                    is_removed INTEGER NOT NULL DEFAULT 0,
                    nome TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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
                    tipo INTEGER NOT NULL DEFAULT 0 CHECK (tipo IN (0,1)),
                    receber_notificacoes INTEGER NOT NULL DEFAULT 1 CHECK (receber_notificacoes IN (0,1)),
                    email_verificado INTEGER NOT NULL DEFAULT 0,
                    data_registo DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Tabela de códigos de verificação de email
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS verificacao_email (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    utilizador_id INTEGER NOT NULL UNIQUE,
                    codigo TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id) ON DELETE CASCADE
                )
                """
            )
            
            # Tabela de reportes de pontos
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ponto_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ponto_id INTEGER NOT NULL,
                    utilizador_id INTEGER NOT NULL,
                    tipo_problema TEXT NOT NULL,
                    categorias_json TEXT,
                    comentario TEXT,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (ponto_id) REFERENCES pontos(id) ON DELETE CASCADE,
                    FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id) ON DELETE CASCADE
                )
                """
            )
            
            # Tabela de códigos de reset de senha
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reset_senha (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    utilizador_id INTEGER NOT NULL,
                    codigo TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    utilizado INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id) ON DELETE CASCADE
                )
                """
            )
                        
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
            
            # Criar admin padrão se não existir
            self._create_default_admin(conn)

    def _get_or_create_fonte_id(self, conn: sqlite3.Connection, fonte_nome: str, now: str) -> int:
        # Garantir que fonte_nome é string
        fonte_nome = str(fonte_nome) if fonte_nome else "desconhecida"
        
        row = conn.execute("SELECT id FROM fontes WHERE nome = ?", (fonte_nome,)).fetchone()
        if row:
            return int(row["id"])
        
        cursor = conn.cursor()
        cursor.execute("INSERT INTO fontes (nome, created_at) VALUES (?, ?)", (fonte_nome, now))
        last_id = cursor.lastrowid
        return int(last_id) if last_id is not None else 1

    def _create_default_admin(self, conn: sqlite3.Connection) -> None:
        import os
        from seguranca import encrypt_password
        
        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            return
        
        admin_email = os.getenv("ADMIN_EMAIL", "admin@reciclatech.pt")
        
        # Verificar se admin já existe
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM utilizadores WHERE tipo = 1")
        
        if cursor.fetchone():
            return
        
        # Criar admin
        admin_pass_cript = encrypt_password(admin_password)
        cursor.execute("""
            INSERT INTO utilizadores
            (nome, email, password_hash, tipo, receber_notificacoes, email_verificado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("Administrador", admin_email, admin_pass_cript, 1, 1, 1))
        
        print(f"[Database] Admin criado: {admin_email}")

    def insert_points(self, points: list[dict]) -> int:
        created = 0
        now = now_iso()

        with self.connection() as conn:            
            for point in points:
                # Garantir tipos corretos
                ponto_nome = str(point.get("nome", "Ponto de Recolha"))
                categorias = point.get("categorias", [])
                fontes = point.get("fontes", [])
                
                # Garantir que fonte_principal é string
                if fontes:
                    fonte_principal = str(fontes[0])
                else:
                    fonte_principal = "desconhecida"
                
                fonte_value = self._get_or_create_fonte_id(conn, fonte_principal, now)
                
                lat = float(point["lat"])
                lng = float(point["lng"])
                
                # Ignorar duplicados exactos: mesma fonte + coords iguais
                existing = conn.execute(
                    "SELECT id FROM pontos WHERE source_id = ? AND ABS(lat - ?) < 0.00001 AND ABS(lng - ?) < 0.00001 LIMIT 1",
                    (fonte_principal, lat, lng)
                ).fetchone()
                
                if existing:
                    print(f"[insert] Skipping duplicate: {fonte_principal} at ({lat}, {lng})", flush=True)
                    continue  # Ignorar duplicado exacto

                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO pontos (lat, lng, fonte_id, source_id, is_removed, nome, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
                    (lat, lng, fonte_value, fonte_principal, ponto_nome, now, now),
                )
                ponto_id = cursor.lastrowid
                created += 1

                for cat_key in categorias:
                    # Garantir que cat_key é string
                    cat_key_str = str(cat_key)
                    meta = category_metadata(cat_key_str)
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
            where_clause = "WHERE p.is_removed = 0"
            params = []
            if since:
                where_clause += " AND p.updated_at > ?"
                params.append(since)
            
            rows = conn.execute(
                f"""
                SELECT p.id, p.lat, p.lng, p.updated_at, p.nome,
                       COALESCE(f.nome, 'desconhecida') as fontes,
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
                       COALESCE(f.nome, 'desconhecida') as fontes,
                       GROUP_CONCAT(pc.categoria_id, ',') as cat_csv
                FROM pontos p
                LEFT JOIN fontes f ON p.fonte_id = f.id
                LEFT JOIN ponto_categorias pc ON pc.ponto_id = p.id
                WHERE p.is_removed = 0
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