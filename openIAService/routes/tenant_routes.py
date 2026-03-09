"""
Rutas de configuración de tenants (empresas/clientes).
Permite CRUD completo de la configuración del bot por tenant.

Todos los endpoints requieren la cabecera: X-Admin-Key: <ADMIN_API_KEY>

Endpoints:
  GET    /api/tenant/                        — lista todos los tenants
  GET    /api/tenant/<tenant_id>             — obtiene config de un tenant
  POST   /api/tenant/                        — crea o reemplaza un tenant
  PATCH  /api/tenant/<tenant_id>             — actualiza campos parciales
  DELETE /api/tenant/<tenant_id>             — elimina un tenant
  POST   /api/tenant/<tenant_id>/cache/clear — invalida caché de un tenant
"""
from flask import Blueprint, request, jsonify

from core.config.dependencies import DependencyContainer
from core.auth.jwt_middleware import require_jwt, get_current_user
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger
from domain.entities.tenant_config import TenantConfig

logger = get_app_logger()
tenant_bp = Blueprint("tenant", __name__, url_prefix="/api/tenant")

# Proteger todo el blueprint con JWT
tenant_bp.before_request(require_jwt)


def _get_service():
    return DependencyContainer.get("TenantConfigService")


# -----------------------------------------------------------------------
# GET /api/tenant/
# -----------------------------------------------------------------------
@tenant_bp.route("/", methods=["GET"])
def list_tenants():
    """Lista los tenants registrados. Users solo ven el suyo."""
    user = get_current_user()
    role = user.get("role")
    user_tenant = user.get("tenant_id")

    service = _get_service()
    if role == "admin":
        tenants = service.list_all()
    else:
        # Users solo pueden ver su propio tenant
        if not user_tenant:
            return jsonify({"ok": True, "count": 0, "tenants": []}), 200
        t = service.get(user_tenant)
        tenants = [t] if t else []

    return jsonify({
        "ok": True,
        "count": len(tenants),
        "tenants": [t.to_dict() for t in tenants],
    }), 200


# -----------------------------------------------------------------------
# GET /api/tenant/<tenant_id>
# -----------------------------------------------------------------------
@tenant_bp.route("/<tenant_id>", methods=["GET"])
def get_tenant(tenant_id: str):
    """Obtiene la configuración de un tenant específico."""
    user = get_current_user()
    if user.get("role") != "admin" and user.get("tenant_id") != tenant_id:
        raise APIException("No tienes permiso para ver este tenant", 403, "FORBIDDEN")

    service = _get_service()
    config = service.get(tenant_id)
    if not config:
        raise APIException("Tenant no encontrado", 404, "NOT_FOUND")
    return jsonify({"ok": True, "tenant": config.to_dict()}), 200


# -----------------------------------------------------------------------
# POST /api/tenant/
# -----------------------------------------------------------------------
@tenant_bp.route("/", methods=["POST"])
def create_or_replace_tenant():
    """
    Crea o reemplaza completamente la configuración de un tenant.

    Body JSON:
    {
        "tenant_id":           "ferreteria_lopez",   (requerido)
        "bot_name":            "Bot Ferretería López",
        "bot_persona":         "Eres el asistente de una ferretería...",
        "welcome_message":     "¡Bienvenido a Ferretería López! ¿En qué te ayudo?",
        "language":            "es",
        "out_of_scope_message": "Lo siento, solo puedo ayudarte con consultas de ferretería.",
        "ai_provider":         "gemini",             (null = usa el global de .env)
        "ai_model":            null,
        "rag_enabled":         true,
        "rag_top_k":           5,
        "rag_min_similarity":  0.3,
        "max_response_tokens": 600,
        "temperature":         0.7,
        "web_search_enabled":  false
    }
    """
    data = request.get_json(silent=True)
    if not data:
        raise APIException("Se requiere un body JSON", 400, "INVALID_JSON")

    tenant_id = data.get("tenant_id", "").strip()
    if not tenant_id:
        raise APIException("El campo 'tenant_id' es requerido", 400, "VALIDATION_ERROR")

    user = get_current_user()
    # Users no pueden crear otro tenant que no sea el suyo
    if user.get("role") != "admin" and user.get("tenant_id") != tenant_id:
        raise APIException("No tienes permisos para configurar este tenant", 403, "FORBIDDEN")

    config = TenantConfig.from_dict({"tenant_id": tenant_id, **data})
    service = _get_service()
    saved = service.save(config)
    logger.info(f"[TenantRoutes] Tenant '{tenant_id}' creado/reemplazado por '{user.get('sub')}'")
    return jsonify({"ok": True, "tenant": saved.to_dict()}), 201


# -----------------------------------------------------------------------
# PATCH /api/tenant/<int:id>
# -----------------------------------------------------------------------
@tenant_bp.route("/<int:config_id>", methods=["PATCH"])
def update_tenant(config_id: int):
    """
    Actualiza solo los campos que se envíen en el body usando ID numérico.
    El resto mantiene sus valores actuales.

    Body JSON: cualquier subconjunto de campos de TenantConfig.
    """
    data = request.get_json(silent=True)
    if not data:
        raise APIException("Se requiere un body JSON", 400, "INVALID_JSON")

    service = _get_service()
    config = service.get_by_numeric_id(config_id)
    if not config:
        raise APIException(f"Config con ID {config_id} no encontrada", 404, "NOT_FOUND")

    user = get_current_user()
    if user.get("role") != "admin" and user.get("tenant_id") != config.tenant_id:
        raise APIException("No tienes permisos para modificar este tenant", 403, "FORBIDDEN")

    # Aplicamos solo los campos recibidos
    updatable_fields = [
        "bot_name", "bot_persona", "welcome_message", "language",
        "out_of_scope_message", "ai_provider", "ai_model",
        "rag_enabled", "rag_top_k", "rag_min_similarity",
        "max_response_tokens", "temperature", "web_search_enabled", "is_active",
    ]

    for key in updatable_fields:
        if key in data:
            setattr(config, key, data[key])

    saved = service.save(config)
    logger.info(f"[TenantRoutes] Tenant ID '{config_id}' actualizado parcialmente")
    return jsonify({"ok": True, "tenant": saved.to_dict()}), 200


# -----------------------------------------------------------------------
# DELETE /api/tenant/<tenant_id>
# -----------------------------------------------------------------------
@tenant_bp.route("/<int:config_id>", methods=["DELETE"])
def delete_tenant(config_id: int):
    """Elimina la configuración de un tenant mediante su id numérico."""
    service = _get_service()
    config = service.get_by_numeric_id(config_id)
    if not config:
        raise APIException("Tenant no encontrado", 404, "NOT_FOUND")
    if config.tenant_id == "default":
        raise APIException("No se puede eliminar el tenant 'default'", 400, "FORBIDDEN")
        
    user = get_current_user()
    if user.get("role") != "admin" and user.get("tenant_id") != config.tenant_id:
        raise APIException("No tienes permisos para eliminar este tenant", 403, "FORBIDDEN")
    
    deleted = service.delete_by_numeric_id(config_id)
    if not deleted:
        raise APIException(f"No se pudo eliminar el tenant id {config_id}", 400, "BAD_REQUEST")
    
    logger.info(f"[TenantRoutes] Tenant con id '{config_id}' eliminado")
    return jsonify({"ok": True, "message": f"Tenant eliminado"}), 200


# -----------------------------------------------------------------------
# POST /api/tenant/<tenant_id>/cache/clear
# -----------------------------------------------------------------------
@tenant_bp.route("/<tenant_id>/cache/clear", methods=["POST"])
def clear_cache(tenant_id: str):
    """Invalida el caché en memoria de un tenant (fuerza recarga desde DB)."""
    service = _get_service()
    service.invalidate_cache(tenant_id)
    return jsonify({"ok": True, "message": f"Caché de '{tenant_id}' invalidado"}), 200


# -----------------------------------------------------------------------
# POST /api/tenant/cache/clear  (todos)
# -----------------------------------------------------------------------
@tenant_bp.route("/cache/clear", methods=["POST"])
def clear_all_cache():
    """Invalida el caché de todos los tenants."""
    service = _get_service()
    service.invalidate_cache()
    return jsonify({"ok": True, "message": "Caché de todos los tenants invalidado"}), 200
