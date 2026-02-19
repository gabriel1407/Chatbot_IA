"""
TenantChannelService - Servicio con caché para lookup de canales por tenant.
Resuelve el tenant_id a partir de identificadores de canal (phone_number_id, etc.)
"""
import threading
import time
from typing import Optional, Dict, List

from core.logging.logger import get_infrastructure_logger
from domain.entities.tenant_channel import TenantChannel
from domain.repositories.tenant_channel_repository import TenantChannelRepository


class TenantChannelService:
    """
    Servicio de lookup de canales con caché en memoria (TTL 5 minutos).

    Uso principal:
    - WhatsApp webhook: get_tenant_by_phone_number_id(phone_number_id)
    - Telegram webhook: get_channel(tenant_id, "telegram")
    - Envío de mensajes: get_token(tenant_id, channel)
    """

    CACHE_TTL = 300  # 5 minutos

    def __init__(self, repo: TenantChannelRepository):
        self._repo = repo
        self._logger = get_infrastructure_logger()
        self._lock = threading.Lock()

        # Cache: phone_number_id → TenantChannel
        self._phone_cache: Dict[str, tuple] = {}   # {phone_number_id: (channel, ts)}
        # Cache: (tenant_id, channel) → TenantChannel
        self._channel_cache: Dict[tuple, tuple] = {}  # {(tid,ch): (channel, ts)}

    # ------------------------------------------------------------------ #
    # Lookups principales                                                  #
    # ------------------------------------------------------------------ #

    def get_tenant_by_phone_number_id(self, phone_number_id: str) -> Optional[TenantChannel]:
        """
        Resuelve qué tenant es dueño de ese número de WhatsApp Business.
        Devuelve None si no está registrado en la DB (usa config de .env como fallback).
        """
        with self._lock:
            cached = self._phone_cache.get(phone_number_id)
            if cached and (time.time() - cached[1]) < self.CACHE_TTL:
                return cached[0]

        result = self._repo.find_by_phone_number_id(phone_number_id)

        with self._lock:
            self._phone_cache[phone_number_id] = (result, time.time())

        if result:
            self._logger.debug(f"[TenantChannel] phone_number_id={phone_number_id} -> tenant={result.tenant_id}")
        else:
            self._logger.debug(f"[TenantChannel] phone_number_id={phone_number_id} -> no encontrado en DB")

        return result

    def get_channel(self, tenant_id: str, channel: str) -> Optional[TenantChannel]:
        """Obtiene las credenciales de un canal para un tenant."""
        key = (tenant_id, channel)
        with self._lock:
            cached = self._channel_cache.get(key)
            if cached and (time.time() - cached[1]) < self.CACHE_TTL:
                return cached[0]

        result = self._repo.find_by_tenant_and_channel(tenant_id, channel)

        with self._lock:
            self._channel_cache[key] = (result, time.time())

        return result

    def get_token(self, tenant_id: str, channel: str) -> Optional[str]:
        """Obtiene solo el token de un canal. Devuelve None si no está en DB."""
        ch = self.get_channel(tenant_id, channel)
        return ch.token if ch else None

    def get_channels_for_tenant(self, tenant_id: str) -> List[TenantChannel]:
        """Lista todos los canales de un tenant."""
        return self._repo.find_by_tenant_id(tenant_id)

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def save(self, channel: TenantChannel) -> TenantChannel:
        result = self._repo.save(channel)
        self.invalidate_cache(channel.tenant_id, channel.channel)
        return result

    def delete(self, tenant_id: str, channel: str) -> bool:
        ok = self._repo.delete(tenant_id, channel)
        self.invalidate_cache(tenant_id, channel)
        return ok

    def list_all(self) -> List[TenantChannel]:
        return self._repo.find_all_active()

    # ------------------------------------------------------------------ #
    # Cache                                                                #
    # ------------------------------------------------------------------ #

    def invalidate_cache(self, tenant_id: str, channel: str):
        with self._lock:
            key = (tenant_id, channel)
            self._channel_cache.pop(key, None)
            # Limpiar también la caché de phone_number_id para ese tenant
            to_remove = [k for k, v in self._phone_cache.items()
                         if v[0] and v[0].tenant_id == tenant_id]
            for k in to_remove:
                self._phone_cache.pop(k, None)
