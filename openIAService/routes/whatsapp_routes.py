from flask import Blueprint, request, jsonify
import logging
import json
from services.channel_adapters import ChannelType, get_unified_channel_service
from core.config.settings import settings
from core.logging.logger import get_app_logger

whatsapp_bp = Blueprint('whatsapp', __name__)
logger = get_app_logger()
unified_service = get_unified_channel_service()

@whatsapp_bp.route('/whatsapp', methods=['GET'])
def verify_token():
    """Verifica el token de WhatsApp."""
    try:
        access_token = settings.whatsapp_verify_token
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if token == access_token:
            logger.info("Token de WhatsApp verificado exitosamente")
            return challenge
        logger.warning("Token de WhatsApp inválido")
        return "Error", 400
    except Exception as e:
        logger.error(f"Error en verify_token: {e}")
        return "Error", 400

@whatsapp_bp.route('/whatsapp', methods=['POST'])
def received_message():
    """Procesa los mensajes recibidos de WhatsApp con RAG integrado."""
    try:
        body = request.get_json()
        if not body:
            logger.warning("No se recibió ningún cuerpo JSON en WhatsApp")
            return "EVENT_RECEIVED"

        logger.info(f"Webhook de WhatsApp recibido")
        
        # Usar el servicio unificado para procesar (incluye búsqueda RAG)
        success = unified_service.process_webhook(ChannelType.WHATSAPP, body)
        
        if success:
            logger.info("Webhook de WhatsApp procesado exitosamente")
        else:
            logger.warning("Webhook de WhatsApp procesado con errores")
        
        return "EVENT_RECEIVED", 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {e}")
        return "EVENT_RECEIVED", 200
