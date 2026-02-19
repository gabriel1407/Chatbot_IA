from flask import Blueprint, request
from services.channel_adapters import ChannelType, get_unified_channel_service, WhatsAppAdapter
from core.config.settings import settings
from core.logging.logger import get_app_logger

whatsapp_bp = Blueprint('whatsapp', __name__)
logger = get_app_logger()


def _resolve_whatsapp_tenant(body: dict):
    """
    Extrae el phone_number_id del payload y busca el tenant correspondiente en DB.
    Retorna (tenant_id, WhatsAppAdapter|None).
    """
    try:
        phone_number_id = (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("metadata", {})
            .get("phone_number_id")
        )
        if not phone_number_id:
            return None, None

        from core.config.dependencies import DependencyContainer
        svc = DependencyContainer.get("TenantChannelService")
        tenant_ch = svc.get_tenant_by_phone_number_id(phone_number_id)
        if tenant_ch:
            logger.info(
                f"[WhatsApp] phone_number_id={phone_number_id} → tenant='{tenant_ch.tenant_id}'"
            )
            adapter = WhatsAppAdapter(
                token=tenant_ch.token,
                phone_number_id=tenant_ch.phone_number_id,
            )
            return tenant_ch.tenant_id, adapter
    except KeyError:
        logger.debug("TenantChannelService no registrado — usando configuración por defecto")
    except Exception as e:
        logger.warning(f"[WhatsApp] Error resolviendo tenant por phone_number_id: {e}")
    return None, None


@whatsapp_bp.route('/whatsapp', methods=['GET'])
def verify_token():
    """Verifica el token de WhatsApp."""
    try:
        # Soporte multi-tenant: buscar verify_token del tenant si se provee phone_number_id
        phone_number_id = request.args.get("phone_number_id")
        verify_token_value = settings.whatsapp_verify_token

        if phone_number_id:
            try:
                from core.config.dependencies import DependencyContainer
                svc = DependencyContainer.get("TenantChannelService")
                tenant_ch = svc.get_tenant_by_phone_number_id(phone_number_id)
                if tenant_ch and tenant_ch.verify_token:
                    verify_token_value = tenant_ch.verify_token
            except Exception:
                pass

        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if token == verify_token_value:
            logger.info("Token de WhatsApp verificado exitosamente")
            return challenge
        logger.warning("Token de WhatsApp inválido")
        return "Error", 400
    except Exception as e:
        logger.error(f"Error en verify_token: {e}")
        return "Error", 400

@whatsapp_bp.route('/whatsapp', methods=['POST'])
def received_message():
    """Procesa los mensajes recibidos de WhatsApp con RAG integrado."""
    try:
        body = request.get_json()
        if not body:
            logger.warning("No se recibió ningún cuerpo JSON en WhatsApp")
            return "EVENT_RECEIVED"

        logger.info("Webhook de WhatsApp recibido")

        unified_service = get_unified_channel_service()

        # 1. Intentar resolver tenant por phone_number_id del payload (multi-tenant)
        tenant_id, adapter_override = _resolve_whatsapp_tenant(body)

        # 2. Fallback: header X-Tenant-ID, query param, o default configurado
        if not tenant_id:
            tenant_id = (
                request.headers.get("X-Tenant-ID")
                or request.args.get("tenant_id")
                or settings.default_tenant_id
            )

        logger.info(f"[WhatsApp] Procesando mensaje para tenant='{tenant_id}'")

        success = unified_service.process_webhook(
            ChannelType.WHATSAPP, body, tenant_id=tenant_id, adapter_override=adapter_override
        )

        if success:
            logger.info("Webhook de WhatsApp procesado exitosamente")
        else:
            logger.warning("Webhook de WhatsApp procesado con errores")

        return "EVENT_RECEIVED", 200

    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {e}")
        return "EVENT_RECEIVED", 200
