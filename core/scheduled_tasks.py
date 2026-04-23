import sqlite3
import json
from datetime import datetime, timedelta
from routes.email_service import enviar_email
from core.config import ServerConfig
import threading
import time

def get_db_path():
    config = ServerConfig()
    return config.db_path

def conectar_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def verificar_pontos_alterados_e_notificar():
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        data_limite = datetime.now() - timedelta(days=1)
        cursor.execute("""
            SELECT id, nome, lat, lng, updated_at
            FROM pontos
            WHERE (updated_at >= ? OR created_at >= ?) AND is_removed = 0
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 50
        """, (data_limite.isoformat(), data_limite.isoformat()))
        
        pontos_alterados = cursor.fetchall()
        
        if not pontos_alterados:
            print("[ScheduledTasks] Nenhum ponto alterado nas últimas 24h")
            conn.close()
            return
        
        print(f"[ScheduledTasks] {len(pontos_alterados)} ponto(s) alterado(s) encontrado(s)")
        
        cursor.execute("""
            SELECT id, email, nome
            FROM utilizadores
            WHERE receber_notificacoes = 1 AND email_verificado = 1 AND tipo = 0
        """)
        
        utilizadores = cursor.fetchall()
        
        if not utilizadores:
            print("[ScheduledTasks] Nenhum utilizador para notificar")
            conn.close()
            return
        
        print(f"[ScheduledTasks] Enviando notificações para {len(utilizadores)} utilizador(es)")
        
        # Enviar emails
        for utilizador in utilizadores:
            contexto = {
                "usuario": utilizador['nome'],
                "pontos": pontos_alterados,
                "total_pontos": len(pontos_alterados),
                "data": datetime.now().strftime("%d/%m/%Y às %H:%M")
            }
            
            enviar_email(
                utilizador['email'],
                "Pontos de Recolha Atualizados - ReciclaTech",
                "notificacao_pontos_atualizados.html",
                contexto=contexto
            )
        
        conn.close()
        print("[ScheduledTasks] Notificações enviadas com sucesso!")
        
    except Exception as e:
        print(f"[ScheduledTasks] Erro ao notificar utilizadores: {e}")

def obter_proxima_execucao():
    agora = datetime.now()
    
    # Próxima meia-noite
    proxima_meia_noite = agora.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    segundos_faltam = (proxima_meia_noite - agora).total_seconds()
    return segundos_faltam, proxima_meia_noite

class ScheduledTaskManager:    
    def __init__(self):
        self.thread = None
        self.ativo = False
    
    def iniciar(self):
        if self.ativo:
            print("[ScheduledTaskManager] Já está ativo")
            return
        
        self.ativo = True
        self.thread = threading.Thread(target=self._loop_verificacao, daemon=True)
        self.thread.start()
        print("[ScheduledTaskManager] Iniciado com sucesso")
    
    def parar(self):
        self.ativo = False
        print("[ScheduledTaskManager] Parado")
    
    def _loop_verificacao(self):
        while self.ativo:
            try:
                segundos_faltam, proxima_exec = obter_proxima_execucao()
                print(f"[ScheduledTaskManager] Próxima execução: {proxima_exec.strftime('%d/%m/%Y às %H:%M:%S')}")
                
                # Aguarda até à próxima execução
                time.sleep(segundos_faltam)
                
                if self.ativo:
                    print("[ScheduledTaskManager] Executando verificação de pontos alterados...")
                    verificar_pontos_alterados_e_notificar()
                    
            except Exception as e:
                print(f"[ScheduledTaskManager] Erro no loop: {e}")
                # Aguarda 1 minuto antes de tentar novamente
                time.sleep(60)

# Instância global
task_manager = ScheduledTaskManager()
