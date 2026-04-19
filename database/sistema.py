import sqlite3
import secrets
from seguranca import encrypt_password, decrypt_password
from routes.email_service import enviar_email_verificacao

DB_PATH = "banco.db"


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def gerar_codigo():
    return str(secrets.randbelow(900000) + 100000)


def registrar_usuario(nome, email, senha, regiao, receber_notificacoes):
    conn = conectar()
    cursor = conn.cursor()

    senha_cript = encrypt_password(senha)
    receber = 1 if receber_notificacoes else 0
    codigo_verificacao = gerar_codigo()

    try:
        cursor.execute("""
            INSERT INTO utilizadores
            (nome, email, password_hash, tipo, regiao, receber_notificacoes, codigo_verificacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, email, senha_cript, "utilizador", regiao, receber, codigo_verificacao))

        email_enviado = enviar_email_verificacao(email, nome, codigo_verificacao)
        if not email_enviado:
            conn.rollback()
            print(f"Falha ao enviar o email de verificação para {email}.")
            return {"sucesso": False, "erro": "email_nao_enviado"}

        conn.commit()
        return {"sucesso": True}

    except sqlite3.IntegrityError:
        conn.rollback()
        return {"sucesso": False, "erro": "email_ja_registado"}

    except Exception as e:
        conn.rollback()
        print(f"Erro ao registrar usuário: {e}")
        return {"sucesso": False, "erro": "geral"}

    finally:
        conn.close()


def verificar_login(email, senha_input):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, nome, password_hash, tipo, codigo_verificacao
            FROM utilizadores
            WHERE email = ?
        """, (email,))
        user = cursor.fetchone()

        if user:
            if user["codigo_verificacao"] is not None:
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

    finally:
        conn.close()

    return None


def confirmar_email_por_codigo(email, codigo):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE utilizadores
            SET codigo_verificacao = NULL, email_verificado = 1
            WHERE email = ? AND codigo_verificacao = ?
        """, (email, codigo))

        conn.commit()

        return cursor.rowcount > 0

    except Exception as e:
        print(f"Erro ao confirmar email por código: {e}")
        return False

    finally:
        conn.close()


def confirmar_email_por_token(token):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE utilizadores
            SET codigo_verificacao = NULL, email_verificado = 1
            WHERE codigo_verificacao = ?
        """, (token,))

        conn.commit()

        return cursor.rowcount > 0

    except Exception as e:
        print(f"Erro ao confirmar email: {e}")
        return False

    finally:
        conn.close()