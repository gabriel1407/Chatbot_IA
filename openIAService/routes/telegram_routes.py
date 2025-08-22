from flask import Blueprint, request
from openIAService.services.telegram_service import process_telegram_update, send_telegram_message
from openIAService.services.metrics_service import measure_time
from openIAService.services.rate_limiter_cleanup import is_allowed

telegram_bp = Blueprint('telegram_bp', __name__)

@telegram_bp.route('/webhook/telegram', methods=['POST'])
@measure_time("telegram_webhook")
def telegram_webhook():
    update = request.get_json()
    # Rate limiting por chat (20 req/min)
    try:
        chat_id = str(update.get("message", {}).get("chat", {}).get("id")) if update else None
        if chat_id:
            key = f"tg:{chat_id}"
            if not is_allowed(key, limit=20, window_seconds=60):
                try:
                    send_telegram_message(chat_id, "Demasiadas solicitudes. Intenta nuevamente en un minuto.")
                except Exception:
                    pass
                return "OK", 200
    except Exception:
        pass
    process_telegram_update(update)
    return "OK", 200