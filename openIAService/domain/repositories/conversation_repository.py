"""
Interface ConversationRepository - Define el contrato para persistencia de conversaciones.
Cumple con el principio de Inversión de Dependencias (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.conversation import Conversation


class ConversationRepository(ABC):
    """
    Interface para repositorio de conversaciones.
    Las implementaciones concretas estarán en la capa de infraestructura.
    """
    
    @abstractmethod
    def save(self, conversation: Conversation) -> Conversation:
        """
        Guarda o actualiza una conversación.
        
        Args:
            conversation: Conversación a guardar
            
        Returns:
            Conversación guardada con ID asignado
        """
        pass
    
    @abstractmethod
    def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Busca una conversación por su ID.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Conversación encontrada o None
        """
        pass
    
    @abstractmethod
    def find_by_user_and_context(
        self,
        user_id: str,
        context_id: str = "default"
    ) -> Optional[Conversation]:
        """
        Busca una conversación por usuario y contexto.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto/tema
            
        Returns:
            Conversación encontrada o None
        """
        pass
    
    @abstractmethod
    def find_all_by_user(self, user_id: str) -> List[Conversation]:
        """
        Busca todas las conversaciones de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        pass
    
    @abstractmethod
    def delete(self, conversation_id: str) -> bool:
        """
        Elimina una conversación.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            True si se eliminó, False si no existía
        """
        pass
    
    @abstractmethod
    def get_active_context_id(self, user_id: str) -> str:
        """
        Obtiene el context_id más reciente de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Context ID activo o "default"
        """
        pass
