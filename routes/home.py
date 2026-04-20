from flask import Blueprint, render_template, request, flash, redirect, url_for
from routes.email_service import enviar_contacto_para_equipa

home_route = Blueprint('home', __name__)

@home_route.route("/", strict_slashes=False)
def home():
    return render_template('index.html')

@home_route.route("/mapa", strict_slashes=False, methods=["GET"])
def mapa_page():
    return render_template("mapa.html")

@home_route.route("/informacoes", strict_slashes=False)
def informacoes():
    return render_template("informacoes.html")

@home_route.route("/dados", strict_slashes=False)
def dados():
    return render_template("dados.html")

@home_route.route('/classificacao', strict_slashes=False)
def classificacao():
    return render_template('classificacao.html')

@home_route.route('/contacto', strict_slashes=False, methods=['GET', 'POST'])
def contacto():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip()
        mensagem = (request.form.get("mensagem") or "").strip()

        if not nome or not email or not mensagem:
            flash("Preenche todos os campos do formulário.", "warning")
            return redirect(url_for("home.contacto"))

        enviar_contacto_para_equipa(nome, email, mensagem)
        flash("Mensagem enviada com sucesso. Obrigado pelo contacto!", "success")
        return redirect(url_for("home.contacto"))

    return render_template('contacto.html')
