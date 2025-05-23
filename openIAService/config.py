import os
from decouple import config

class Config:
    """Configuraciones generales de la aplicación."""
    SECRET_KEY = config('SECRET_KEY', default='supersecretkey')
    UPLOAD_FOLDER = os.path.join('local', 'uploads')
    TOKEN_WHATSAPP = config('TOKEN_WHATSAPP')
    OPENAI_API_KEY = config('OPENAI_API_KEY')
    WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/245533201976802/messages"
    TELEGRAM_TOKEN = config('TELEGRAM_TOKEN')  # Agregado para Telegram
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"  # Agregado para Telegram

    @staticmethod
    def init_app(app):
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        app.config['TELEGRAM_TOKEN'] = Config.TELEGRAM_TOKEN  # Agregado para Telegram
        app.config['TELEGRAM_API_URL'] = Config.TELEGRAM_API_URL  # Agregado para Telegram