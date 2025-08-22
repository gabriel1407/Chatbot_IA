import requests
import logging
from decouple import config
from openIAService.services.openia_service import handle_text_message
from openIAService.services.files_processing_service import process_image, process_audio, process_document
from openIAService.services.context_service import (
    load_context,
    detect_new_topic,
    get_active_context_id
)
from openIAService.services.metrics_service import log_user_interaction, measure_time
from openIAService.services.task_queue_service import submit_task_by_name

# Logger específico para Telegram (stdout para Docker)
telegram_logger = logging.getLogger("telegram")
telegram_handler = logging.StreamHandler()
telegram_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
telegram_handler.setFormatter(telegram_formatter)
telegram_logger.setLevel(logging.INFO)
if not telegram_logger.hasHandlers():
    telegram_logger.addHandler(telegram_handler)

TELEGRAM_TOKEN = config('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload)
        telegram_logger.info(f"Respuesta de Telegram API: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        telegram_logger.error(f"Error en send_telegram_message: {e}")
        return False

def download_telegram_file(file_id, file_ext):
    """Descarga archivos multimedia de Telegram."""
    try:
        file_info = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        # Asegura que el directorio exista
        import os
        upload_dir = "local/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        local_path = f"{upload_dir}/{file_id}.{file_ext}"
        file_data = requests.get(file_url).content
        with open(local_path, "wb") as f:
            f.write(file_data)
        telegram_logger.info(f"Archivo descargado: {local_path}")
        return local_path
    except Exception as e:
        telegram_logger.error(f"Error en download_telegram_file: {e}")
        return None

@measure_time("telegram_process_update")
def process_telegram_update(update):
    try:
        telegram_logger.info(f"Nuevo update recibido: {update}")
        message = update.get("message")
        if not message:
            telegram_logger.warning("Update recibido sin mensaje.")
            return
        chat_id = str(message["chat"]["id"])

        # Contexto activo (tema actual)
        context_id = get_active_context_id(chat_id)

        if "text" in message:
            user_text = message["text"]
            if detect_new_topic(user_text):
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                # No envíes ningún mensaje de aviso
            context = load_context(chat_id, context_id)
            telegram_logger.info(f"Mensaje de texto recibido de {chat_id}: {user_text}")
            try:
                log_user_interaction(chat_id, "telegram", "text")
            except Exception:
                pass
            response_text = handle_text_message(user_text, chat_id, context_id=context_id)

        elif "photo" in message:
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            caption = message.get("caption", "")
            if detect_new_topic(caption):
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            context = load_context(chat_id, context_id)
            file_path = download_telegram_file(file_id, "jpg")
            try:
                log_user_interaction(chat_id, "telegram", "photo")
            except Exception:
                pass
            # Ack inmediato y procesamiento asíncrono mediante tarea importable
            send_telegram_message(chat_id, "Procesando tu imagen...")
            telegram_logger.info(f"[ENQUEUE] TG photo chat_id={chat_id} context_id={context_id} file_path={file_path}")
            submit_task_by_name(
                "openIAService.services.tasks:process_telegram_photo",
                str(chat_id), str(context_id), str(caption or ""), str(file_path or "")
            )
            response_text = ""

        elif "audio" in message or "voice" in message:
            audio = message.get("audio") or message.get("voice")
            file_id = audio["file_id"]
            file_path = download_telegram_file(file_id, "ogg")
            try:
                log_user_interaction(chat_id, "telegram", "audio")
            except Exception:
                pass
            # Ack inmediato y procesamiento asíncrono mediante tarea importable
            send_telegram_message(chat_id, "Procesando tu audio...")
            telegram_logger.info(f"[ENQUEUE] TG audio chat_id={chat_id} context_id={context_id} file_path={file_path}")
            submit_task_by_name(
                "openIAService.services.tasks:process_telegram_audio",
                str(chat_id), str(context_id), str(file_path or "")
            )
            response_text = ""

        elif "document" in message:
            document = message["document"]
            file_id = document["file_id"]
            mime_type = document.get("mime_type", "")
            file_ext = "pdf" if "pdf" in mime_type else "docx" if "word" in mime_type else None
            if file_ext:
                file_path = download_telegram_file(file_id, file_ext)
                try:
                    log_user_interaction(chat_id, "telegram", "document")
                except Exception:
                    pass
                # Ack inmediato y procesamiento asíncrono mediante tarea importable
                send_telegram_message(chat_id, "Procesando tu documento...")
                telegram_logger.info(f"[ENQUEUE] TG document chat_id={chat_id} context_id={context_id} file_path={file_path} ext={file_ext}")
                submit_task_by_name(
                    "openIAService.services.tasks:process_telegram_document",
                    str(chat_id), str(context_id), str(file_path or ""), str(file_ext)
                )
                response_text = ""
            else:
                response_text = "Formato de documento no soportado."
        else:
            telegram_logger.warning(f"Tipo de mensaje no reconocido de {chat_id}: {message}")
            response_text = "Mensaje no reconocido."

        if response_text and response_text.strip():
            send_telegram_message(chat_id, response_text)
            telegram_logger.info(f"Respuesta enviada a {chat_id}: {response_text}")
        else:
            telegram_logger.warning(f"Respuesta vacía generada para {chat_id}, enviando mensaje por defecto")
            send_telegram_message(chat_id, "Lo siento, no pude procesar tu mensaje correctamente. Por favor, inténtalo de nuevo.")
    except Exception as e:
        telegram_logger.error(f"Error en process_telegram_update: {e}")
        try:
            send_telegram_message(chat_id, "Ocurrió un error procesando tu mensaje. Por favor, inténtalo más tarde.")
        except:
            pass
