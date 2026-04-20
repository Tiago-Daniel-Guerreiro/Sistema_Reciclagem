from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from database.sistema import registrar_usuario, verificar_login, confirmar_email_por_codigo, reenviar_codigo
import re

autenticar_route = Blueprint('autenticar', __name__)


def _validar_codigo_format(codigo):
    return bool(re.match(r'^[A-Z0-9]{6}-[A-Z0-9]{6}$', codigo.upper()))

@autenticar_route.route('/registo', methods=['GET', 'POST'])
def registo():
    if request.method == 'POST':
        nome = request.form.get('nome')
        regiao = request.form.get('regiao')
        email = request.form.get('email')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmarSenha')
        receber = request.form.get('receiveemails')
        receber_notificacoes = bool(receber)

        if not nome or not regiao or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "warning")
            return render_template("registo.html")

        if senha != confirmar_senha:
            flash("As senhas não coincidem.", "warning")
            return render_template("registo.html")

        resultado = registrar_usuario(nome, email, senha, regiao, receber_notificacoes)

        if resultado.get("sucesso"):
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

            flash(f"Bem-vindo {user['nome']}!", "success")
            return redirect(url_for('home.home'))

        flash("Email ou senha incorretos.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@autenticar_route.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada.", "info")
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
            session.pop("email_pendente_verificacao", None)
            flash("Email confirmado com sucesso! Já podes iniciar sessão.", "success")
            return redirect(url_for("autenticar.login"))

        flash("Código inválido, expirado ou não corresponde a este email.", "danger")
        return render_template("verificar_email.html", email_pendente=email)

    return render_template("verificar_email.html", email_pendente=email_pendente)


@autenticar_route.route('/confirmar-email/<token>')
def confirmar_email_legacy(token):
    flash("Sistema antigo desativado.", "info")
    return redirect(url_for("autenticar.login"))


@autenticar_route.route('/api/reenviar-codigo', methods=['POST'])
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