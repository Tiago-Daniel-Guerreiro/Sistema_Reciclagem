from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime
from core.config import ServerConfig
from core.database import DatabaseManager
from routes.email_service import enviar_novo_ponto

admin_route = Blueprint('admin', __name__, url_prefix='/admin')

# Usar o mesmo BD que a app
def get_db_path():
    config = ServerConfig()
    return config.db_path

def refresh_snapshot():
    """Gera novamente o ficheiro `templates/Map/data/snapshot.json` a partir da BD.

    O mapa Leaflet (em `templates/Map/`) consome este ficheiro estático.
    """
    cfg = ServerConfig()
    db = DatabaseManager(cfg.db_path)
    snapshot = db.export_snapshot()
    snapshot_path = Path(__file__).resolve().parent.parent / "templates" / "Map" / "data" / "snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

def _get_or_create_fonte_id(conn: sqlite3.Connection, nome_fonte: str):
    nome_fonte = (nome_fonte or "manual").strip() or "manual"
    now = datetime.utcnow().isoformat()
    conn.execute("INSERT OR IGNORE INTO fontes (nome, created_at) VALUES (?, ?)", (nome_fonte, now))
    row = conn.execute("SELECT id FROM fontes WHERE nome = ? LIMIT 1", (nome_fonte,)).fetchone()
    return int(row["id"]) if row else 1

def conectar_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Você precisa estar autenticado.", "danger")
            return redirect(url_for('autenticar.login'))
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT tipo FROM utilizadores WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user['tipo'] != 1:
            flash("Acesso negado. Apenas administradores.", "danger")
            return redirect(url_for('home.home'))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_route.route('/', methods=['GET'])
@require_admin
def dashboard():
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Contar registros
    stats = {}
    tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as total FROM {table}")
        stats[table] = cursor.fetchone()['total']
    
    # Contar reports
    cursor.execute("SELECT COUNT(*) as total FROM ponto_reports")
    stats['reports'] = cursor.fetchone()['total']
    
    # Buscar pontos com reports
    cursor.execute("""
        SELECT p.id, p.nome, COUNT(pr.id) as total_reports
        FROM pontos p
        LEFT JOIN ponto_reports pr ON p.id = pr.ponto_id
        WHERE pr.id IS NOT NULL
        GROUP BY p.id
        ORDER BY total_reports DESC
        LIMIT 10
    """)
    pontos_reportados = cursor.fetchall()
    
    conn.close()
    return render_template('admin/dashboard.html', stats=stats, pontos_reportados=pontos_reportados)


@admin_route.route('/pontos', methods=['GET'])
@require_admin
def pontos_manage():
    q = (request.args.get("q") or "").strip().lower()
    conn = conectar_db()
    cursor = conn.cursor()
    if q:
        cursor.execute(
            "SELECT id, nome, lat, lng, updated_at FROM pontos WHERE is_removed = 0 AND LOWER(COALESCE(nome,'')) LIKE ? ORDER BY updated_at DESC LIMIT 200",
            (f"%{q}%",),
        )
    else:
        cursor.execute(
            "SELECT id, nome, lat, lng, updated_at FROM pontos WHERE is_removed = 0 ORDER BY updated_at DESC LIMIT 200"
        )
    pontos = cursor.fetchall()
    conn.close()
    return render_template("admin/pontos_manage.html", pontos=pontos, q=q)


@admin_route.route('/pontos/novo', methods=['GET', 'POST'])
@require_admin
def pontos_novo():
    conn = conectar_db()
    cursor = conn.cursor()
    categorias = cursor.execute("SELECT id, nome_exibicao FROM categorias ORDER BY nome_exibicao").fetchall()

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        lat = (request.form.get("lat") or "").strip()
        lng = (request.form.get("lng") or "").strip()
        fonte_nome = (request.form.get("fonte") or "manual").strip()
        categorias_ids = request.form.getlist("categorias")

        if not nome or not lat or not lng:
            flash("Preenche pelo menos Nome, Latitude e Longitude.", "warning")
            conn.close()
            return render_template("admin/ponto_form.html", categorias=categorias, form=request.form)

        try:
            lat_f = float(lat.replace(",", "."))
            lng_f = float(lng.replace(",", "."))
        except ValueError:
            flash("Latitude/Longitude inválidas.", "danger")
            conn.close()
            return render_template("admin/ponto_form.html", categorias=categorias, form=request.form)

        now = datetime.utcnow().replace(microsecond=0).isoformat()
        try:
            fonte_id = _get_or_create_fonte_id(conn, fonte_nome)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO pontos (lat, lng, fonte_id, source_id, is_removed, nome, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
                (lat_f, lng_f, fonte_id, fonte_nome, nome, now, now),
            )
            ponto_id = cur.lastrowid

            # categorias (opcional)
            for cid in categorias_ids:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO ponto_categorias (ponto_id, categoria_id) VALUES (?, ?)",
                        (ponto_id, int(cid)),
                    )
                except Exception:
                    continue

            conn.commit()

            # email + snapshot
            try:
                enviar_novo_ponto({"id": ponto_id, "nome": nome, "lat": lat_f, "lng": lng_f})
            except Exception as e:
                print(f"[ADMIN] Falha ao enviar email de novo ponto: {e}", flush=True)

            try:
                refresh_snapshot()
            except Exception as e:
                print(f"[ADMIN] Falha ao atualizar snapshot.json: {e}", flush=True)

            flash("Ponto criado com sucesso!", "success")
            conn.close()
            return redirect(url_for("admin.pontos_manage"))
        except Exception as e:
            flash(f"Erro ao criar ponto: {e}", "danger")
            conn.close()
            return render_template("admin/ponto_form.html", categorias=categorias, form=request.form)

    conn.close()
    return render_template("admin/ponto_form.html", categorias=categorias, form={})


@admin_route.route('/table/<table_name>', methods=['GET'])
@require_admin
def list_table(table_name):
    valid_tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar coluna ID (dinâmico)
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col['name'] for col in columns]
    
    # Encontrar chave primária
    cursor.execute(f"PRAGMA table_info({table_name})")
    pk_column = None
    for col in cursor.fetchall():
        if col['pk'] != 0:  # pk=1 significa PRIMARY KEY
            if pk_column is None or col['pk'] < pk_column[1]:
                pk_column = (col['name'], col['pk'])
    
    # Buscar dados
    if table_name == 'pontos':
        cursor.execute(f"SELECT * FROM {table_name} WHERE is_removed = 0 ORDER BY id DESC LIMIT 100")
    elif pk_column:
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY {pk_column[0]} DESC LIMIT 100")
    else:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
    
    rows = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/table_list.html', 
                         table_name=table_name, 
                         columns=column_names, 
                         rows=rows,
                         pk_column=pk_column[0] if pk_column else 'id')


@admin_route.route('/table/<table_name>/add', methods=['GET', 'POST'])
@require_admin
def add_record(table_name):
    valid_tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar informações das colunas
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    if request.method == 'POST':
        try:
            # Preparar dados do formulário
            data = {}
            for col in columns:
                col_name = col['name']
                if col_name == 'id':  # Pular ID auto-increment
                    continue
                
                if col_name in request.form:
                    value = request.form.get(col_name)
                    
                    # Converter para tipo correto
                    if col['type'] == 'INTEGER' and value:
                        value = int(value) if value else None
                    elif col['type'] == 'REAL' and value:
                        value = float(value) if value else None
                    
                    data[col_name] = value
            
            # Adicionar timestamps se necessário
            if 'data_criacao' in [c['name'] for c in columns]:
                data['data_criacao'] = datetime.now().isoformat()
            
            # Executar INSERT
            columns_list = list(data.keys())
            placeholders = ','.join(['?' for _ in columns_list])
            columns_str = ','.join(columns_list)
            
            cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})", 
                         list(data.values()))
            conn.commit()
            created_id = cursor.lastrowid

            if table_name == "pontos" and created_id:
                try:
                    row = conn.execute("SELECT * FROM pontos WHERE id = ?", (created_id,)).fetchone()
                    if row:
                        ponto = dict(row)
                        # Normalizar nomes para o email template (compatibilidade)
                        ponto_for_email = {
                            "id": ponto.get("id"),
                            "nome": ponto.get("nome") or "Ponto de Recolha",
                            "lat": ponto.get("lat"),
                            "lng": ponto.get("lng"),
                        }
                        enviar_novo_ponto(ponto_for_email)
                except Exception as e:
                    print(f"[ADMIN] Falha ao enviar email de novo ponto: {e}", flush=True)

                try:
                    refresh_snapshot()
                except Exception as e:
                    print(f"[ADMIN] Falha ao atualizar snapshot.json: {e}", flush=True)
            
            flash(f"Registro adicionado com sucesso!", "success")
            return redirect(url_for('admin.list_table', table_name=table_name))
            
        except Exception as e:
            flash(f"Erro ao adicionar: {str(e)}", "danger")
    
    conn.close()
    
    return render_template('admin/table_form.html', 
                         table_name=table_name, 
                         columns=columns, 
                         record=None)


@admin_route.route('/table/<table_name>/edit/<int:record_id>', methods=['GET', 'POST'])
@require_admin
def edit_record(table_name, record_id):
    valid_tables = ['utilizadores', 'pontos', 'categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar informações das colunas
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    # Buscar registro
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    
    if not record:
        flash("Registro não encontrado.", "danger")
        conn.close()
        return redirect(url_for('admin.list_table', table_name=table_name))
    
    if request.method == 'POST':
        try:
            data = {}
            for col in columns:
                col_name = col['name']
                if col_name == 'id':
                    continue
                
                if col_name in request.form:
                    value = request.form.get(col_name)
                    
                    if col['type'] == 'INTEGER' and value:
                        value = int(value) if value else None
                    elif col['type'] == 'REAL' and value:
                        value = float(value) if value else None
                    
                    data[col_name] = value
            
            # Executar UPDATE
            set_clause = ','.join([f"{k}=?" for k in data.keys()])
            values = list(data.values())
            values.append(record_id)
            
            cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", values)
            conn.commit()
            
            flash(f"Registro atualizado com sucesso!", "success")
            return redirect(url_for('admin.list_table', table_name=table_name))
            
        except Exception as e:
            flash(f"Erro ao atualizar: {str(e)}", "danger")
    
    conn.close()
    
    return render_template('admin/table_form.html', 
                         table_name=table_name, 
                         columns=columns, 
                         record=dict(record))


@admin_route.route('/table/<table_name>/delete/<int:record_id>', methods=['POST'])
@require_admin
def delete_record(table_name, record_id):
    valid_tables = ['utilizadores', 'pontos', 'categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Soft delete para pontos (marcar como is_removed = 1)
        if table_name == 'pontos':
            # Verificar se já foi soft deleted
            cursor.execute("SELECT is_removed FROM pontos WHERE id = ?", (record_id,))
            result = cursor.fetchone()
            
            if result and result['is_removed'] == 1:
                # Já foi soft deleted - fazer hard delete completo
                cursor.execute("DELETE FROM ponto_categorias WHERE ponto_id = ?", (record_id,))
                cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
                flash(f"Ponto completamente deletado!", "success")
            else:
                # Primeiro soft delete
                cursor.execute(f"UPDATE {table_name} SET is_removed = 1 WHERE id = ?", (record_id,))
                flash(f"Ponto marcado como deletado (soft delete)!", "success")
        else:
            # Hard delete para outras tabelas
            cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
            flash(f"Registro deletado com sucesso!", "success")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        flash(f"Erro ao deletar: {str(e)}", "danger")
    
    return redirect(url_for('admin.list_table', table_name=table_name))


@admin_route.route('/table/<table_name>/details/<int:record_id>', methods=['GET'])
@require_admin
def view_record(table_name, record_id):
    valid_tables = ['utilizadores', 'pontos', 'categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar registro
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    
    if not record:
        flash("Registro não encontrado.", "danger")
        conn.close()
        return redirect(url_for('admin.list_table', table_name=table_name))
    
    # Buscar relacionamentos se existirem
    relationships = {}
    
    if table_name == 'pontos':
        cursor.execute("SELECT * FROM ponto_categorias WHERE ponto_id = ?", (record_id,))
        relationships['categorias'] = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/record_details.html', 
                         table_name=table_name, 
                         record=dict(record),
                         relationships=relationships)


@admin_route.route('/ponto/<int:ponto_id>/reports', methods=['GET'])
@require_admin
def view_ponto_reports(ponto_id):
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar informações do ponto
    cursor.execute("SELECT * FROM pontos WHERE id = ?", (ponto_id,))
    ponto = cursor.fetchone()
    
    if not ponto:
        flash("Ponto não encontrado.", "danger")
        return redirect(url_for('admin.view_reports'))
    
    # Buscar todos os reports deste ponto
    cursor.execute("""
        SELECT pr.*, u.nome, u.email
        FROM ponto_reports pr
        JOIN utilizadores u ON pr.utilizador_id = u.id
        WHERE pr.ponto_id = ?
        ORDER BY pr.criado_em DESC
    """, (ponto_id,))
    reports = cursor.fetchall()
    
    conn.close()
    return render_template('admin/ponto_reports_details.html', 
                         ponto=dict(ponto), 
                         reports=reports)
