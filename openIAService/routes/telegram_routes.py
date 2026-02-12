from flask import Blueprint, request
from services.channel_adapters import ChannelType, get_unified_channel_service
from core.logging.logger import get_app_logger

telegram_bp = Blueprint('telegram_bp', __name__)
logger = get_app_logger()

@telegram_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    Webhook para Telegram que usa UnifiedChannelService + RAG.
    """
    try:
        raw_data = request.get_json()
        if not raw_data:
            logger.warning("Webhook de Telegram recibido sin datos JSON")
            return "OK", 200
        
        from core.config.settings import settings
        if settings.rag_enabled:
            logger.info("Procesando webhook de Telegram con RAG integrado")
        else:
            logger.info("Procesando webhook de Telegram (RAG deshabilitado)")
        
        unified_service = get_unified_channel_service()

        # Usar el servicio unificado para procesar (incluye búsqueda RAG)
        success = unified_service.process_webhook(ChannelType.TELEGRAM, raw_data)
        
        if success:
            logger.info("Webhook de Telegram procesado exitosamente")
        else:
            logger.warning("Webhook de Telegram procesado con errores")
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook de Telegram: {e}")
        return "OK", 200  # Telegram requiere respuesta 200 siempre
