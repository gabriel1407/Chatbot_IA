import os
import json
import sqlite3
import logging
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from contextlib import contextmanager
from openIAService.services.cache_service import cache_user_context, get_cached_user_context, invalidate_user_context

DB_PATH = os.path.join('local', 'contextos.db')
if not os.path.exists('local'):
    os.makedirs('local', exist_ok=True)

class ConnectionPool:
    """Pool de conexiones SQLite para mejorar el rendimiento."""
    
    def __init__(self, database_path: str, pool_size: int = 20):
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializa el pool con conexiones."""
        for _ in range(self.pool_size):
            # Reintentos para evitar errores de bloqueo durante el arranque en paralelo
            for attempt in range(10):
                try:
                    conn = sqlite3.connect(self.database_path, check_same_thread=False, timeout=30.0)
                    # Dar tiempo a SQLite cuando hay contención
                    conn.execute("PRAGMA busy_timeout=30000")
                    conn.execute("PRAGMA journal_mode=WAL")  # Mejora el rendimiento y concurrencia
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                    conn.execute("PRAGMA temp_store=MEMORY")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS user_context (
                            user_id TEXT,
                            context_id TEXT,
                            context TEXT,
                            last_updated TIMESTAMP,
                            PRIMARY KEY (user_id, context_id)
                        )
                    """)
                    conn.commit()
                    self.pool.put(conn)
                    break
                except sqlite3.OperationalError as e:
                    logging.warning(f"[DB] SQLite locked during init (attempt {attempt+1}/10): {e}")
                    time.sleep(0.3)
                except Exception as e:
                    logging.error(f"[DB] Error inicializando conexión SQLite: {e}")
                    time.sleep(0.3)
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener una conexión del pool."""
        conn = None
        try:
            conn = self.pool.get(timeout=15)
            yield conn
        except Empty:
            # Si no hay conexiones disponibles, crea una temporal
            logging.warning("[DB] Pool agotado, creando conexión temporal")
            conn = sqlite3.connect(self.database_path, check_same_thread=False)
            yield conn
        finally:
            if conn:
                try:
                    self.pool.put_nowait(conn)
                except:
                    # Si el pool está lleno, cierra la conexión
                    conn.close()

# Instancia global del pool de conexiones
connection_pool = ConnectionPool(DB_PATH, pool_size=20)

def get_active_context_id(user_id):
    """
    Recupera el context_id más recientemente usado por el usuario.
    Si no hay, devuelve 'default'.
    """
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context_id FROM user_context WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1",
                (str(user_id),)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
    except Exception as e:
        logging.error(f"[Context] Error recuperando context_id para usuario {user_id}: {e}")
    return "default"

def load_context(user_id, context_id=None):
    """
    Carga el contexto (historial) de un usuario y un context_id (tema).
    Primero verifica el caché, luego la base de datos.
    """
    if context_id is None:
        context_id = get_active_context_id(user_id)
    
    # Intenta obtener del caché primero
    cached_context = get_cached_user_context(user_id, context_id)
    if cached_context is not None:
        logging.info(f"[Context] Contexto cargado desde caché para usuario {user_id} ({context_id})")
        return cached_context
    
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context FROM user_context WHERE user_id = ? AND context_id = ?",
                (str(user_id), str(context_id))
            )
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    context = json.loads(row[0])
                    # Cachea el contexto para futuras consultas
                    cache_user_context(user_id, context_id, context)
                    logging.info(f"[Context] Contexto cargado desde DB para usuario {user_id} ({context_id})")
                    return context
                except Exception as e:
                    logging.error(f"[Context] Error decodificando JSON de contexto para usuario {user_id} ({context_id}): {e}")
                    save_context(user_id, [], context_id)  # limpia
                    return []
            logging.info(f"[Context] No existe contexto previo para usuario {user_id} ({context_id}).")
            return []
    except Exception as e:
        logging.error(f"[Context] Error cargando contexto de usuario {user_id} desde DB: {e}")
        return []

def save_context(user_id, context, context_id=None):
    """
    Guarda el contexto para un usuario y un context_id (tema).
    También actualiza el caché.
    """
    if context_id is None:
        context_id = "default"
    try:
        context_json = json.dumps(context, ensure_ascii=False)
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_context (user_id, context_id, context, last_updated) VALUES (?, ?, ?, ?)",
                (str(user_id), str(context_id), context_json, datetime.now())
            )
            conn.commit()
        
        # Actualiza el caché
        cache_user_context(user_id, context_id, context)
        logging.info(f"[Context] Contexto guardado para usuario {user_id} ({context_id})")
    except Exception as e:
        logging.error(f"[Context] Error guardando contexto para usuario {user_id} ({context_id}): {e}")

def list_contexts(user_id):
    """
    Lista todos los context_id (temas) existentes para el usuario.
    """
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context_id, last_updated FROM user_context WHERE user_id = ? ORDER BY last_updated DESC",
                (str(user_id),)
            )
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        logging.error(f"[Context] Error listando contextos de usuario {user_id}: {e}")
        return []

def delete_context(user_id, context_id):
    """
    Borra un contexto específico de un usuario.
    También lo elimina del caché.
    """
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_context WHERE user_id = ? AND context_id = ?",
                (str(user_id), str(context_id))
            )
            conn.commit()
        
        # Elimina del caché
        invalidate_user_context(user_id, context_id)
        logging.info(f"[Context] Contexto eliminado para usuario {user_id} ({context_id})")
    except Exception as e:
        logging.error(f"[Context] Error eliminando contexto para usuario {user_id} ({context_id}): {e}")

# Ejemplo de función para detectar nuevo tema (muy simple, ajusta a tu gusto)
def detect_new_topic(user_input):
    """
    Detecta si el usuario quiere empezar un nuevo tema.
    """
    lower_input = user_input.lower()
    keywords = [
        "nuevo tema", "hablemos de", "cambia de tema", "cambiar de tema", "nueva conversación",
        "otro asunto", "otra pregunta", "hablemos sobre", "hablar de", "nuevo tópico",
        "hablar ahora de", "quisiera preguntar sobre", "otra cosa", "cambiar el tema",
        "tema diferente", "empezar otro tema", "start new topic", "change topic", "new conversation",
        "different subject", "let's talk about", "can we talk about", "new subject", "another topic",
        "move on to", "quiero hablar de", "tengo otra duda", "podemos cambiar de tema",
        "ahora quiero preguntar", "otra consulta", "consultar otra cosa", "otra pregunta", "cambiando de tema"
    ]
    return any(phrase in lower_input for phrase in keywords)