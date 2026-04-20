import secrets
import string
from datetime import datetime, timedelta
from seguranca import encrypt_password, decrypt_password
from routes.email_service import enviar_email_verificacao
from core.config import ServerConfig
from core.database import DatabaseManager

_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        config = ServerConfig()
        _db_manager = DatabaseManager(config.db_path, merge_distance_meters=config.merge_distance_meters)
    return _db_manager


def gerar_codigo():
    caracteres = string.digits + string.ascii_uppercase
    parte1 = ''.join(secrets.choice(caracteres) for _ in range(6))
    parte2 = ''.join(secrets.choice(caracteres) for _ in range(6))
    return f"{parte1}-{parte2}"


def registrar_usuario(nome, email, senha, regiao, receber_notificacoes):
    db = get_db_manager()
    
    senha_cript = encrypt_password(senha)
    receber = 1 if receber_notificacoes else 0
    codigo_verificacao = gerar_codigo()
    agora = datetime.now().isoformat()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO utilizadores
                (nome, email, password_hash, tipo, regiao, receber_notificacoes, codigo_verificacao, codigo_verificacao_criado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, email, senha_cript, "utilizador", regiao, receber, codigo_verificacao, agora))

        email_enviado = enviar_email_verificacao(email, nome, codigo_verificacao)
        if not email_enviado:
            print(f"Falha ao enviar o email de verificação para {email}.")
            return {"sucesso": False, "erro": "email_nao_enviado"}

        return {"sucesso": True}

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return {"sucesso": False, "erro": "email_ja_registado"}
        print(f"Erro ao registrar usuário: {e}")
        return {"sucesso": False, "erro": "geral"}


def verificar_login(email, senha_input):
    db = get_db_manager()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nome, password_hash, tipo, codigo_verificacao, codigo_verificacao_criado_em
                FROM utilizadores
                WHERE email = ?
            """, (email,))
            user = cursor.fetchone()

            if user:
                if user["codigo_verificacao"] is not None:
                    if user["codigo_verificacao_criado_em"]:
                        tempo_criacao = datetime.fromisoformat(user["codigo_verificacao_criado_em"])
                        if datetime.now() - tempo_criacao > timedelta(hours=24):
                            return {"erro": "codigo_expirado"}
                    return {"erro": "email_nao_verificado"}

                senha_bd = decrypt_password(user["password_hash"])

                if senha_input == senha_bd:
                    return {
                        "id": user["id"],
                        "nome": user["nome"],
                        "tipo": user["tipo"]
                    }

    except Exception as e:
        print(f"Erro ao verificar login: {e}")

    return None


def confirmar_email_por_codigo(email, codigo):
    db = get_db_manager()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT codigo_verificacao, codigo_verificacao_criado_em
                FROM utilizadores
                WHERE email = ?
            """, (email,))
            user = cursor.fetchone()

            if not user or user["codigo_verificacao"].upper() != codigo.upper():
                return False

            if user["codigo_verificacao_criado_em"]:
                tempo_criacao = datetime.fromisoformat(user["codigo_verificacao_criado_em"])
                if datetime.now() - tempo_criacao > timedelta(hours=24):
                    return False

            cursor.execute("""
                UPDATE utilizadores
                SET codigo_verificacao = NULL, codigo_verificacao_criado_em = NULL, email_verificado = 1
                WHERE email = ? AND codigo_verificacao = ?
            """, (email, codigo))

            return cursor.rowcount > 0

    except Exception as e:
        print(f"Erro ao confirmar email por código: {e}")
        return False


def confirmar_email_por_token(token):
    db = get_db_manager()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE utilizadores
                SET codigo_verificacao = NULL, codigo_verificacao_criado_em = NULL, email_verificado = 1
                WHERE codigo_verificacao = ?
            """, (token,))

        return cursor.rowcount > 0

    except Exception as e:
        print(f"Erro ao confirmar email: {e}")
        return False


def reenviar_codigo(email):
    db = get_db_manager()
    
    novo_codigo = gerar_codigo()
    agora = datetime.now().isoformat()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT nome, codigo_verificacao
                FROM utilizadores
                WHERE email = ?
            """, (email,))
            user = cursor.fetchone()

            if not user:
                return {"sucesso": False, "erro": "usuario_nao_encontrado"}

            if user["codigo_verificacao"] is None:
                return {"sucesso": False, "erro": "email_ja_verificado"}

            cursor.execute("""
                UPDATE utilizadores
                SET codigo_verificacao = ?, codigo_verificacao_criado_em = ?
                WHERE email = ?
            """, (novo_codigo, agora, email))

            email_enviado = enviar_email_verificacao(email, user["nome"], novo_codigo)
            if not email_enviado:
                print(f"Falha ao reenviar código para {email}.")
                return {"sucesso": False, "erro": "email_nao_enviado"}

            return {"sucesso": True, "codigo": novo_codigo}

    except Exception as e:
        print(f"Erro ao reenviar código: {e}")
        return {"sucesso": False, "erro": "geral"}