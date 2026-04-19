import sys
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from seguranca import encrypt_password

def limpar_e_reiniciar_banco():
    caminho_banco = os.path.join(os.path.dirname(__file__), "..", "banco.db")
    if not os.path.exists(caminho_banco):
        caminho_banco = "banco.db"

    print(f"Limpando o banco: {os.path.abspath(caminho_banco)}")

    conexao = sqlite3.connect(caminho_banco)
    cursor = conexao.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tabelas = cursor.fetchall()

    for tabela in tabelas:
        cursor.execute(f'DROP TABLE IF EXISTS "{tabela[0]}";')

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE utilizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('admin','utilizador')),
    regiao TEXT NOT NULL,
    receber_notificacoes INTEGER NOT NULL DEFAULT 1 CHECK (receber_notificacoes IN (0,1)),
    email_verificado INTEGER NOT NULL DEFAULT 0,
    codigo_verificacao TEXT,
    data_registo DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    
    
    cursor.execute("""
    CREATE TABLE pontos_recolha (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        horario TEXT,
        contacto TEXT,
        website TEXT,
        descricao TEXT,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER,
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE tipos_residuos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        instrucoes_descarte TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE ponto_residuo (
        ponto_id INTEGER NOT NULL,
        residuo_id INTEGER NOT NULL,
        PRIMARY KEY (ponto_id, residuo_id),
        FOREIGN KEY (ponto_id) REFERENCES pontos_recolha(id) ON DELETE CASCADE,
        FOREIGN KEY (residuo_id) REFERENCES tipos_residuos(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE graficos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('barra')),
        descricao TEXT,
        fonte_geral TEXT,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER,
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE estatisticas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grafico_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT,
        fonte TEXT,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (grafico_id) REFERENCES graficos(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE dados_grafico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estatistica_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        valor REAL NOT NULL,
        fonte TEXT,
        ordem INTEGER,
        FOREIGN KEY (estatistica_id) REFERENCES estatisticas(id) ON DELETE CASCADE
    )
    """)

    senha_admin = encrypt_password("123")
    cursor.execute("""
    INSERT INTO utilizadores (nome, email, password_hash, tipo, regiao, receber_notificacoes)
    VALUES (?, ?, ?, ?, ?, ?)
    """, ("Administrador ReciclaTech Lisboa", "admin.ReciclaTech@gmail.com", senha_admin, "admin", "centro", 1))

    conexao.commit()
    conexao.close()
    print(" Banco recriado com sucesso!")

if __name__ == "__main__":
    confirmar = input("Isso apagará TODOS os dados. Tem certeza? (s/n): ")
    if confirmar.lower() == 's':
        limpar_e_reiniciar_banco()
    else:
        print("Operação cancelada.")