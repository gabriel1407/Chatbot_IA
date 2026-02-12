"""
Improved Routes - Rutas mejoradas que usan la nueva arquitectura.
Implementa principios SOLID y Clean Architecture.
"""
from flask import Blueprint, request

from core.logging.logger import get_app_logger

# Blueprint para las nuevas rutas mejoradas
improved_bp = Blueprint('improved', __name__, url_prefix='/api/v2')

# Logger
logger = get_app_logger()


@improved_bp.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook_v2():
    """
    Endpoint de compatibilidad para v2.
    Delega al webhook canónico para mantener un único flujo de procesamiento.
    """
    logger.warning("[DEPRECATED] Usa /whatsapp en lugar de /api/v2/webhook/whatsapp")
    from routes.whatsapp_routes import verify_token, received_message

    if request.method == 'GET':
        return verify_token()

    return received_message()


@improved_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook_v2():
    """
    Endpoint de compatibilidad para v2.
    Delega al webhook canónico para mantener un único flujo de procesamiento.
    """
    logger.warning("[DEPRECATED] Usa /webhook/telegram en lugar de /api/v2/webhook/telegram")
    from routes.telegram_routes import telegram_webhook
    return telegram_webhook()