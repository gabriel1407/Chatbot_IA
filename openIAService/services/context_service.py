import os
import json
import sqlite3
import logging
from datetime import datetime

DB_PATH = os.path.join('local', 'contextos.db')
if not os.path.exists('local'):
    os.makedirs('local')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_context (
            user_id TEXT,
            context_id TEXT,
            context TEXT,
            last_updated TIMESTAMP,
            PRIMARY KEY (user_id, context_id)
        )
    """)
    return conn

def get_active_context_id(user_id):
    """
    Recupera el context_id más recientemente usado por el usuario.
    Si no hay, devuelve 'default'.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context_id FROM user_context WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1",
            (str(user_id),)
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception as e:
        logging.error(f"[Context] Error recuperando context_id para usuario {user_id}: {e}")
    return "default"

def load_context(user_id, context_id=None):
    """
    Carga el contexto (historial) de un usuario y un context_id (tema).
    """
    if context_id is None:
        context_id = get_active_context_id(user_id)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context FROM user_context WHERE user_id = ? AND context_id = ?",
            (str(user_id), str(context_id))
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            try:
                context = json.loads(row[0])
                logging.info(f"[Context] Contexto cargado para usuario {user_id} ({context_id}): {context}")
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
    """
    if context_id is None:
        context_id = "default"
    try:
        context_json = json.dumps(context, ensure_ascii=False)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_context (user_id, context_id, context, last_updated) VALUES (?, ?, ?, ?)",
            (str(user_id), str(context_id), context_json, datetime.now())
        )
        conn.commit()
        conn.close()
        logging.info(f"[Context] Contexto guardado para usuario {user_id} ({context_id}): {context}")
    except Exception as e:
        logging.error(f"[Context] Error guardando contexto para usuario {user_id} ({context_id}): {e}")

def list_contexts(user_id):
    """
    Lista todos los context_id (temas) existentes para el usuario.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context_id, last_updated FROM user_context WHERE user_id = ? ORDER BY last_updated DESC",
            (str(user_id),)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logging.error(f"[Context] Error listando contextos de usuario {user_id}: {e}")
        return []

def delete_context(user_id, context_id):
    """
    Borra un contexto específico de un usuario.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_context WHERE user_id = ? AND context_id = ?",
            (str(user_id), str(context_id))
        )
        conn.commit()
        conn.close()
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