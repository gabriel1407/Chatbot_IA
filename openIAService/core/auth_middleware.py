"""
Admin Auth Middleware.
Protege los endpoints administrativos con una API key simple.

Uso:
    from core.auth_middleware import require_admin_key

    @bp.before_request
    def auth():
        return require_admin_key()

    # o como decorador en rutas específicas:
    @bp.route("/accion", methods=["POST"])
    @require_admin_key
    def accion():
        ...
"""
import functools
from flask import request, jsonify
from core.config.settings import settings


def _check_key() -> bool:
    """Verifica que la petición lleve la API key de administración correcta."""
    admin_key = getattr(settings, "admin_api_key", None)
    if not admin_key:
        # Si no hay clave configurada, el endpoint queda abierto (warn en logs)
        return True
    provided = (
        request.headers.get("X-Admin-Key")
        or request.args.get("admin_key")
    )
    return provided == admin_key


def require_admin_key(func=None):
    """
    Puede usarse como:
      - before_request handler: `app.before_request(require_admin_key)`
      - Decorador de ruta: `@require_admin_key`
    """
    # Modo before_request (sin función destino)
    if func is None:
        if not _check_key():
            return jsonify({"error": "Acceso no autorizado. Proporciona X-Admin-Key."}), 403
        return None  # Deja pasar

    # Modo decorador
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _check_key():
            return jsonify({"error": "Acceso no autorizado. Proporciona X-Admin-Key."}), 403
        return func(*args, **kwargs)

    return wrapper
