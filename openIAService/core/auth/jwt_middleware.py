"""
JWT Middleware para Flask.

Uso en blueprints:
    from core.auth.jwt_middleware import require_jwt, get_current_user

    # Proteger todo el blueprint:
    bp.before_request(require_jwt)

    # O como decorador en rutas específicas:
    @bp.route("/accion", methods=["POST"])
    @require_jwt
    def accion():
        user = get_current_user()   # {"sub": "admin", "role": "admin"}
        ...
"""
import functools
from typing import Optional

from flask import request, jsonify, g

from core.auth.jwt_service import jwt_service, TokenError
from core.logging.logger import get_app_logger

logger = get_app_logger()

# Rutas que nunca necesitan token (whitelist)
_PUBLIC_ENDPOINTS = {
    "auth.login",
    "auth.refresh_token",
    "admin.health_check_v2",
}


def _extract_token() -> Optional[str]:
    """Extrae el token del header Authorization: Bearer <token>."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def _validate() -> Optional[tuple]:
    """
    Valida el JWT de la petición actual.
    Retorna None si es válido (o ruta pública), o una respuesta de error Flask.
    """
    # Rutas públicas: sin auth
    if request.endpoint in _PUBLIC_ENDPOINTS:
        return None

    token = _extract_token()
    if not token:
        return jsonify({"error": "Se requiere token de autenticación (Authorization: Bearer <token>)."}), 401

    try:
        payload = jwt_service.decode(token, expected_type="access")
        g.current_user = payload          # disponible en toda la request
        logger.debug(f"[JWT] Acceso autorizado para '{payload.get('sub')}'")
        return None
    except TokenError as e:
        logger.warning(f"[JWT] Token rechazado: {e}")
        return jsonify({"error": str(e)}), 401


def require_jwt(func=None):
    """
    Puede usarse como:
      - before_request handler: `bp.before_request(require_jwt)`
      - Decorador de ruta:      `@require_jwt`
    """
    # Modo before_request (Flask lo llama sin argumento de función)
    if func is None or not callable(func):
        return _validate()

    # Modo decorador
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        error = _validate()
        if error is not None:
            return error
        return func(*args, **kwargs)

    return wrapper


def get_current_user() -> dict:
    """
    Retorna el payload del JWT del usuario autenticado.
    Solo válido dentro de una request protegida por require_jwt.
    """
    return getattr(g, "current_user", {})
