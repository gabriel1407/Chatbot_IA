"""
Entidad Conversation - Representa una conversación completa.
Agrupa mensajes y gestiona el contexto.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from domain.entities.message import Message, MessageRole


@dataclass
class Conversation:
    """
    Entidad que representa una conversación completa.
    
    Attributes:
        id: Identificador único de la conversación
        user_id: ID del usuario propietario
        context_id: ID del contexto/tema (para múltiples conversaciones por usuario)
        messages: Lista de mensajes en la conversación
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        metadata: Información adicional (canal, idioma, etc.)
    """
    user_id: str
    context_id: str = "default"
    id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validaciones después de la inicialización."""
        if not self.user_id:
            raise ValueError("El user_id es obligatorio")
    
    def add_message(self, message: Message) -> None:
        """
        Agrega un mensaje a la conversación.
        
        Args:
            message: Mensaje a agregar
        """
        if message.user_id != self.user_id:
            raise ValueError("El mensaje no pertenece a este usuario")
        
        if message.conversation_id != self.id:
            message.conversation_id = self.id
        
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_messages_for_llm(self, limit: Optional[int] = None) -> List[dict]:
        """
        Obtiene los mensajes en formato compatible con OpenAI.
        
        Args:
            limit: Número máximo de mensajes a retornar (None = todos)
            
        Returns:
            Lista de mensajes en formato dict
        """
        messages_to_return = self.messages[-limit:] if limit else self.messages
        return [msg.to_dict() for msg in messages_to_return]
    
    def get_last_message(self) -> Optional[Message]:
        """Obtiene el último mensaje de la conversación."""
        return self.messages[-1] if self.messages else None
    
    def get_user_messages(self) -> List[Message]:
        """Obtiene solo los mensajes del usuario."""
        return [msg for msg in self.messages if msg.role == MessageRole.USER]
    
    def get_assistant_messages(self) -> List[Message]:
        """Obtiene solo los mensajes del asistente."""
        return [msg for msg in self.messages if msg.role == MessageRole.ASSISTANT]
    
    def count_messages(self) -> int:
        """Cuenta el número total de mensajes."""
        return len(self.messages)
    
    def clear_messages(self) -> None:
        """Limpia todos los mensajes de la conversación."""
        self.messages = []
        self.updated_at = datetime.now()
    
    def to_persistence_dict(self) -> dict:
        """Convierte la conversación a formato dict para persistencia."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "context_id": self.context_id,
            "messages": [msg.to_persistence_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
