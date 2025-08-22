import logging
from openIAService.services.openia_service import handle_text_message
from openIAService.services.files_processing_service import process_audio, process_document
from openIAService.services.context_service import load_context, detect_new_topic
from openIAService.services.whatsapp_service import create_text_message, send_whatsapp_message
from openIAService.services.telegram_service import send_telegram_message

# WhatsApp tasks

def process_whatsapp_image(recipient: str, context_id: str, caption: str, file_path: str):
    logging.info(f"[TASK] WA image START recipient={recipient} context_id={context_id} file_path={file_path}")
    try:
        context = load_context(recipient, context_id)
        response_text = handle_text_message(caption, recipient, image_path=file_path, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
        logging.info(f"[TASK] WA image DONE recipient={recipient} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] WA image error recipient={recipient} context_id={context_id}: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu imagen."))


def process_whatsapp_audio(recipient: str, context_id: str, file_path: str):
    logging.info(f"[TASK] WA audio START recipient={recipient} context_id={context_id} file_path={file_path}")
    try:
        extracted_text = process_audio(file_path, 'es')
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(recipient, context_id)
        response_text = handle_text_message(extracted_text, recipient, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
        logging.info(f"[TASK] WA audio DONE recipient={recipient} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] WA audio error recipient={recipient} context_id={context_id}: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu audio."))


def process_whatsapp_document(recipient: str, context_id: str, file_path: str, file_extension: str):
    logging.info(f"[TASK] WA document START recipient={recipient} context_id={context_id} file_path={file_path} ext={file_extension}")
    try:
        extracted_text = process_document(file_path, file_extension)
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(recipient, context_id)
        response_text = handle_text_message(extracted_text, recipient, context_id=context_id)
        send_whatsapp_message(create_text_message(recipient, response_text))
        logging.info(f"[TASK] WA document DONE recipient={recipient} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] WA document error recipient={recipient} context_id={context_id}: {e}")
        send_whatsapp_message(create_text_message(recipient, "Ocurrió un error al procesar tu documento."))

# Telegram tasks

def process_telegram_photo(chat_id: str, context_id: str, caption: str, file_path: str):
    logging.info(f"[TASK] TG photo START chat_id={chat_id} context_id={context_id} file_path={file_path}")
    try:
        response_text = handle_text_message(caption, chat_id, image_path=file_path, context_id=context_id)
        send_telegram_message(chat_id, response_text)
        logging.info(f"[TASK] TG photo DONE chat_id={chat_id} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] TG photo error chat_id={chat_id} context_id={context_id}: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu imagen.")


def process_telegram_audio(chat_id: str, context_id: str, file_path: str):
    logging.info(f"[TASK] TG audio START chat_id={chat_id} context_id={context_id} file_path={file_path}")
    try:
        extracted_text = process_audio(file_path, 'es')
        if not extracted_text or not extracted_text.strip():
            logging.warning(f"[TASK] TG audio empty text extracted from {file_path}")
            send_telegram_message(chat_id, "No pude transcribir el audio. Verifica que el archivo contenga audio claro.")
            return
            
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(chat_id, context_id)
        response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)
        
        if not response_text or not response_text.strip():
            logging.warning(f"[TASK] TG audio empty response generated for chat_id={chat_id}")
            response_text = "Escuché tu audio pero no pude generar una respuesta. Por favor, inténtalo de nuevo."
            
        send_telegram_message(chat_id, response_text)
        logging.info(f"[TASK] TG audio DONE chat_id={chat_id} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] TG audio error chat_id={chat_id} context_id={context_id}: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu audio.")


def process_telegram_document(chat_id: str, context_id: str, file_path: str, file_ext: str):
    logging.info(f"[TASK] TG document START chat_id={chat_id} context_id={context_id} file_path={file_path} ext={file_ext}")
    try:
        extracted_text = process_document(file_path, file_ext)
        if not extracted_text or not extracted_text.strip():
            logging.warning(f"[TASK] TG document empty text extracted from {file_path}")
            send_telegram_message(chat_id, "No pude extraer texto del documento. Verifica que el archivo contenga texto legible.")
            return
            
        if detect_new_topic(extracted_text):
            from datetime import datetime
            context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context = load_context(chat_id, context_id)
        response_text = handle_text_message(extracted_text, chat_id, context_id=context_id)
        
        if not response_text or not response_text.strip():
            logging.warning(f"[TASK] TG document empty response generated for chat_id={chat_id}")
            response_text = "Procesé tu documento pero no pude generar una respuesta. Por favor, inténtalo de nuevo."
            
        send_telegram_message(chat_id, response_text)
        logging.info(f"[TASK] TG document DONE chat_id={chat_id} context_id={context_id}")
    except Exception as e:
        logging.error(f"[TASK] TG document error chat_id={chat_id} context_id={context_id}: {e}")
        send_telegram_message(chat_id, "Ocurrió un error al procesar tu documento.")
