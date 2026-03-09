"""
Rutas de gestión de canales por tenant.
Permite registrar/actualizar las credenciales de WhatsApp, Telegram, etc. de cada cliente.
"""
from flask import Blueprint, request, jsonify
from core.auth.jwt_middleware import require_jwt, get_current_user
from domain.entities.tenant_channel import TenantChannel

tenant_channel_bp = Blueprint("tenant_channel", __name__, url_prefix="/api/tenant-channels")


@tenant_channel_bp.before_request
def _auth():
    return require_jwt()


def _get_service():
    from core.config.dependencies import DependencyContainer
    return DependencyContainer.get("TenantChannelService")


@tenant_channel_bp.route("/", methods=["GET"])
def list_all():
    """Lista todos los canales activos. Users solo ven los de su tenant."""
    user = get_current_user()
    role = user.get("role")
    user_tenant = user.get("tenant_id")

    svc = _get_service()
    if role == "admin" and not user_tenant:
        channels = svc.list_all()
    else:
        if not user_tenant:
            return jsonify({"ok": True, "channels": []})
        channels = svc.get_channels_for_tenant(user_tenant)
        
    return jsonify({"ok": True, "channels": [c.to_dict() for c in channels]})


@tenant_channel_bp.route("/<tenant_id>", methods=["GET"])
def list_by_tenant(tenant_id: str):
    """Lista todos los canales de un tenant."""
    user = get_current_user()
    if not (user.get("role") == "admin" and not user.get("tenant_id")) and user.get("tenant_id") != tenant_id:
        from core.exceptions.custom_exceptions import APIException
        raise APIException("No tienes permiso para ver los canales de este tenant", 403, "FORBIDDEN")

    svc = _get_service()
    channels = svc.get_channels_for_tenant(tenant_id)
    return jsonify({"ok": True, "tenant_id": tenant_id, "channels": [c.to_dict() for c in channels]})


@tenant_channel_bp.route("/", methods=["POST"])
def create_or_update():
    """
    Crea o actualiza las credenciales de un canal para un tenant.

    Body JSON:
    {
        "tenant_id": "digitel",
        "channel": "whatsapp",          // "whatsapp" | "telegram"
        "token": "EAANIN...",
        "phone_number_id": "24553...",  // Solo WhatsApp
        "verify_token": "mi_verify",    // Solo WhatsApp
        "bot_username": "@DigitelBot",  // Solo Telegram
        "display_name": "WhatsApp Digitel",
        "is_active": true
    }
    """
    data = request.get_json(force=True) or {}

    tenant_id = data.get("tenant_id", "").strip()
    channel = data.get("channel", "").strip().lower()
    token = data.get("token", "").strip()

    if not tenant_id:
        return jsonify({"ok": False, "error": "tenant_id es requerido"}), 400
    if channel not in ("whatsapp", "telegram"):
        return jsonify({"ok": False, "error": "channel debe ser 'whatsapp' o 'telegram'"}), 400
    if not token:
        return jsonify({"ok": False, "error": "token es requerido"}), 400

    user = get_current_user()
    if not (user.get("role") == "admin" and not user.get("tenant_id")) and user.get("tenant_id") != tenant_id:
        from core.exceptions.custom_exceptions import APIException
        raise APIException("No tienes permisos para configurar canales en este tenant", 403, "FORBIDDEN")

    tc = TenantChannel(
        tenant_id=tenant_id,
        channel=channel,
        token=token,
        is_active=bool(data.get("is_active", True)),
        phone_number_id=data.get("phone_number_id") or None,
        verify_token=data.get("verify_token") or None,
        bot_username=data.get("bot_username") or None,
        display_name=data.get("display_name") or None,
    )

    svc = _get_service()
    saved = svc.save(tc)
    # Si es canal Telegram, intentar registrar webhook automáticamente
    if channel == "telegram" and saved and saved.token:
        try:
            import requests
            # Construir la URL pública del webhook. Usamos request.host_url
            # y forzamos el prefijo /service_ia para coincidir con nginx si aplica.
            base = request.host_url.rstrip("/")
            webhook_url = f"{base}/service_ia/webhook/telegram/{tenant_id}"
            resp = requests.get(
                f"https://api.telegram.org/bot{saved.token}/setWebhook",
                params={"url": webhook_url},
                timeout=10,
            )
            try:
                json_resp = resp.json()
            except Exception:
                json_resp = {"ok": False, "status_code": resp.status_code, "text": resp.text}
            # Añadir info al response para visibilidad
            return jsonify({"ok": True, "channel": saved.to_dict(), "webhook_registration": json_resp}), 201
        except Exception as e:
            # No fallamos la creación por error en webhook; sólo devolvemos info
            return jsonify({"ok": True, "channel": saved.to_dict(), "webhook_error": str(e)}), 201

    # Si es canal WhatsApp, intentar verificar que token + phone_number_id funcionan
    if channel == "whatsapp" and saved and saved.token and saved.phone_number_id:
        try:
            import requests
            graph_url = f"https://graph.facebook.com/v18.0/{saved.phone_number_id}"
            resp = requests.get(graph_url, params={"access_token": saved.token}, timeout=10)
            try:
                check = resp.json()
            except Exception:
                check = {"ok": False, "status_code": resp.status_code, "text": resp.text}
            return jsonify({"ok": True, "channel": saved.to_dict(), "whatsapp_check": check}), 201
        except Exception as e:
            return jsonify({"ok": True, "channel": saved.to_dict(), "whatsapp_error": str(e)}), 201

    return jsonify({"ok": True, "channel": saved.to_dict()}), 201


@tenant_channel_bp.route("/<int:channel_id>", methods=["DELETE"])
def delete_channel(channel_id: int):
    """Desactiva un canal mediante su id numérico."""
    svc = _get_service()
    ch = svc.get_by_numeric_id(channel_id)
    if not ch:
        return jsonify({"ok": False, "error": "Canal no encontrado"}), 404
        
    user = get_current_user()
    if not (user.get("role") == "admin" and not user.get("tenant_id")) and user.get("tenant_id") != ch.tenant_id:
        from core.exceptions.custom_exceptions import APIException
        raise APIException("No tienes permisos para eliminar este canal", 403, "FORBIDDEN")
        
    ok = svc.delete_by_numeric_id(channel_id)
    return jsonify({"ok": ok})


@tenant_channel_bp.route("/<int:channel_id>/cache/clear", methods=["POST"])
def clear_cache(channel_id: int):
    """Invalida la caché de un canal."""
    svc = _get_service()
    ch = svc.get_by_numeric_id(channel_id)
    if not ch:
        return jsonify({"ok": False, "error": "Canal no encontrado"}), 404
        
    user = get_current_user()
    if not (user.get("role") == "admin" and not user.get("tenant_id")) and user.get("tenant_id") != ch.tenant_id:
        from core.exceptions.custom_exceptions import APIException
        raise APIException("No tienes permisos sobre este canal", 403, "FORBIDDEN")
        
    svc.invalidate_cache(ch.tenant_id, ch.channel)
    return jsonify({"ok": True})


@tenant_channel_bp.route("/<int:channel_id>", methods=["PUT"])
def edit_channel(channel_id: int):
    """Edita un canal existente (actualiza token, phone_number_id, displayName, etc)."""
    svc = _get_service()
    ch = svc.get_by_numeric_id(channel_id)
    if not ch:
        return jsonify({"ok": False, "error": "Canal no encontrado"}), 404
        
    user = get_current_user()
    if not (user.get("role") == "admin" and not user.get("tenant_id")) and user.get("tenant_id") != ch.tenant_id:
        from core.exceptions.custom_exceptions import APIException
        raise APIException("No tienes permisos para modificar este canal", 403, "FORBIDDEN")

    data = request.get_json(force=True) or {}
    
    # Update properties if provided
    if "tenant_id" in data:
        ch.tenant_id = data["tenant_id"]
    if "channel" in data:
        ch.channel = data["channel"]
    if "token" in data:
        ch.token = data["token"]
    if "is_active" in data:
        ch.is_active = bool(data["is_active"])
    if "phone_number_id" in data:
        ch.phone_number_id = data["phone_number_id"] or None
    if "verify_token" in data:
        ch.verify_token = data["verify_token"] or None
    if "bot_username" in data:
        ch.bot_username = data["bot_username"] or None
    if "display_name" in data:
        ch.display_name = data["display_name"] or None

    saved = svc.save(ch)
    # Refrescamos cache después del cambio
    svc.invalidate_cache(ch.tenant_id, ch.channel)
    
    return jsonify({"ok": True, "channel": saved.to_dict()}), 200
