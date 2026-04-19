from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from database.sistema import registrar_usuario, verificar_login, confirmar_email_por_codigo

autenticar_route = Blueprint('autenticar', __name__)

@autenticar_route.route('/registo', methods=['GET', 'POST'])
@autenticar_route.route('/registo.html', methods=['GET', 'POST'])
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
@autenticar_route.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        user = verificar_login(email, senha)

        if user:
            if user.get("erro") == "email_nao_verificado":
                session["email_pendente_verificacao"] = email
                flash("Precisas confirmar o teu email antes de entrar.", "warning")
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
@autenticar_route.route('/verificar-email.html', methods=['GET', 'POST'])
def verificar_email():
    email_pendente = session.get("email_pendente_verificacao", "")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        codigo = (request.form.get("codigo") or "").strip()

        if not email or not codigo:
            flash("Preenche email e código de verificação.", "warning")
            return render_template("verificar_email.html", email_pendente=email_pendente)

        if not codigo.isdigit() or len(codigo) != 6:
            flash("O código deve ter 6 dígitos numéricos.", "warning")
            return render_template("verificar_email.html", email_pendente=email)

        confirmado = confirmar_email_por_codigo(email, codigo)

        if confirmado:
            session.pop("email_pendente_verificacao", None)
            flash("Email confirmado com sucesso. Já podes iniciar sessão.", "success")
            return redirect(url_for("autenticar.login"))

        flash("Código inválido para este email.", "danger")
        return render_template("verificar_email.html", email_pendente=email)

    return render_template("verificar_email.html", email_pendente=email_pendente)


@autenticar_route.route('/confirmar-email/<token>')
def confirmar_email_legacy(token):
    flash("Sistema antigo desativado.", "info")
    return redirect(url_for("autenticar.login"))