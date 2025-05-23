import os
import json
import sqlite3
import logging

DB_PATH = os.path.join('local', 'contextos.db')
if not os.path.exists('local'):
    os.makedirs('local')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_context (
            user_id TEXT PRIMARY KEY,
            context TEXT
        )
    """)
    return conn

def load_context(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT context FROM user_context WHERE user_id = ?", (str(user_id),))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            try:
                context = json.loads(row[0])
                logging.info(f"[Context] Contexto cargado para usuario {user_id}: {context}")
                return context
            except Exception as e:
                logging.error(f"[Context] Error decodificando JSON de contexto para usuario {user_id}: {e}")
                # Limpia el contexto corrupto
                save_context(user_id, [])
                return []
        logging.info(f"[Context] No existe contexto previo para usuario {user_id}.")
        return []
    except Exception as e:
        logging.error(f"[Context] Error cargando contexto de usuario {user_id} desde DB: {e}")
        return []

def save_context(user_id, context):
    try:
        context_json = json.dumps(context, ensure_ascii=False)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_context (user_id, context) VALUES (?, ?)",
            (str(user_id), context_json)
        )
        conn.commit()
        conn.close()
        logging.info(f"[Context] Contexto guardado para usuario {user_id}: {context}")
    except Exception as e:
        logging.error(f"[Context] Error guardando contexto para usuario {user_id}: {e}")
