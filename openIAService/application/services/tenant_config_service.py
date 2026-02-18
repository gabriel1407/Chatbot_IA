"""
TenantConfigService — Carga y cachea la configuración del bot por tenant.

Flujo:
  1. La primera vez que se pide la config de un tenant, se busca en MySQL.
  2. Se guarda en memoria con un TTL (por defecto 5 minutos).
  3. Si no existe en DB, devuelve un TenantConfig con valores por defecto.

El caché evita golpear la DB en cada mensaje entrante de WhatsApp/Telegram.
"""
import threading
import time
from typing import Optional, Dict, Tuple

from domain.entities.tenant_config import TenantConfig
from domain.repositories.tenant_config_repository import TenantConfigRepository
from core.logging.logger import get_application_logger

logger = get_application_logger()

# Tenant por defecto que se usa cuando no hay config en la DB
DEFAULT_TENANT_ID = "default"

# TTL del caché en segundos
_CACHE_TTL = 300  # 5 minutos


class TenantConfigService:
    """
    Servicio de configuración de tenants con caché en memoria.
    Thread-safe gracias a un Lock por lectura/escritura del dict.
    """

    def __init__(self, repository: TenantConfigRepository, cache_ttl: int = _CACHE_TTL):
        self._repo = repository
        self._ttl = cache_ttl
        # _cache[tenant_id] = (TenantConfig, expires_at)
        self._cache: Dict[str, Tuple[TenantConfig, float]] = {}
        self._lock = threading.Lock()

        # Seed: si no existe "default" en DB, lo creamos con valores vacíos
        self._ensure_default_tenant()

    # ------------------------------------------------------------------ #
    # Acceso principal                                                      #
    # ------------------------------------------------------------------ #

    def get(self, tenant_id: str = DEFAULT_TENANT_ID) -> TenantConfig:
        """
        Retorna la configuración del tenant.
        Primero busca en caché, luego en DB.
        Si no existe, retorna la config del tenant 'default'.
        """
        config = self._get_from_cache(tenant_id)
        if config:
            return config

        # Buscar en DB
        config = self._repo.find_by_id(tenant_id)
        if config is None:
            # Fallback a "default"
            if tenant_id != DEFAULT_TENANT_ID:
                logger.warning(f"[TenantConfig] '{tenant_id}' no encontrado. Usando 'default'.")
                config = self._repo.find_by_id(DEFAULT_TENANT_ID)
            if config is None:
                config = TenantConfig(tenant_id=DEFAULT_TENANT_ID)

        self._set_cache(tenant_id, config)
        return config

    def save(self, config: TenantConfig) -> TenantConfig:
        """Guarda/actualiza y limpia la caché de ese tenant."""
        saved = self._repo.save(config)
        self._invalidate(config.tenant_id)
        logger.info(f"[TenantConfig] Config guardada y caché invalidada para '{config.tenant_id}'")
        return saved

    def delete(self, tenant_id: str) -> bool:
        result = self._repo.delete(tenant_id)
        self._invalidate(tenant_id)
        return result

    def list_all(self):
        return self._repo.find_all()

    def invalidate_cache(self, tenant_id: Optional[str] = None):
        """Invalida el caché de un tenant o de todos si no se especifica."""
        with self._lock:
            if tenant_id:
                self._cache.pop(tenant_id, None)
            else:
                self._cache.clear()
        logger.info(f"[TenantConfig] Caché invalidado para: {tenant_id or 'TODOS'}")

    # ------------------------------------------------------------------ #
    # Helpers internos                                                      #
    # ------------------------------------------------------------------ #

    def _get_from_cache(self, tenant_id: str) -> Optional[TenantConfig]:
        with self._lock:
            entry = self._cache.get(tenant_id)
        if entry is None:
            return None
        config, expires_at = entry
        if time.monotonic() > expires_at:
            self._invalidate(tenant_id)
            return None
        return config

    def _set_cache(self, tenant_id: str, config: TenantConfig) -> None:
        expires_at = time.monotonic() + self._ttl
        with self._lock:
            self._cache[tenant_id] = (config, expires_at)

    def _invalidate(self, tenant_id: str) -> None:
        with self._lock:
            self._cache.pop(tenant_id, None)

    def _ensure_default_tenant(self) -> None:
        """Crea el tenant 'default' en DB si todavía no existe."""
        try:
            existing = self._repo.find_by_id(DEFAULT_TENANT_ID)
            if existing is None:
                default_cfg = TenantConfig(tenant_id=DEFAULT_TENANT_ID)
                self._repo.save(default_cfg)
                logger.info("[TenantConfig] Tenant 'default' creado en DB con valores iniciales.")
        except Exception as e:
            logger.warning(f"[TenantConfig] No se pudo crear tenant default: {e}")
