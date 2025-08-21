from flask import Blueprint, request, jsonify
import logging
import json
from openIAService.services.whatsapp_service import send_whatsapp_message, create_text_message, process_individual_message
from openIAService.services.metrics_service import log_user_interaction, measure_time
from openIAService.services.limiter import limiter

def whatsapp_sender_key():
    try:
        body = request.get_json(silent=True) or {}
        entry = (body.get("entry") or [{}])[0]
        change = (entry.get("changes") or [{}])[0]
        value = change.get("value", {})
        sender = (value.get("contacts") or [{}])[0].get("wa_id")
        if sender:
            return f"wa:{sender}"
    except Exception:
        pass
    # Fallback to remote address
    return request.remote_addr or "unknown"

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/whatsapp', methods=['GET'])
@measure_time("whatsapp_verify")
@limiter.limit("20 per minute", key_func=lambda: request.args.get('hub.verify_token', request.remote_addr))
def verify_token():
    """Verifica el token de WhatsApp."""
    try:
        access_token = "E23431A21A991BE82FF3D79D5F1F8"
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if token == access_token:
            return challenge
        return "Error", 400
    except Exception as e:
        logging.error(f"Error en verify_token: {e}")
        return "Error", 400

@whatsapp_bp.route('/whatsapp', methods=['POST'])
@measure_time("whatsapp_webhook")
@limiter.limit("20 per minute", key_func=whatsapp_sender_key)
def received_message():
    """Procesa los mensajes recibidos de WhatsApp."""
    try:
        body = request.get_json()
        if not body:
            logging.error("No se recibió ningún cuerpo JSON.")
            return "EVENT_RECEIVED"

        #logging.info(f"JSON recibido: {json.dumps(body)}")

        if "entry" in body and isinstance(body["entry"], list):
            for entry in body["entry"]:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        message_id = message.get("id")
                        if message_id:
                            try:
                                sender = value.get("contacts", [{}])[0].get("wa_id") or message.get("from")
                                msg_type = next((k for k in ["text","image","audio","document"] if k in message), "unknown")
                                log_user_interaction(str(sender or "unknown"), "whatsapp", msg_type)
                            except Exception:
                                pass
                            process_individual_message(message)
                        else:
                            logging.warning("Mensaje recibido sin ID.")
        return "EVENT_RECEIVED"
    except Exception as e:
        logging.error(f"Error en received_message: {e}")
        return "EVENT_RECEIVED"
