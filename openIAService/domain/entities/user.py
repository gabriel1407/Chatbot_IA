"""
Entidad User - Representa un usuario del sistema.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class UserChannel(Enum):
    """Canales de comunicación soportados."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    API = "api"


@dataclass
class User:
    """
    Entidad que representa un usuario del sistema.
    
    Attributes:
        id: Identificador único del usuario (phone number, telegram_id, etc.)
        channel: Canal por el que se comunica
        name: Nombre del usuario (opcional)
        language: Idioma preferido
        created_at: Fecha de registro
        last_interaction: Última interacción
        metadata: Información adicional
    """
    id: str
    channel: UserChannel
    language: str = "es"
    name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validaciones después de la inicialización."""
        if not self.id:
            raise ValueError("El user_id es obligatorio")
    
    def update_last_interaction(self) -> None:
        """Actualiza el timestamp de última interacción."""
        self.last_interaction = datetime.now()
    
    def to_dict(self) -> dict:
        """Convierte el usuario a formato dict."""
        return {
            "id": self.id,
            "channel": self.channel.value,
            "name": self.name,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "metadata": self.metadata
        }
