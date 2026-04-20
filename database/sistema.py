import secrets
import string
from datetime import datetime, timedelta
from seguranca import encrypt_password, decrypt_password
from routes.email_service import enviar_email_verificacao
from core.config import ServerConfig
from core.database import DatabaseManager
import os
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        config = ServerConfig()
        _db_manager = DatabaseManager(config.db_path)
    return _db_manager


def gerar_codigo():
    caracteres = string.digits + string.ascii_uppercase
    parte1 = ''.join(secrets.choice(caracteres) for _ in range(6))
    parte2 = ''.join(secrets.choice(caracteres) for _ in range(6))
    return f"{parte1}-{parte2}"


def registrar_usuario(nome, email, senha, receber_notificacoes):
    db = get_db_manager()
    
    senha_cript = encrypt_password(senha)
    receber = 1 if receber_notificacoes else 0
    codigo_verificacao = gerar_codigo()
    agora = datetime.now().isoformat()

    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            
            # Inserir utilizador
            cursor.execute("""
                INSERT INTO utilizadores
                (nome, email, password_hash, tipo, receber_notificacoes)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, email, senha_cript, 0, receber))  # tipo 0 = utilizador
            
            usuario_id = cursor.lastrowid
            
            # Inserir código de verificação
            cursor.execute("""
                INSERT INTO verificacao_email
                (utilizador_id, codigo, criado_em)
                VALUES (?, ?, ?)
            """, (usuario_id, codigo_verificacao, agora))

        email_enviado = enviar_email_verificacao(email, nome, codigo_verificacao)
        if not email_enviado:
            print(f"[REGISTO] Falha ao enviar email de verificação para {email}.")
            return {"sucesso": False, "erro": "email_nao_enviado"}

        print(f"[REGISTO] Utilizador {nome} ({email}) registado com sucesso. Código enviado.")
        return {"sucesso": True, "user_id": usuario_id}

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
                SELECT u.id, u.nome, u.password_hash, u.tipo, u.email_verificado, ve.codigo
                FROM utilizadores u
                LEFT JOIN verificacao_email ve ON u.id = ve.utilizador_id
                WHERE u.email = ?
            """, (email,))
            user = cursor.fetchone()

            if user:
                # Se email não verificado
                if user["email_verificado"] == 0:
                    if user["codigo"]:  # Tem código pendente
                        tempo_criacao = datetime.fromisoformat(user["codigo"])
                        if datetime.now() - tempo_criacao > timedelta(hours=24):
                            return {"erro": "codigo_expirado"}
                    return {"erro": "email_nao_verificado"}

                senha_bd = decrypt_password(user["password_hash"])

                if senha_input == senha_bd:
                    return {
                        "id": user["id"],
                        "nome": user["nome"],
                        "tipo": user["tipo"],  # 0 = utilizador, 1 = admin
                        "email": email
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
                SELECT u.id, u.email_verificado, ve.codigo, ve.criado_em
                FROM utilizadores u
                LEFT JOIN verificacao_email ve ON u.id = ve.utilizador_id
                WHERE u.email = ?
            """, (email,))
            user = cursor.fetchone()

            if not user or not user["codigo"] or user["codigo"].upper() != codigo.upper():
                return False

            # Verificar se código expirou
            if user["criado_em"]:
                tempo_criacao = datetime.fromisoformat(user["criado_em"])
                if datetime.now() - tempo_criacao > timedelta(hours=24):
                    return False

            # Marcar email como verificado e limpar código
            cursor.execute("""
                UPDATE utilizadores
                SET email_verificado = 1
                WHERE id = ?
            """, (user["id"],))
            
            cursor.execute("""
                DELETE FROM verificacao_email
                WHERE utilizador_id = ?
            """, (user["id"],))

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
                SELECT u.id, u.nome, u.email_verificado
                FROM utilizadores u
                WHERE u.email = ?
            """, (email,))
            user = cursor.fetchone()

            if not user:
                return {"sucesso": False, "erro": "usuario_nao_encontrado"}

            if user["email_verificado"] == 1:
                return {"sucesso": False, "erro": "email_ja_verificado"}

            # Atualizar ou criar código de verificação
            cursor.execute("""
                UPDATE verificacao_email
                SET codigo = ?, criado_em = ?
                WHERE utilizador_id = ?
            """, (novo_codigo, agora, user["id"]))
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO verificacao_email
                    (utilizador_id, codigo, criado_em)
                    VALUES (?, ?, ?)
                """, (user["id"], novo_codigo, agora))

            email_enviado = enviar_email_verificacao(email, user["nome"], novo_codigo)
            if not email_enviado:
                print(f"Falha ao reenviar código para {email}.")
                return {"sucesso": False, "erro": "email_nao_enviado"}

            return {"sucesso": True}

    except Exception as e:
        print(f"Erro ao reenviar código: {e}")
        return {"sucesso": False, "erro": "geral"}


def solicitar_reset_senha(email):
    from routes.email_service import enviar_email_reset_senha
    
    db = get_db_manager()
    
    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            
            # Procurar utilizador verificado
            cursor.execute("""
                SELECT id, nome FROM utilizadores
                WHERE email = ? AND email_verificado = 1
            """, (email,))
            user = cursor.fetchone()

            if not user:
                return {"sucesso": False, "erro": "email_nao_verificado"}

            codigo_reset = gerar_codigo()
            agora = datetime.now().isoformat()
            
            # Inserir código de reset
            cursor.execute("""
                INSERT INTO reset_senha
                (utilizador_id, codigo, criado_em)
                VALUES (?, ?, ?)
            """, (user["id"], codigo_reset, agora))

            # Enviar email
            email_enviado = enviar_email_reset_senha(email, user["nome"], codigo_reset)
            if not email_enviado:
                return {"sucesso": False, "erro": "email_nao_enviado"}

            return {"sucesso": True}

    except Exception as e:
        print(f"Erro ao solicitar reset de senha: {e}")
        return {"sucesso": False, "erro": "geral"}


def reset_senha_com_codigo(email, codigo, nova_senha):
    db = get_db_manager()
    
    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            
            # Procurar utilizador e código
            cursor.execute("""
                SELECT u.id, rs.id as reset_id, rs.criado_em
                FROM utilizadores u
                JOIN reset_senha rs ON u.id = rs.utilizador_id
                WHERE u.email = ? AND rs.codigo = ? AND rs.utilizado = 0
            """, (email, codigo))
            result = cursor.fetchone()

            if not result:
                return {"sucesso": False, "erro": "codigo_invalido"}

            # Verificar se código expirou (24 horas)
            tempo_criacao = datetime.fromisoformat(result["criado_em"])
            if datetime.now() - tempo_criacao > timedelta(hours=24):
                return {"sucesso": False, "erro": "codigo_expirado"}

            # Atualizar senha
            nova_senha_cript = encrypt_password(nova_senha)
            cursor.execute("""
                UPDATE utilizadores
                SET password_hash = ?
                WHERE id = ?
            """, (nova_senha_cript, result["id"]))
            
            # Marcar código como utilizado
            cursor.execute("""
                UPDATE reset_senha
                SET utilizado = 1
                WHERE id = ?
            """, (result["reset_id"],))

            return {"sucesso": True}

    except Exception as e:
        print(f"Erro ao resetar senha: {e}")
        return {"sucesso": False, "erro": "geral"}


def criar_admin_se_nao_existir():
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        print("[Sistema] ADMIN_PASSWORD não definido no .env, pulando criação de admin.")
        return False
    
    db = get_db_manager()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@reciclatech.pt")
    
    try:
        with db.connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se admin já existe
            cursor.execute("""
                SELECT id FROM utilizadores WHERE tipo = 1
            """)
            
            if cursor.fetchone():
                print("[Sistema] Admin já existe, pulando inicialização.")
                return False
            
            # Criar admin
            admin_pass_cript = encrypt_password(admin_password)
            cursor.execute("""
                INSERT INTO utilizadores
                (nome, email, password_hash, tipo, receber_notificacoes, email_verificado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Administrador", admin_email, admin_pass_cript, 1, 1, 1))  # tipo 1 = admin
            
            print(f"[Sistema] Admin criado com sucesso! Email: {admin_email}")
            return True
        
    except Exception as e:
        print(f"[Sistema] Erro ao criar admin: {e}")
        return False