from flask import Blueprint, request, render_template, jsonify, session, redirect, url_for, Response
from core.database import DatabaseManager
from core.config import ServerConfig
import json
from datetime import datetime
from functools import wraps

relatos_route = Blueprint('relatos', __name__)

def get_db_manager():
    config = ServerConfig()
    return DatabaseManager(config.db_path)

def requer_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('autenticar.login'))
        return f(*args, **kwargs)
    return decorated_function

@relatos_route.route('/reportar/<int:ponto_id>', methods=['GET', 'POST'])
@relatos_route.route('/reportar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@requer_login
def reportar_ponto(ponto_id):
    db = get_db_manager()
    
    if request.method == 'GET':
        # Buscar ponto e categorias
        with db.connection() as conn:
            cursor = conn.cursor()
            
            # Buscar ponto
            cursor.execute("""
                SELECT p.id, p.nome, p.lat, p.lng, COALESCE(f.nome, 'desconhecida') as fonte
                FROM pontos p
                LEFT JOIN fontes f ON p.fonte_id = f.id
                WHERE p.id = ?
            """, (ponto_id,))
            ponto = cursor.fetchone()
            
            if not ponto:
                return "Ponto não encontrado", 404
            
            # Buscar categorias do ponto
            cursor.execute("""
                SELECT c.id, c.nome_exibicao
                FROM ponto_categorias pc
                JOIN categorias c ON pc.categoria_id = c.id
                WHERE pc.ponto_id = ?
                ORDER BY c.nome_exibicao
            """, (ponto_id,))
            categorias_ponto = [row["id"] for row in cursor.fetchall()]
            
            # Buscar todas as categorias
            cursor.execute("""
                SELECT id, nome_exibicao
                FROM categorias
                ORDER BY nome_exibicao
            """)
            todas_categorias = cursor.fetchall()
        
        return render_template('relato.html', 
            ponto=ponto, 
            categorias_ponto=categorias_ponto,
            todas_categorias=todas_categorias
        )
    
    if request.method == 'POST':
        tipo_problema = request.form.get('tipo_problema')
        categorias_selecionadas = request.form.getlist('categorias[]')
        comentario = request.form.get('comentario', '')
        
        if not tipo_problema:
            return jsonify({"sucesso": False, "erro": "tipo_problema_obrigatorio"}), 400
        
        try:
            with db.connection() as conn:
                cursor = conn.cursor()
                
                # Se for categorias incorretas, guardar JSON
                categorias_json = None
                if tipo_problema == 'categorias_incorretas':
                    categorias_json = json.dumps(categorias_selecionadas)
                
                # Inserir report
                cursor.execute("""
                    INSERT INTO ponto_reports
                    (ponto_id, utilizador_id, tipo_problema, categorias_json, comentario, criado_em)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ponto_id,
                    session['user_id'],
                    tipo_problema,
                    categorias_json,
                    comentario,
                    datetime.now().isoformat()
                ))
            
            return jsonify({
                "sucesso": True,
                "mensagem": "Relatório enviado com sucesso! Obrigado pela sua contribuição."
            })
        
        except Exception as e:
            print(f"[RELATO] Erro ao guardar relatório: {e}")
            return jsonify({"sucesso": False, "erro": str(e)}), 500
