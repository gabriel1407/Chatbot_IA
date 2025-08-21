import logging
from openIAService.services.openia_service import handle_text_message
from openIAService.services.files_processing_service import process_audio, process_document
from openIAService.services.context_service import load_context, detect_new_topic
from openIAService.services.whatsapp_service import create_text_message, send_whatsapp_message
from openIAService.services.telegram_service import send_telegram_message

# WhatsApp tasks

def process_whatsapp_image(recipient: str, context_id: str, caption: str, file_path: str):
    try:
        context = load_context(recipient, context_id)
        response_text = handle_text_message(caption, recipient, image_path=file_path, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
    except Exception as e:
        logging.error(f"[TASK] WA image error: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu imagen."))


def process_whatsapp_audio(recipient: str, context_id: str, file_path: str):
    try:
        extracted_text = process_audio(file_path, 'es')
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(recipient, context_id)
        response_text = handle_text_message(extracted_text, recipient, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
    except Exception as e:
        logging.error(f"[TASK] WA audio error: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu audio."))


def process_whatsapp_document(recipient: str, context_id: str, file_path: str, file_extension: str):
    try:
        extracted_text = process_document(file_path, file_extension)
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(recipient, context_id)
        response_text = handle_text_message(extracted_text, recipient, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
    except Exception as e:
        logging.error(f"[TASK] WA document error: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu documento."))

# Telegram tasks

def process_telegram_photo(chat_id: str, context_id: str, caption: str, file_path: str):
    try:
        response_text = handle_text_message(caption, chat_id, image_path=file_path, context_id=context_id)
        send_telegram_message(chat_id, response_text)
    except Exception as e:
        logging.error(f"[TASK] TG photo error: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu imagen.")


def process_telegram_audio(chat_id: str, context_id: str, file_path: str):
    try:
        extracted_text = process_audio(file_path, 'es')
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(chat_id, context_id)
        response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)
        send_telegram_message(chat_id, response_text)
    except Exception as e:
        logging.error(f"[TASK] TG audio error: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu audio.")


def process_telegram_document(chat_id: str, context_id: str, file_path: str, file_ext: str):
    try:
        extracted_text = process_document(file_path, file_ext)
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(chat_id, context_id)
        response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)
        send_telegram_message(chat_id, response_text)
    except Exception as e:
        logging.error(f"[TASK] TG document error: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu documento.")
