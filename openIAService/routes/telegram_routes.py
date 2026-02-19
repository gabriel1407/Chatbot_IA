from flask import Blueprint, request
from services.channel_adapters import ChannelType, get_unified_channel_service, TelegramAdapter
from core.config.settings import settings
from core.logging.logger import get_app_logger

telegram_bp = Blueprint('telegram_bp', __name__)
logger = get_app_logger()


def _process_telegram(raw_data: dict, tenant_id: str, adapter_override=None):
    """Helper para procesar el webhook de Telegram."""
    unified_service = get_unified_channel_service()
    if settings.rag_enabled:
        logger.info(f"Procesando webhook de Telegram con RAG integrado (tenant='{tenant_id}')")
    else:
        logger.info(f"Procesando webhook de Telegram (RAG deshabilitado) (tenant='{tenant_id}')")

    success = unified_service.process_webhook(
        ChannelType.TELEGRAM, raw_data, tenant_id=tenant_id, adapter_override=adapter_override
    )
    if success:
        logger.info("Webhook de Telegram procesado exitosamente")
    else:
        logger.warning("Webhook de Telegram procesado con errores")
    return success


@telegram_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    Webhook genérico para Telegram (usa settings globales).
    Soporta X-Tenant-ID / ?tenant_id= para enrutamiento manual.
    """
    try:
        raw_data = request.get_json()
        if not raw_data:
            logger.warning("Webhook de Telegram recibido sin datos JSON")
            return "OK", 200

        tenant_id = (
            request.headers.get("X-Tenant-ID")
            or request.args.get("tenant_id")
            or settings.default_tenant_id
        )

        _process_telegram(raw_data, tenant_id)
        return "OK", 200

    except Exception as e:
        logger.error(f"Error procesando webhook de Telegram: {e}")
        return "OK", 200  # Telegram requiere respuesta 200 siempre


@telegram_bp.route('/webhook/telegram/<tenant_id>', methods=['POST'])
def telegram_webhook_tenant(tenant_id: str):
    """
    Webhook dedicado por tenant para Telegram.
    Cada cliente configura su bot con su propia URL:
      https://api.telegram.org/bot<TOKEN>/setWebhook?url=.../webhook/telegram/<tenant_id>
    """
    try:
        raw_data = request.get_json()
        if not raw_data:
            logger.warning(f"Webhook de Telegram (tenant={tenant_id}) recibido sin datos JSON")
            return "OK", 200

        adapter_override = None
        try:
            from core.config.dependencies import DependencyContainer
            svc = DependencyContainer.get("TenantChannelService")
            tenant_ch = svc.get_channel(tenant_id, "telegram")
            if tenant_ch and tenant_ch.token:
                logger.info(f"[Telegram] Usando token personalizado para tenant='{tenant_id}'")
                adapter_override = TelegramAdapter(token=tenant_ch.token)
            else:
                logger.warning(
                    f"[Telegram] No hay canal configurado para tenant='{tenant_id}' — usando token por defecto"
                )
        except KeyError:
            logger.debug("TenantChannelService no registrado — usando token por defecto")
        except Exception as e:
            logger.warning(f"[Telegram] Error obteniendo canal de DB para tenant='{tenant_id}': {e}")

        _process_telegram(raw_data, tenant_id, adapter_override=adapter_override)
        return "OK", 200

    except Exception as e:
        logger.error(f"Error procesando webhook de Telegram (tenant={tenant_id}): {e}")
        return "OK", 200
