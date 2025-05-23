from flask import Blueprint, request
from services.telegram_service import process_telegram_update

telegram_bp = Blueprint('telegram_bp', __name__)

@telegram_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    process_telegram_update(update)
    return "OK", 200