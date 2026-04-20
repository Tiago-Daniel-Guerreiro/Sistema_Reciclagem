import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from dotenv import load_dotenv
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOTENV_PATHS = [
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.path.dirname(__file__), ".env")
]
for dotenv_path in DOTENV_PATHS:
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f"[EmailService] .env carregado de: {dotenv_path}")
        break

EMAIL_REMETENTE = os.getenv("SMTP_USER", "")
SENHA_APP = os.getenv("SMTP_PASS", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../templates/emails")
DB_PATH = os.path.join(os.path.dirname(__file__), "../banco.db")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def enviar_email(destinatario, assunto, template_nome=None, contexto=None, corpo_html=None):
    if not EMAIL_REMETENTE or not SENHA_APP:
        print("SMTP não configurado. Email não enviado.")
        return False

    try:
        if template_nome:
            template = env.get_template(template_nome)
            corpo_html = template.render(contexto or {})

        if not corpo_html:
            corpo_html = "<p>Email sem conteúdo.</p>"

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = destinatario
        msg['Subject'] = assunto

        msg.add_header('Reply-To', EMAIL_REMETENTE)
        msg.add_header('X-Mailer', 'Python SMTP')
        msg.add_header('Precedence', 'bulk')

        msg.attach(MIMEText(corpo_html, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(msg)

        print(f"Email enviado para {destinatario}")
        return True

    except Exception as e:
        print(f"Erro ao enviar email para {destinatario}: {e}")
        return False


def enviar_email_verificacao(destinatario, nome, codigo_verificacao):
    assunto = "Confirmação de Email - ReciclaTech"

    contexto = {
        "usuario": nome,
        "codigo_verificacao": codigo_verificacao
    }

    return enviar_email(destinatario, assunto, "verificacao_email.html", contexto=contexto)

def enviar_contacto_para_equipa(nome, email, mensagem):
    if not EMAIL_REMETENTE or not SENHA_APP:
        print("SMTP não configurado: contacto registado sem envio de email.")
        return

    assunto = f"[ReciclaTech] Novo contacto de {nome}"

    corpo_html = f"""
    <p><strong>Nome:</strong> {nome}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Mensagem:</strong></p>
    <p>{mensagem}</p>
    """

    enviar_email(EMAIL_REMETENTE, assunto, corpo_html=corpo_html)


def enviar_novo_ponto(ponto):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email, nome
        FROM utilizadores
        WHERE receber_notificacoes = 1
    """)

    usuarios = cursor.fetchall()
    conn.close()

    for row in usuarios:
        email = row["email"]
        nome_usuario = row["nome"]

        contexto = {
            "usuario": nome_usuario,
            "ponto_nome": ponto['nome'],
            "latitude": ponto['latitude'],
            "longitude": ponto['longitude'],
            "horario": ponto['horario'],
            "contacto": ponto['contacto'],
            "website": ponto['website'],
            "descricao": ponto['descricao']
        }

        enviar_email(
            email,
            f"Novo ponto de reciclagem",
            "novo_ponto.html",
            contexto
        )


def enviar_evento(evento):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email, nome
        FROM utilizadores
        WHERE receber_notificacoes = 1
    """)

    usuarios = cursor.fetchall()
    conn.close()

    for row in usuarios:
        email = row["email"]
        nome_usuario = row["nome"]

        contexto = {
            "usuario": nome_usuario,
            "evento_nome": evento['nome'],
            "data": evento['data'],
            "local": evento['local'],
            "descricao": evento['descricao']
        }

        enviar_email(
            email,
            f"Novo evento de reciclagem: {evento['nome']}",
            "evento.html",
            contexto
        )


def enviar_dica(dica):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email, nome
        FROM utilizadores
        WHERE receber_notificacoes = 1
    """)

    usuarios = cursor.fetchall()
    conn.close()

    for row in usuarios:
        email = row["email"]
        nome_usuario = row["nome"]

        contexto = {
            "usuario": nome_usuario,
            "titulo": dica['titulo'],
            "conteudo": dica['conteudo']
        }

        enviar_email(
            email,
            f"Dica ambiental: {dica['titulo']}",
            "dica.html",
            contexto
        )


def enviar_email_reset_senha(destinatario, nome, codigo_reset):
    assunto = "Reset de Senha - ReciclaTech"

    contexto = {
        "usuario": nome,
        "codigo_reset": codigo_reset
    }

    return enviar_email(destinatario, assunto, "reset_senha.html", contexto=contexto)
