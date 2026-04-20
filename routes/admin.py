from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import sqlite3
import os
from datetime import datetime
from core.config import ServerConfig

admin_route = Blueprint('admin', __name__, url_prefix='/admin')

# Usar o mesmo BD que a app
def get_db_path():
    config = ServerConfig()
    return config.db_path

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
    
    conn.close()
    return render_template('admin/dashboard.html', stats=stats)


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
    
    # Buscar dados (soft delete filter para pontos)
    if table_name == 'pontos':
        cursor.execute(f"SELECT * FROM {table_name} WHERE is_removed = 0 ORDER BY id DESC LIMIT 100")
    else:
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/table_list.html', 
                         table_name=table_name, 
                         columns=column_names, 
                         rows=rows)


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
    valid_tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
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
    valid_tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
    if table_name not in valid_tables:
        flash("Tabela inválida.", "danger")
        return redirect(url_for('admin.dashboard'))
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Soft delete para pontos (marcar como is_removed = 1)
        if table_name == 'pontos':
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
    valid_tables = ['utilizadores', 'pontos', 'categorias', 'ponto_categorias']
    
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
    
    if table_name == 'graficos':
        cursor.execute("SELECT * FROM estatisticas WHERE grafico_id = ?", (record_id,))
        relationships['estatisticas'] = cursor.fetchall()
    
    if table_name == 'estatisticas':
        cursor.execute("SELECT * FROM dados_grafico WHERE estatistica_id = ?", (record_id,))
        relationships['dados_grafico'] = cursor.fetchall()
        cursor.execute("SELECT * FROM graficos WHERE id = ?", (record['grafico_id'],))
        relationships['grafico'] = cursor.fetchone()
    
    if table_name == 'pontos':
        cursor.execute("SELECT * FROM ponto_categorias WHERE ponto_id = ?", (record_id,))
        relationships['categorias'] = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/record_details.html', 
                         table_name=table_name, 
                         record=dict(record),
                         relationships=relationships)
