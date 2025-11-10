import requests
import json
from decouple import config
from services.openia_service import handle_text_message
from services.files_processing_service import process_image, process_audio, process_document
from services.context_service_adapter import load_context, save_context, detect_new_topic, get_active_context_id
from core.logging.logger import get_whatsapp_logger

# Usar el nuevo sistema de logging centralizado
whatsapp_logger = get_whatsapp_logger()

TOKEN_WHATSAPP = config('TOKEN_WHATSAPP')
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/245533201976802/messages"

def send_whatsapp_message(body):
    """
    Envía un mensaje a WhatsApp mediante la API de Facebook.
    
    Args:
        body: Cuerpo del mensaje en formato dict
        
    Returns:
        bool: True si se envió exitosamente
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN_WHATSAPP}"
        }
        response = requests.post(WHATSAPP_API_URL, data=json.dumps(body), headers=headers)
        whatsapp_logger.info(f"Mensaje enviado a WhatsApp: {response.status_code}")
        whatsapp_logger.debug(f"Respuesta de WhatsApp API: {response.text}")
        return response.status_code == 200
    except Exception as e:
        whatsapp_logger.error(f"Error en send_whatsapp_message: {e}")
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
    """
    Procesa un mensaje recibido desde WhatsApp manteniendo el contexto por tema/conversación.
    """
    try:
        recipient = message.get("from")
        if not recipient:
            whatsapp_logger.error("Mensaje recibido sin número de remitente.")
            return

        # Por defecto, context_id es "default"
        context_id = get_active_context_id(recipient)

        # Detectar nuevo tema (puedes mejorar el trigger, aquí solo un ejemplo)
        user_text = None
        if "text" in message:
            user_text = message["text"].get("body", "")
            if detect_new_topic(user_text):
                # Crea un nuevo context_id basado en timestamp o un nombre
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                # Opcional: puedes avisar al usuario
                send_whatsapp_message(create_text_message(
                    recipient, ""
                ))
            # Carga el contexto actual (tema)
            context = load_context(recipient, context_id)
            response_text = handle_text_message(user_text, recipient, context_id=context_id)
            # No guardes aún, lo hace handle_text_message si lo tienes así, si no, guárdalo aquí

        elif "image" in message:
            image_id = message["image"]["id"]
            caption = message["image"].get("caption", "")
            file_path = download_media(image_id, "image/jpeg")
            if detect_new_topic(caption):
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                send_whatsapp_message(create_text_message(
                    recipient, ""
                ))
            context = load_context(recipient, context_id)
            response_text = handle_text_message(caption, recipient, image_path=file_path, context_id=context_id)

        elif "audio" in message:
            audio_id = message["audio"]["id"]
            file_path = download_media(audio_id, "audio/ogg")
            extracted_text = process_audio(file_path, 'es')
            if detect_new_topic(extracted_text):
                from datetime import datetime
                context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                send_whatsapp_message(create_text_message(
                    recipient, ""
                ))
            context = load_context(recipient, context_id)
            response_text = handle_text_message(extracted_text, recipient, context_id=context_id)

        elif "document" in message:
            document_id = message["document"]["id"]
            mime_type = message["document"].get("mime_type", "")
            file_extension = "pdf" if "pdf" in mime_type else "docx" if "word" in mime_type else None
            if file_extension:
                file_path = download_media(document_id, f"application/{file_extension}")
                extracted_text = process_document(file_path, file_extension)
                if detect_new_topic(extracted_text):
                    from datetime import datetime
                    context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    send_whatsapp_message(create_text_message(
                        recipient, ""
                    ))
                context = load_context(recipient, context_id)
                response_text = handle_text_message(extracted_text, recipient, context_id=context_id)
            else:
                response_text = "Formato de documento no soportado."
        else:
            response_text = "Mensaje no reconocido."

        response_message = create_text_message(recipient, response_text)
        send_whatsapp_message(response_message)
    except Exception as e:
        whatsapp_logger.error(f"Error en process_individual_message: {e}")


        
        
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
        whatsapp_logger.info(f"Archivo descargado: {file_path}")
        return file_path
    except Exception as e:
        whatsapp_logger.error(f"Error en download_media: {e}")
        return None
