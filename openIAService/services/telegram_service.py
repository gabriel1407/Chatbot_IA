import requests
import logging
from decouple import config
from services.openia_service import handle_text_message
from services.files_processing_service import process_image, process_audio, process_document

# Logger específico para Telegram
telegram_logger = logging.getLogger("telegram")
telegram_handler = logging.FileHandler("telegram.log")
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
        chat_id = message["chat"]["id"]

        if "text" in message:
            user_text = message["text"]
            telegram_logger.info(f"Mensaje de texto recibido de {chat_id}: {user_text}")
            response_text = handle_text_message(user_text, str(chat_id))
        elif "photo" in message:
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            caption = message.get("caption", "")
            telegram_logger.info(f"Foto recibida de {chat_id}, file_id: {file_id}, caption: {caption}")
            file_path = download_telegram_file(file_id, "jpg")
            # Ahora sí pasas el caption y el path de la imagen juntos
            response_text = handle_text_message(caption, str(chat_id), image_path=file_path)

        elif "audio" in message or "voice" in message:
            audio = message.get("audio") or message.get("voice")
            file_id = audio["file_id"]
            telegram_logger.info(f"Audio recibido de {chat_id}, file_id: {file_id}")
            file_path = download_telegram_file(file_id, "ogg")
            extracted_text = process_audio(file_path, 'es')
            response_text = handle_text_message(extracted_text, str(chat_id))
        elif "document" in message:
            document = message["document"]
            file_id = document["file_id"]
            mime_type = document.get("mime_type", "")
            telegram_logger.info(f"Documento recibido de {chat_id}, file_id: {file_id}, mime_type: {mime_type}")
            file_ext = "pdf" if "pdf" in mime_type else "docx" if "word" in mime_type else None
            if file_ext:
                file_path = download_telegram_file(file_id, file_ext)
                extracted_text = process_document(file_path, file_ext)
                response_text = handle_text_message(extracted_text, str(chat_id))
            else:
                response_text = "Formato de documento no soportado."
        else:
            telegram_logger.warning(f"Tipo de mensaje no reconocido de {chat_id}: {message}")
            response_text = "Mensaje no reconocido."

        send_telegram_message(chat_id, response_text)
        telegram_logger.info(f"Respuesta enviada a {chat_id}: {response_text}")
    except Exception as e:
        telegram_logger.error(f"Error en process_telegram_update: {e}")