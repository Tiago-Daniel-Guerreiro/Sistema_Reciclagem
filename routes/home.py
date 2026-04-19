from flask import Blueprint, render_template, request, flash, redirect, url_for
from routes.email_service import enviar_contacto_para_equipa

home_route = Blueprint('home', __name__)

@home_route.route('/')
@home_route.route('/index.html')
def home():
    return render_template('index.html')

@home_route.route("/informacoes")
@home_route.route("/informacoes.html")
def informacoes():
    return render_template("informacoes.html")

@home_route.route("/dados")
@home_route.route("/dados.html")
def dados():
    return render_template("dados.html")

@home_route.route('/classificacao')
@home_route.route('/classificacao.html')
def classificacao():
    return render_template('classificacao.html')
 
@home_route.route('/mapa')
@home_route.route('/mapa.html')
def mapa():
    return render_template('mapa.html')

@home_route.route('/contacto', methods=['GET', 'POST'])
@home_route.route('/contacto.html', methods=['GET', 'POST'])
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
