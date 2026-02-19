"""
Manejadores globales de errores HTTP para Flask.
Estandariza payloads de error en toda la aplicación.
"""
from datetime import datetime

from flask import jsonify
from werkzeug.exceptions import HTTPException

from core.exceptions.custom_exceptions import APIException, ChatbotBaseException
from core.logging.logger import get_app_logger

logger = get_app_logger()


def _error_payload(message: str, code: str):
    return {
        "success": False,
        "error": message,
        "code": code,
        "timestamp": datetime.now().isoformat(),
    }


def register_http_error_handlers(app):
    """Registra handlers globales de errores sobre app Flask."""

    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException):
        logger.warning(f"APIException: {error.code} - {error.message}")
        return jsonify(_error_payload(error.message, error.code)), error.status_code

    @app.errorhandler(ChatbotBaseException)
    def handle_chatbot_exception(error: ChatbotBaseException):
        logger.error(f"ChatbotBaseException: {error.code} - {error.message}")
        return jsonify(_error_payload(error.message, error.code)), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        logger.warning(f"HTTPException: {error.code} - {error.description}")
        return jsonify(_error_payload(error.description, "HTTP_ERROR")), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        logger.exception(f"Unhandled exception: {error}")
        return jsonify(_error_payload("Error interno del servidor", "UNHANDLED_ERROR")), 500
