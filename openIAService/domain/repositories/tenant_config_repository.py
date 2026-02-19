"""
TenantConfigRepository Interface - Contrato para persistencia de configuración de tenants.
Cumple con el principio de Inversión de Dependencias (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.tenant_config import TenantConfig


class TenantConfigRepository(ABC):
    """Interface para repositorio de configuración de tenants."""

    @abstractmethod
    def save(self, config: TenantConfig) -> TenantConfig:
        """Crea o actualiza la configuración de un tenant."""
        pass

    @abstractmethod
    def find_by_id(self, tenant_id: str) -> Optional[TenantConfig]:
        """Retorna la configuración de un tenant o None si no existe."""
        pass

    @abstractmethod
    def find_all(self) -> List[TenantConfig]:
        """Lista todos los tenants registrados."""
        pass

    @abstractmethod
    def delete(self, tenant_id: str) -> bool:
        """Elimina la configuración de un tenant. Retorna True si existía."""
        pass
