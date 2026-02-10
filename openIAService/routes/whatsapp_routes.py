from flask import Blueprint, request, jsonify
import logging
import json
from services.whatsapp_service import send_whatsapp_message, create_text_message, process_individual_message
from core.config.settings import settings

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/whatsapp', methods=['GET'])
def verify_token():
    """Verifica el token de WhatsApp."""
    try:
        access_token = settings.whatsapp_verify_token
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if token == access_token:
            return challenge
        return "Error", 400
    except Exception as e:
        logging.error(f"Error en verify_token: {e}")
        return "Error", 400

@whatsapp_bp.route('/whatsapp', methods=['POST'])
def received_message():
    """Procesa los mensajes recibidos de WhatsApp."""
    try:
        body = request.get_json()
        if not body:
            logging.error("No se recibió ningún cuerpo JSON.")
            return "EVENT_RECEIVED"

        logging.info(f"JSON recibido: {json.dumps(body)}")

        if "entry" in body and isinstance(body["entry"], list):
            for entry in body["entry"]:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        message_id = message.get("id")
                        if message_id:
                            process_individual_message(message)
                        else:
                            logging.warning("Mensaje recibido sin ID.")
        return "EVENT_RECEIVED"
    except Exception as e:
        logging.error(f"Error en received_message: {e}")
        return "EVENT_RECEIVED"
