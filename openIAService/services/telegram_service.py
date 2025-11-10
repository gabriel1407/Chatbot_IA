import requests
from decouple import config
from services.openia_service import handle_text_message
from services.files_processing_service import process_image, process_audio, process_document
from services.context_service_adapter import (
    load_context,
    detect_new_topic,
    get_active_context_id
)
from core.logging.logger import get_telegram_logger

# Usar el nuevo sistema de logging centralizado
telegram_logger = get_telegram_logger()

TELEGRAM_TOKEN = config('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_telegram_message(chat_id, text):
    """
    Envía un mensaje de texto a Telegram.
    
    Args:
        chat_id: ID del chat
        text: Texto a enviar
        
    Returns:
        bool: True si se envió exitosamente
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload)
        telegram_logger.info(f"Mensaje enviado a chat {chat_id}: {response.status_code}")
        telegram_logger.debug(f"Respuesta de Telegram API: {response.text}")
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
        local_path = f"local/uploads/{file_id}.{file_ext}"
        file_data = requests.get(file_url).content
        with open(local_path, "wb") as f:
            f.write(file_data)
        telegram_logger.info(f"Archivo descargado: {local_path}")
        return local_path
    except Exception as e:
        telegram_logger.error(f"Error en download_telegram_file: {e}")
        return None

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
            response_text = handle_text_message(caption, chat_id, image_path=file_path, context_id=context_id)

        elif "audio" in message or "voice" in message:
            audio = message.get("audio") or message.get("voice")
            file_id = audio["file_id"]
            file_path = download_telegram_file(file_id, "ogg")
            extracted_text = process_audio(file_path, 'es')
            if detect_new_topic(extracted_text):
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            context = load_context(chat_id, context_id)
            response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)

        elif "document" in message:
            document = message["document"]
            file_id = document["file_id"]
            mime_type = document.get("mime_type", "")
            file_ext = "pdf" if "pdf" in mime_type else "docx" if "word" in mime_type else None
            if file_ext:
                file_path = download_telegram_file(file_id, file_ext)
                extracted_text = process_document(file_path, file_ext)
                if detect_new_topic(extracted_text):
                    from datetime import datetime
                    context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                context = load_context(chat_id, context_id)
                response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)
            else:
                response_text = "Formato de documento no soportado."
        else:
            telegram_logger.warning(f"Tipo de mensaje no reconocido de {chat_id}: {message}")
            response_text = "Mensaje no reconocido."

        send_telegram_message(chat_id, response_text)
        telegram_logger.info(f"Respuesta enviada a {chat_id}: {response_text}")
    except Exception as e:
        telegram_logger.error(f"Error en process_telegram_update: {e}")
