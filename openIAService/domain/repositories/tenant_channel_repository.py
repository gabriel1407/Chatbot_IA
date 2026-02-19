"""
TenantChannelRepository - Interface del repositorio de canales por tenant.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.tenant_channel import TenantChannel


class TenantChannelRepository(ABC):

    @abstractmethod
    def save(self, channel: TenantChannel) -> TenantChannel:
        """Crea o actualiza un canal de tenant."""
        ...

    @abstractmethod
    def find_by_tenant_and_channel(self, tenant_id: str, channel: str) -> Optional[TenantChannel]:
        """Obtiene las credenciales de un canal específico para un tenant."""
        ...

    @abstractmethod
    def find_by_phone_number_id(self, phone_number_id: str) -> Optional[TenantChannel]:
        """
        Busca el tenant dueño de un número de WhatsApp Business.
        Usado para routing automático de webhooks entrantes.
        """
        ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: str) -> List[TenantChannel]:
        """Lista todos los canales activos de un tenant."""
        ...

    @abstractmethod
    def find_all_active(self) -> List[TenantChannel]:
        """Lista todos los canales activos (todos los tenants)."""
        ...

    @abstractmethod
    def delete(self, tenant_id: str, channel: str) -> bool:
        """Elimina el canal de un tenant."""
        ...
