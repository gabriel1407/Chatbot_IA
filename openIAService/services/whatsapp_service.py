import requests
import json
import logging
from decouple import config
from services.openia_service import handle_text_message
from services.files_processing_service import process_image, process_audio, process_document

TOKEN_WHATSAPP = config('TOKEN_WHATSAPP')
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/245533201976802/messages"

def send_whatsapp_message(body):
    """Envía un mensaje a WhatsApp mediante la API de Facebook."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN_WHATSAPP}"
        }
        response = requests.post(WHATSAPP_API_URL, data=json.dumps(body), headers=headers)
        logging.info(f"Respuesta de WhatsApp API: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error en send_whatsapp_message: {e}")
        return False

def create_text_message(recipient, message):
    """Crea un mensaje de texto para WhatsApp."""
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": message}
    }

def process_individual_message(message):
    """Procesa un mensaje recibido desde WhatsApp."""
    try:
        recipient = message.get("from")
        if not recipient:
            logging.error("Mensaje recibido sin número de remitente.")
            return

        if "text" in message:
            text = message["text"].get("body", "Texto no disponible")
            response_text = handle_text_message(text, recipient)
        elif "image" in message:
            image_id = message["image"]["id"]
            caption = message["image"].get("caption", "")
            file_path = download_media(image_id, "image/jpeg")
            # Usa el caption y la imagen para GPT-4o (visión)
            response_text = handle_text_message(caption, recipient, image_path=file_path)
        elif "audio" in message:
            audio_id = message["audio"]["id"]
            file_path = download_media(audio_id, "audio/ogg")
            extracted_text = process_audio(file_path, 'es')
            response_text = handle_text_message(extracted_text, recipient)
        elif "document" in message:
            document_id = message["document"]["id"]
            mime_type = message["document"].get("mime_type", "")
            file_extension = "pdf" if "pdf" in mime_type else "docx" if "word" in mime_type else None
            if file_extension:
                file_path = download_media(document_id, f"application/{file_extension}")
                extracted_text = process_document(file_path, file_extension)
                response_text = handle_text_message(extracted_text, recipient)
            else:
                response_text = "Formato de documento no soportado."
        else:
            response_text = "Mensaje no reconocido."

        response_message = create_text_message(recipient, response_text)
        send_whatsapp_message(response_message)
    except Exception as e:
        logging.error(f"Error en process_individual_message: {e}")

        
        
def download_media(media_id, media_type):
    """Descarga archivos multimedia de WhatsApp."""
    try:
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {"Authorization": f"Bearer {TOKEN_WHATSAPP}"}
        response = requests.get(url, headers=headers)
        media_url = response.json().get('url')
        media_response = requests.get(media_url, headers=headers)
        file_path = f"local/uploads/{media_id}.{media_type.split('/')[-1]}"
        with open(file_path, 'wb') as f:
            f.write(media_response.content)
        logging.info(f"Archivo descargado: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Error en download_media: {e}")
        return None
