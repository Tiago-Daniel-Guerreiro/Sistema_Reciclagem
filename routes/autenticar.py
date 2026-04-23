from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from database.sistema import registrar_usuario, verificar_login, confirmar_email_por_codigo, reenviar_codigo, solicitar_reset_senha, reset_senha_com_codigo
import re

autenticar_route = Blueprint('autenticar', __name__)


def _validar_codigo_format(codigo):
    return bool(re.match(r'^[A-Z0-9]{6}-[A-Z0-9]{6}$', codigo.upper()))

@autenticar_route.route('/registo', methods=['GET', 'POST'])
def registo():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmarSenha')
        receber = request.form.get('receiveemails')
        receber_notificacoes = bool(receber)

        if not nome or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "warning")
            return render_template("registo.html")

        if senha != confirmar_senha:
            flash("As senhas não coincidem.", "warning")
            return render_template("registo.html")

        resultado = registrar_usuario(nome, email, senha, receber_notificacoes)

        if resultado.get("sucesso"):
            # Login automático após registo bem-sucedido
            user = {
                'id': resultado.get('user_id'),
                'nome': nome,
                'tipo': 0,
            }
            
            session['user_id'] = user['id']
            session['nome'] = user['nome']
            session['usuario_tipo'] = user['tipo']
            session['user_email'] = email
            session["email_pendente_verificacao"] = email
            
            flash("Conta criada com sucesso! Verifica o teu email com o código enviado.", "success")
            return redirect(url_for('autenticar.verificar_email'))

        if resultado.get("erro") == "email_ja_registado":
            flash("Este email já está registado.", "danger")
        elif resultado.get("erro") == "email_nao_enviado":
            flash("Conta criada, mas não foi possível enviar o email de verificação. Verifica as configurações SMTP.", "danger")
        else:
            flash("Erro ao criar conta. Tenta novamente mais tarde.", "danger")

        return render_template("registo.html")

    return render_template("registo.html")


@autenticar_route.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        user = verificar_login(email, senha)

        if user:
            if user.get("erro") == "email_nao_verificado":
                session["email_pendente_verificacao"] = email
                flash("Precisas confirmar o teu email antes de entrar. Verifica o teu email com o código.", "warning")
                return redirect(url_for("autenticar.verificar_email"))
            
            if user.get("erro") == "codigo_expirado":
                session["email_pendente_verificacao"] = email
                flash("Código de verificação expirou. Pedimos um novo código por email.", "warning")
                reenviar_codigo(email)
                return redirect(url_for("autenticar.verificar_email"))

            session['user_id'] = user['id']
            session['nome'] = user['nome']
            session['usuario_tipo'] = user['tipo']
            session['user_email'] = email 

            flash(f"Bem-vindo {user['nome']}!", "success")
            return redirect(url_for('home.home'))

        flash("Email ou senha incorretos.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@autenticar_route.route('/logout')
def logout():
    session.clear()
    flash("Desconectado com sucesso.", "success")
    return redirect(url_for('home.home'))


@autenticar_route.route('/verificar-email', methods=['GET', 'POST'])
def verificar_email():
    email_pendente = session.get("email_pendente_verificacao", "")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        codigo = (request.form.get("codigo") or "").strip().upper()

        if not email or not codigo:
            flash("Preenche email e código de verificação.", "warning")
            return render_template("verificar_email.html", email_pendente=email_pendente)

        # Validar formato: 6chars-6chars
        if not _validar_codigo_format(codigo):
            flash("Formato inválido. Código deve ser: ABC123-DEF456", "warning")
            return render_template("verificar_email.html", email_pendente=email)

        confirmado = confirmar_email_por_codigo(email, codigo)

        if confirmado:
            # Após verificação, faz login automático
            from database.sistema import obter_utilizador_por_email
            user = obter_utilizador_por_email(email)
            
            if user:
                session.pop("email_pendente_verificacao", None)
                session['user_id'] = user['id']
                session['nome'] = user['nome']
                session['usuario_tipo'] = user['tipo']
                session['user_email'] = email
                
                flash("Email confirmado com sucesso! Bem-vindo!", "success")
                return redirect(url_for("home.home"))
            else:
                flash("Erro ao fazer login automático. Por favor, faz login manualmente.", "danger")
                return redirect(url_for("autenticar.login"))

        flash("Código inválido, expirado ou não corresponde a este email.", "danger")
        return render_template("verificar_email.html", email_pendente=email)

    return render_template("verificar_email.html", email_pendente=email_pendente)


@autenticar_route.route('/confirmar-email/<token>')
def confirmar_email_legacy(token):
    flash("Sistema antigo desativado.", "info")
    return redirect(url_for("autenticar.login"))


@autenticar_route.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = (request.form.get('email') or "").strip()
        
        if not email:
            flash("Por favor, introduza o email.", "warning")
            return render_template("esqueci_senha.html")
        
        resultado = solicitar_reset_senha(email)
        
        if resultado.get("sucesso"):
            flash("Se o email estiver registado e verificado, receberás um código de reset.", "info")
            return redirect(url_for("autenticar.login"))
        
        if resultado.get("erro") == "email_nao_verificado":
            flash("Este email ainda não foi verificado. Verifica o teu email primeiro.", "warning")
            return render_template("esqueci_senha.html")
        
        # Mostrar mensagem genérica por segurança
        flash("Se o email estiver registado e verificado, receberás um código de reset.", "info")
        return redirect(url_for("autenticar.login"))
    
    return render_template("esqueci_senha.html")


@autenticar_route.route('/reset-senha', methods=['GET', 'POST'])
def reset_senha():
    if request.method == 'POST':
        email = (request.form.get('email') or "").strip()
        codigo = (request.form.get('codigo') or "").strip().upper()
        nova_senha = request.form.get('nova_senha') or ""
        confirmar_nova_senha = request.form.get('confirmar_nova_senha') or ""
        
        if not email or not codigo or not nova_senha or not confirmar_nova_senha:
            flash("Preencha todos os campos.", "warning")
            return render_template("reset_senha.html")
        
        if nova_senha != confirmar_nova_senha:
            flash("As senhas não coincidem.", "warning")
            return render_template("reset_senha.html")
        
        if not _validar_codigo_format(codigo):
            flash("Formato inválido. Código deve ser: ABC123-DEF456", "warning")
            return render_template("reset_senha.html")
        
        resultado = reset_senha_com_codigo(email, codigo, nova_senha)
        
        if resultado.get("sucesso"):
            flash("Senha alterada com sucesso! Já podes fazer login.", "success")
            return redirect(url_for("autenticar.login"))
        
        if resultado.get("erro") == "codigo_invalido":
            flash("Código inválido.", "danger")
        elif resultado.get("erro") == "codigo_expirado":
            flash("Código expirou. Solicita um novo.", "danger")
        else:
            flash("Erro ao resetar senha.", "danger")
        
        return render_template("reset_senha.html")
    
    return render_template("reset_senha.html")

@autenticar_route.route('/reenviar-codigo', methods=['POST'])
def reenviar_codigo_route():
    email = (request.form.get('email') or request.json.get('email') or "").strip()
    
    if not email:
        return jsonify({"sucesso": False, "erro": "email_obrigatorio"}), 400
    
    resultado = reenviar_codigo(email)
    
    if resultado.get("sucesso"):
        return jsonify({
            "sucesso": True,
            "mensagem": "Código reenviado para o email com sucesso!"
        }), 200
    
    if resultado.get("erro") == "usuario_nao_encontrado":
        return jsonify({"sucesso": False, "erro": "usuario_nao_encontrado"}), 404
    
    if resultado.get("erro") == "email_ja_verificado":
        return jsonify({"sucesso": False, "erro": "email_ja_verificado"}), 409
    
    return jsonify({"sucesso": False, "erro": resultado.get("erro")}), 500


@autenticar_route.route('/conta', methods=['GET', 'POST'])
def conta():
    """Página de conta do utilizador"""
    if 'user_id' not in session:
        flash("Você precisa estar autenticado.", "danger")
        return redirect(url_for('autenticar.login'))
    
    import sqlite3
    from core.config import ServerConfig
    from seguranca import encrypt_password, verify_password
    
    config = ServerConfig()
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    
    if request.method == 'POST':
        try:
            user_id = session['user_id']
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            senha_atual = request.form.get('senha_atual', '').strip()
            senha_nova = request.form.get('senha_nova', '').strip()
            receber_notificacoes = bool(request.form.get('receber_notificacoes'))
            
            # Buscar utilizador atual
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM utilizadores WHERE id = ?", (user_id,))
            utilizador = cursor.fetchone()
            
            if not utilizador:
                flash("Utilizador não encontrado.", "danger")
                return redirect(url_for('autenticar.conta'))
            
            # Se quer mudar a senha, verificar a senha atual
            if senha_nova:
                if not senha_atual:
                    flash("Insira a sua senha atual para mudar a senha.", "danger")
                    return render_template('conta.html', utilizador=dict(utilizador))
                
                if not verify_password(senha_atual, utilizador['password_hash']):
                    flash("Senha atual incorreta.", "danger")
                    return render_template('conta.html', utilizador=dict(utilizador))
            
            # Validar email se foi alterado
            if email != utilizador['email']:
                cursor.execute("SELECT id FROM utilizadores WHERE email = ? AND id != ?", (email, user_id))
                if cursor.fetchone():
                    flash("Este email já está registado por outro utilizador.", "danger")
                    return render_template('conta.html', utilizador=dict(utilizador))
            
            # Atualizar dados
            updates = []
            params = []
            
            if nome:
                updates.append("nome = ?")
                params.append(nome)
            
            if email:
                updates.append("email = ?")
                params.append(email)
            
            if senha_nova:
                updates.append("password_hash = ?")
                params.append(encrypt_password(senha_nova))
            
            updates.append("receber_notificacoes = ?")
            params.append(1 if receber_notificacoes else 0)
            
            params.append(user_id)
            
            cursor.execute(f"UPDATE utilizadores SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            
            # Atualizar sessão
            if nome:
                session['nome'] = nome
            if email:
                session['user_email'] = email
            
            flash("Conta atualizada com sucesso!", "success")
            return redirect(url_for('autenticar.conta'))
            
        except Exception as e:
            flash(f"Erro ao atualizar conta: {str(e)}", "danger")
        finally:
            conn.close()
    
    # GET - Mostrar página
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utilizadores WHERE id = ?", (session['user_id'],))
    utilizador = cursor.fetchone()
    conn.close()
    
    if not utilizador:
        flash("Utilizador não encontrado.", "danger")
        return redirect(url_for('home.home'))
    
    return render_template('conta.html', utilizador=dict(utilizador))