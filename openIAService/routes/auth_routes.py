"""
Auth Routes — Login, refresh y gestión de usuarios admin.

Endpoints públicos:
  POST /api/auth/login             — recibe {username, password}, devuelve JWT pair
  POST /api/auth/refresh           — recibe {refresh_token}, devuelve nuevo access_token

Endpoints protegidos (requieren Bearer access_token):
  GET  /api/auth/me                — info del usuario autenticado
  PATCH /api/auth/me/password      — cambiar propia contraseña

Endpoints solo para rol "admin":
  GET   /api/auth/users            — listar todos los usuarios
  POST  /api/auth/users            — crear nuevo usuario
  PATCH /api/auth/users/<username>/status  — activar/desactivar usuario
"""
from flask import Blueprint, request, jsonify, g

from core.auth.jwt_service import jwt_service, TokenError
from core.auth.jwt_middleware import require_jwt, get_current_user
from core.config.dependencies import DependencyContainer
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger

logger = get_app_logger()
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Todos los endpoints del blueprint requieren JWT salvo login y refresh
auth_bp.before_request(require_jwt)


def _get_user_repo():
    return DependencyContainer.get("AdminUserRepository")


# -----------------------------------------------------------------------
# POST /api/auth/login
# -----------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Autentica un usuario y devuelve un par de tokens JWT.

    Body JSON:
        { "username": "admin", "password": "tu_contraseña" }

    Respuesta:
        {
            "access_token":  "eyJ...",
            "refresh_token": "eyJ...",
            "token_type":    "Bearer",
            "expires_in":    1800        // segundos
        }

    Usa el access_token en las siguientes peticiones:
        Authorization: Bearer <access_token>
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        raise APIException("Se requieren 'username' y 'password'", 400, "VALIDATION_ERROR")

    repo = _get_user_repo()
    user = repo.verify_password(username, password)
    if user is None:
        logger.warning(f"[Auth] Login fallido para '{username}' desde {request.remote_addr}")
        raise APIException("Credenciales incorrectas", 401, "INVALID_CREDENTIALS")

    tokens = jwt_service.create_token_pair(user["username"], user["role"])
    logger.info(f"[Auth] Login exitoso para '{username}'")
    return jsonify(tokens), 200


# -----------------------------------------------------------------------
# POST /api/auth/refresh
# -----------------------------------------------------------------------
@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    Renueva el access_token usando un refresh_token válido.

    Body JSON:
        { "refresh_token": "eyJ..." }

    Respuesta:
        { "access_token": "eyJ...", "token_type": "Bearer", "expires_in": 1800 }
    """
    data = request.get_json(silent=True) or {}
    token = (data.get("refresh_token") or "").strip()
    if not token:
        raise APIException("Se requiere 'refresh_token'", 400, "VALIDATION_ERROR")

    try:
        payload = jwt_service.decode(token, expected_type="refresh")
    except TokenError as e:
        raise APIException(str(e), 401, "INVALID_TOKEN")

    new_access = jwt_service.create_access_token(payload["sub"], payload.get("role", "admin"))
    return jsonify({
        "access_token": new_access,
        "token_type": "Bearer",
        "expires_in": jwt_service._access_ttl * 60,
    }), 200


# -----------------------------------------------------------------------
# GET /api/auth/me
# -----------------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
def me():
    """Retorna los datos del usuario autenticado (desde el token)."""
    user = get_current_user()
    return jsonify({
        "username": user.get("sub"),
        "role":     user.get("role"),
    }), 200


# -----------------------------------------------------------------------
# PATCH /api/auth/me/password
# -----------------------------------------------------------------------
@auth_bp.route("/me/password", methods=["PATCH"])
def change_my_password():
    """
    Permite al usuario autenticado cambiar su propia contraseña.

    Body JSON:
        { "current_password": "...", "new_password": "..." }
    """
    data = request.get_json(silent=True) or {}
    current_pw = data.get("current_password") or ""
    new_pw = data.get("new_password") or ""

    if not current_pw or not new_pw:
        raise APIException(
            "Se requieren 'current_password' y 'new_password'", 400, "VALIDATION_ERROR"
        )
    if len(new_pw) < 8:
        raise APIException("La nueva contraseña debe tener al menos 8 caracteres", 400, "VALIDATION_ERROR")

    username = get_current_user().get("sub")
    repo = _get_user_repo()

    # Verificar contraseña actual
    if not repo.verify_password(username, current_pw):
        raise APIException("La contraseña actual es incorrecta", 401, "INVALID_CREDENTIALS")

    repo.change_password(username, new_pw)
    logger.info(f"[Auth] Contraseña cambiada para '{username}'")
    return jsonify({"ok": True, "message": "Contraseña actualizada correctamente"}), 200


# -----------------------------------------------------------------------
# GET /api/auth/users       (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users", methods=["GET"])
def list_users():
    """Lista todos los usuarios admin registrados."""
    _require_admin_role()
    repo = _get_user_repo()
    users = repo.list_users()
    # No exponemos datos sensibles
    safe = [
        {
            "username":   u["username"],
            "role":       u["role"],
            "is_active":  bool(u["is_active"]),
            "created_at": u["created_at"].isoformat() if u.get("created_at") else None,
            "last_login": u["last_login"].isoformat() if u.get("last_login") else None,
        }
        for u in users
    ]
    return jsonify({"ok": True, "users": safe}), 200


# -----------------------------------------------------------------------
# POST /api/auth/users      (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users", methods=["POST"])
def create_user():
    """
    Crea un nuevo usuario admin.

    Body JSON:
        { "username": "ops_user", "password": "segura123", "role": "admin" }

    Roles disponibles: "admin" (acceso total) | "viewer" (solo lectura — futuro)
    """
    _require_admin_role()
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "admin").strip()

    if not username or not password:
        raise APIException("Se requieren 'username' y 'password'", 400, "VALIDATION_ERROR")
    if len(password) < 8:
        raise APIException("La contraseña debe tener al menos 8 caracteres", 400, "VALIDATION_ERROR")
    if role not in ("admin", "viewer"):
        raise APIException("Rol inválido. Opciones: 'admin', 'viewer'", 400, "VALIDATION_ERROR")

    repo = _get_user_repo()
    created = repo.create_user(username, password, role)
    if not created:
        raise APIException(f"El usuario '{username}' ya existe", 409, "CONFLICT")

    return jsonify({"ok": True, "message": f"Usuario '{username}' creado con rol '{role}'"}), 201


# -----------------------------------------------------------------------
# PATCH /api/auth/users/<username>/status   (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users/<username>/status", methods=["PATCH"])
def update_user_status(username: str):
    """
    Activa o desactiva un usuario.

    Body JSON:
        { "is_active": false }
    """
    _require_admin_role()
    current = get_current_user().get("sub")
    if username == current:
        raise APIException("No puedes desactivarte a ti mismo", 400, "FORBIDDEN")

    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise APIException("Se requiere el campo 'is_active'", 400, "VALIDATION_ERROR")

    repo = _get_user_repo()
    updated = repo.set_active(username, bool(data["is_active"]))
    if not updated:
        raise APIException(f"Usuario '{username}' no encontrado", 404, "NOT_FOUND")

    state = "activado" if data["is_active"] else "desactivado"
    return jsonify({"ok": True, "message": f"Usuario '{username}' {state}"}), 200


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------
def _require_admin_role():
    role = get_current_user().get("role")
    if role != "admin":
        raise APIException("Se requiere rol 'admin' para esta acción", 403, "FORBIDDEN")
