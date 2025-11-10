"""
Entidad Message - Representa un mensaje en el sistema.
Cumple con el principio de Single Responsibility.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class MessageType(Enum):
    """Tipos de mensaje soportados."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    VIDEO = "video"


class MessageRole(Enum):
    """Roles en una conversación."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """
    Entidad que representa un mensaje individual.
    
    Attributes:
        id: Identificador único del mensaje
        content: Contenido del mensaje
        role: Rol del emisor (user, assistant, system)
        message_type: Tipo de mensaje
        user_id: ID del usuario que envió el mensaje
        conversation_id: ID de la conversación a la que pertenece
        timestamp: Momento en que se creó el mensaje
        metadata: Información adicional (file_path, media_id, etc.)
    """
    content: str
    role: MessageRole
    user_id: str
    conversation_id: str
    message_type: MessageType = MessageType.TEXT
    id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validaciones después de la inicialización."""
        if not self.content and self.message_type == MessageType.TEXT:
            raise ValueError("El contenido del mensaje no puede estar vacío para mensajes de texto")
        
        if not self.user_id:
            raise ValueError("El user_id es obligatorio")
        
        if not self.conversation_id:
            raise ValueError("El conversation_id es obligatorio")
    
    def to_dict(self) -> dict:
        """Convierte el mensaje a formato dict para OpenAI."""
        return {
            "role": self.role.value,
            "content": self.content
        }
    
    def to_persistence_dict(self) -> dict:
        """Convierte el mensaje a formato dict para persistencia."""
        return {
            "id": self.id,
            "content": self.content,
            "role": self.role.value,
            "message_type": self.message_type.value,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def has_media(self) -> bool:
        """Verifica si el mensaje tiene contenido multimedia."""
        return self.message_type != MessageType.TEXT
    
    def get_media_path(self) -> Optional[str]:
        """Obtiene la ruta del archivo multimedia si existe."""
        return self.metadata.get("file_path")
