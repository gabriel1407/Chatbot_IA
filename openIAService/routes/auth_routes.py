"""
Auth Routes — Registro, Login, refresh y gestión de usuarios.

Endpoints públicos:
  POST /api/auth/register          — auto-registro de cliente con rol 'user'
  POST /api/auth/login             — recibe {username|email, password}, devuelve JWT pair
  POST /api/auth/refresh           — recibe {refresh_token}, devuelve nuevo access_token

Endpoints protegidos (requieren Bearer access_token):
  GET  /api/auth/me                — info completa del usuario autenticado
  PATCH /api/auth/me/password      — cambiar propia contraseña

Endpoints solo para rol "admin":
  GET   /api/auth/users            — listar todos los usuarios
  POST  /api/auth/users            — crear usuario (admin puede elegir rol)
  PATCH /api/auth/users/<username>/status  — activar/desactivar usuario
"""
from flask import Blueprint, request, jsonify, g

from core.auth.jwt_service import jwt_service, TokenError
from core.auth.jwt_middleware import require_jwt, get_current_user, require_role
from core.config.dependencies import DependencyContainer
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger

logger = get_app_logger()
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Todos los endpoints del blueprint requieren JWT salvo login, refresh y register
auth_bp.before_request(require_jwt)


def _get_user_repo():
    return DependencyContainer.get("AdminUserRepository")


# -----------------------------------------------------------------------
# POST /api/auth/register  (público)
# -----------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Auto-registro de nuevo cliente en la plataforma.

    Body JSON:
        {
            "username":  "miempresa",
            "email":     "contacto@empresa.com",
            "password":  "contraseña_segura",
            "full_name": "Juan Pérez"          (opcional)
        }

    Respuesta: 201 con JWT pair listo para usar.
    El usuario creado tiene rol 'user' y parte en plan Free.
    """
    data = request.get_json(silent=True) or {}
    username  = (data.get("username") or "").strip()
    email     = (data.get("email") or "").strip().lower()
    password  = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip() or None

    if not username or not email or not password:
        raise APIException(
            "Se requieren 'username', 'email' y 'password'", 400, "VALIDATION_ERROR"
        )

    repo = _get_user_repo()
    ok, error_msg = repo.register_user(username, email, password, full_name)
    if not ok:
        raise APIException(error_msg, 409, "CONFLICT")

    # Devolver JWT pair directamente para que el cliente no tenga que hacer login por separado
    # Se pasa tenant_id=None porque acaba de registrarse como user normal
    tokens = jwt_service.create_token_pair(username, "user", None)
    logger.info(f"[Auth] Nuevo registro: '{username}' ({email})")
    return jsonify({
        **tokens,
        "message": "Cuenta creada exitosamente. Bienvenido a ChatBot IA.",
    }), 201


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
        # Intentar login por email si el username no matcheó
        email_user = repo.find_by_email(username)
        if email_user:
            user = repo.verify_password(email_user["username"], password)

    if user is None:
        logger.warning(f"[Auth] Login fallido para '{username}' desde {request.remote_addr}")
        raise APIException("Credenciales incorrectas", 401, "INVALID_CREDENTIALS")

    tokens = jwt_service.create_token_pair(
        user["username"], 
        user["role"], 
        user.get("tenant_id")
    )
    logger.info(f"[Auth] Login exitoso para '{user['username']}' (rol: {user['role']})")
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

    new_access = jwt_service.create_access_token(
        payload["sub"], 
        payload.get("role", "admin"),
        payload.get("tenant_id")
    )
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
    """Retorna los datos completos del usuario autenticado."""
    current = get_current_user()
    username = current.get("sub")
    repo = _get_user_repo()
    info = repo.get_user_info(username)
    if info:
        return jsonify({"ok": True, "user": info}), 200
    # Fallback si el usuario no tiene info extendida aún
    return jsonify({"ok": True, "user": {
        "username": username,
        "role": current.get("role"),
        "email": None,
        "full_name": None,
    }}), 200


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
            "id":         u.get("id"),
            "username":   u["username"],
            "email":      u.get("email"),
            "full_name":  u.get("full_name"),
            "role":       u["role"],
            "tenant_id":  u.get("tenant_id"),
            "is_active":  bool(u["is_active"]),
            "created_at": u["created_at"].isoformat() if u.get("created_at") else None,
            "last_login": u["last_login"].isoformat() if u.get("last_login") else None,
        }
        for u in users
    ]
    return jsonify({"ok": True, "users": safe}), 200


# -----------------------------------------------------------------------
# GET /api/auth/users/<int:user_id> (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user_by_id(user_id: int):
    """Devuelve la información de un usuario específico por su ID."""
    _require_admin_role()
    repo = _get_user_repo()
    
    # We load list for now and filter, or we can add find_by_id
    users = repo.list_users()
    user = next((u for u in users if u.get("id") == user_id), None)
    if not user:
        raise APIException("Usuario no encontrado", 404, "NOT_FOUND")

    safe = {
        "id":         user.get("id"),
        "username":   user["username"],
        "email":      user.get("email"),
        "full_name":  user.get("full_name"),
        "role":       user["role"],
        "tenant_id":  user.get("tenant_id"),
        "is_active":  bool(user["is_active"]),
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
        "last_login": user["last_login"].isoformat() if user.get("last_login") else None,
    }
    return jsonify({"ok": True, "user": safe}), 200

# -----------------------------------------------------------------------
# POST /api/auth/users      (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users", methods=["POST"])
def create_user():
    """
    Crea un nuevo usuario admin.

    Body JSON:
        { "username": "ops_user", "password": "segura123", "role": "admin" }

    Roles disponibles: "admin", "user"
    """
    _require_admin_role()
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "user").strip()
    email = (data.get("email") or "").strip().lower() or None
    full_name = (data.get("full_name") or "").strip() or None
    tenant_id = (data.get("tenant_id") or "").strip() or None

    if not username or not password:
        raise APIException("Se requieren 'username' y 'password'", 400, "VALIDATION_ERROR")
    if len(password) < 8:
        raise APIException("La contraseña debe tener al menos 8 caracteres", 400, "VALIDATION_ERROR")
    if role not in ("admin", "user", "viewer"):
        raise APIException("Rol inválido. Opciones: 'admin', 'user'", 400, "VALIDATION_ERROR")

    repo = _get_user_repo()
    created = repo.create_user(username, password, role, email=email, full_name=full_name, tenant_id=tenant_id)
    if not created:
        raise APIException(f"El usuario o email '{username}/{email}' ya existe", 409, "CONFLICT")

    return jsonify({"ok": True, "message": f"Usuario '{username}' creado con rol '{role}'"}), 201


# -----------------------------------------------------------------------
# PUT /api/auth/users/<int:user_id>  (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users/<int:user_id>", methods=["PUT"])
def edit_user(user_id: int):
    """
    Actualiza la información perfil y rol de un usuario.
    Body JSON:
        { "email": "...", "full_name": "...", "role": "admin|user" }
    """
    _require_admin_role()
    data = request.get_json(silent=True) or {}
    
    email = (data.get("email") or "").strip().lower() or None
    full_name = data.get("full_name")
    tenant_id = data.get("tenant_id")
    if isinstance(full_name, str):
        full_name = full_name.strip() or None
    if isinstance(tenant_id, str):
        tenant_id = tenant_id.strip() or None
        
    role = (data.get("role") or "").strip()
    if role and role not in ("admin", "user", "viewer"):
        raise APIException("Rol inválido. Opciones: 'admin', 'user'", 400, "VALIDATION_ERROR")

    repo = _get_user_repo()
    updated = repo.update_user(user_id, email=email, full_name=full_name, role=role if role else None, tenant_id=tenant_id)
    if not updated:
        raise APIException(f"No se pudo actualizar o el usuario id '{user_id}' no existe", 400, "BAD_REQUEST")

    return jsonify({"ok": True, "message": f"Usuario id '{user_id}' actualizado correctamente"}), 200


# -----------------------------------------------------------------------
# DELETE /api/auth/users/<int:user_id>  (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
def remove_user(user_id: int):
    """Elimina del sistema a un usuario permanentemente."""
    _require_admin_role()
    
    # Prevenir que se elimine a sí mismo
    current_username = get_current_user().get("sub")
    repo = _get_user_repo()
    u_info = next((u for u in repo.list_users() if u["username"] == current_username), None)
    if u_info and u_info.get("id") == user_id:
        raise APIException("No puedes eliminarte a ti mismo", 400, "FORBIDDEN")

    deleted = repo.delete_user(user_id)
    if not deleted:
        raise APIException(f"No se pudo eliminar al usuario id '{user_id}'", 400, "BAD_REQUEST")

    return jsonify({"ok": True, "message": f"Usuario id '{user_id}' eliminado"}), 200


# -----------------------------------------------------------------------
# PATCH /api/auth/users/<int:user_id>/status   (solo admin)
# -----------------------------------------------------------------------
@auth_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
def update_user_status(user_id: int):
    """
    Activa o desactiva un usuario.

    Body JSON:
        { "is_active": false }
    """
    _require_admin_role()
    current_username = get_current_user().get("sub")
    repo = _get_user_repo()
    u_info = next((u for u in repo.list_users() if u["username"] == current_username), None)
    if u_info and u_info.get("id") == user_id:
        raise APIException("No puedes desactivarte a ti mismo", 400, "FORBIDDEN")

    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise APIException("Se requiere el campo 'is_active'", 400, "VALIDATION_ERROR")

    updated = repo.set_active(user_id, bool(data["is_active"]))
    if not updated:
        raise APIException(f"Usuario id '{user_id}' no encontrado", 404, "NOT_FOUND")

    state = "activado" if data["is_active"] else "desactivado"
    return jsonify({"ok": True, "message": f"Usuario id '{user_id}' {state}"}), 200


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------
def _require_admin_role():
    """Comprueba que el usuario actual sea admin. Helper legacy, prefiere @require_role."""
    role = get_current_user().get("role")
    if role != "admin":
        raise APIException("Se requiere rol 'admin' para esta acción", 403, "FORBIDDEN")
