"""
Context Service Adapter - Adaptador para mantener compatibilidad con el código existente.
Implementa el patrón Adapter y facilita la migración gradual.
"""
from typing import Optional, List
from datetime import datetime

# Importar la nueva arquitectura
from infrastructure.persistence.conversation_repository_factory import create_conversation_repository
from infrastructure.persistence.topic_detection_service import TopicDetectionService
from application.use_cases.context_use_cases import (
    RetrieveContextUseCase,
    SaveContextUseCase,
    AddMessageToContextUseCase,
    ListUserContextsUseCase,
    DeleteContextUseCase,
    GetActiveContextUseCase
)
from domain.entities.message import MessageRole
from core.logging.logger import get_application_logger


class ContextServiceAdapter:
    """
    Adaptador que mantiene la interfaz del context_service.py original
    pero usa la nueva arquitectura internamente.
    """
    
    def __init__(self, db_path: str = "local/contextos.db"):
        self.logger = get_application_logger()
        
        # Inicializar componentes de la nueva arquitectura
        self.conversation_repository = create_conversation_repository(db_path=db_path)
        self.topic_detection_service = TopicDetectionService()
        
        # Inicializar casos de uso
        self.retrieve_context_use_case = RetrieveContextUseCase(
            self.conversation_repository,
            self.topic_detection_service
        )
        self.save_context_use_case = SaveContextUseCase(self.conversation_repository)
        self.add_message_use_case = AddMessageToContextUseCase(
            self.conversation_repository,
            self.retrieve_context_use_case,
            self.save_context_use_case
        )
        self.list_contexts_use_case = ListUserContextsUseCase(self.conversation_repository)
        self.delete_context_use_case = DeleteContextUseCase(self.conversation_repository)
        self.get_active_context_use_case = GetActiveContextUseCase(self.conversation_repository)
    
    def load_context(self, user_id: str, context_id: Optional[str] = None) -> List[dict]:
        """
        Mantiene compatibilidad con la función original load_context().
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto (opcional)
            
        Returns:
            Lista de mensajes en formato dict para OpenAI
        """
        try:
            conversation = self.retrieve_context_use_case.execute(
                user_id=str(user_id),
                context_id=context_id,
                auto_detect_topic=False  # No auto-detectar en carga manual
            )
            
            # Convertir a formato original (lista de dicts)
            return conversation.get_messages_for_llm()
            
        except Exception as e:
            self.logger.error(f"Error en load_context adaptado: {e}")
            return []
    
    def save_context(
        self, 
        user_id: str, 
        context: List[dict], 
        context_id: Optional[str] = None
    ) -> bool:
        """
        Mantiene compatibilidad con la función original save_context().
        
        Args:
            user_id: ID del usuario
            context: Lista de mensajes en formato dict
            context_id: ID del contexto (opcional)
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            if context_id is None:
                context_id = "default"
            
            # Recuperar conversación existente
            conversation = self.retrieve_context_use_case.execute(
                user_id=str(user_id),
                context_id=context_id,
                auto_detect_topic=False
            )
            
            # Limpiar mensajes existentes
            conversation.clear_messages()
            
            # Agregar mensajes del contexto
            from domain.entities.message import Message, MessageType
            for msg_dict in context:
                try:
                    role = MessageRole(msg_dict.get("role", "user"))
                    message = Message(
                        content=msg_dict.get("content", ""),
                        role=role,
                        user_id=str(user_id),
                        conversation_id=conversation.id,
                        message_type=MessageType.TEXT
                    )
                    conversation.add_message(message)
                except Exception as e:
                    self.logger.warning(f"Error agregando mensaje al contexto: {e}")
            
            # Guardar conversación
            return self.save_context_use_case.execute(conversation)
            
        except Exception as e:
            self.logger.error(f"Error en save_context adaptado: {e}")
            return False
    
    def get_active_context_id(self, user_id: str) -> str:
        """
        Mantiene compatibilidad con la función original get_active_context_id().
        
        Args:
            user_id: ID del usuario
            
        Returns:
            ID del contexto activo
        """
        return self.get_active_context_use_case.execute(str(user_id))
    
    def detect_new_topic(self, user_input: str) -> bool:
        """
        Mantiene compatibilidad con la función original detect_new_topic().
        
        Args:
            user_input: Entrada del usuario
            
        Returns:
            True si se detecta cambio de tema
        """
        return self.topic_detection_service.detect_new_topic(user_input)
    
    def list_contexts(self, user_id: str) -> List[tuple]:
        """
        Mantiene compatibilidad con la función original list_contexts().
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de tuplas (context_id, last_updated)
        """
        try:
            conversations = self.list_contexts_use_case.execute(str(user_id))
            
            # Convertir a formato original (tuplas)
            result = []
            for conv in conversations:
                result.append((conv.context_id, conv.updated_at.isoformat()))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en list_contexts adaptado: {e}")
            return []
    
    def delete_context(self, user_id: str, context_id: str) -> bool:
        """
        Mantiene compatibilidad con la función original delete_context().
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        return self.delete_context_use_case.execute(str(user_id), context_id)
    
    # Nuevos métodos que aprovechan la nueva arquitectura
    
    def add_user_message(
        self, 
        user_id: str, 
        message_content: str, 
        context_id: Optional[str] = None,
        auto_detect_topic: bool = True
    ) -> List[dict]:
        """
        Agrega un mensaje del usuario al contexto y retorna la conversación actualizada.
        
        Args:
            user_id: ID del usuario
            message_content: Contenido del mensaje
            context_id: ID del contexto (opcional)
            auto_detect_topic: Si debe auto-detectar nuevo tema
            
        Returns:
            Lista de mensajes actualizada en formato dict
        """
        conversation = self.add_message_use_case.execute(
            user_id=str(user_id),
            message_content=message_content,
            message_role=MessageRole.USER,
            context_id=context_id,
            auto_detect_topic=auto_detect_topic
        )
        
        return conversation.get_messages_for_llm()
    
    def add_assistant_message(
        self, 
        user_id: str, 
        response_content: str, 
        context_id: Optional[str] = None
    ) -> List[dict]:
        """
        Agrega una respuesta del asistente al contexto.
        
        Args:
            user_id: ID del usuario
            response_content: Contenido de la respuesta
            context_id: ID del contexto (opcional)
            
        Returns:
            Lista de mensajes actualizada en formato dict
        """
        conversation = self.add_message_use_case.execute(
            user_id=str(user_id),
            message_content=response_content,
            message_role=MessageRole.ASSISTANT,
            context_id=context_id,
            auto_detect_topic=False  # No detectar tema en respuestas
        )
        
        return conversation.get_messages_for_llm()
    
    def get_conversation_summary(self, user_id: str, context_id: Optional[str] = None) -> dict:
        """
        Obtiene un resumen de la conversación.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto (opcional)
            
        Returns:
            Diccionario con resumen de la conversación
        """
        try:
            conversation = self.retrieve_context_use_case.execute(
                user_id=str(user_id),
                context_id=context_id,
                auto_detect_topic=False
            )
            
            return {
                "user_id": conversation.user_id,
                "context_id": conversation.context_id,
                "message_count": conversation.count_messages(),
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "last_message": conversation.get_last_message().content if conversation.get_last_message() else None
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de conversación: {e}")
            return {}


# Instancia global para compatibilidad hacia atrás
_context_adapter = None

def get_context_adapter() -> ContextServiceAdapter:
    """
    Factory function para obtener la instancia del adaptador.
    Implementa patrón Singleton para compatibilidad.
    """
    global _context_adapter
    if _context_adapter is None:
        _context_adapter = ContextServiceAdapter()
    return _context_adapter


# Funciones de compatibilidad que mantienen la interfaz original
def load_context(user_id: str, context_id: Optional[str] = None) -> List[dict]:
    """Función de compatibilidad para load_context original."""
    return get_context_adapter().load_context(user_id, context_id)


def save_context(user_id: str, context: List[dict], context_id: Optional[str] = None) -> bool:
    """Función de compatibilidad para save_context original."""
    return get_context_adapter().save_context(user_id, context, context_id)


def get_active_context_id(user_id: str) -> str:
    """Función de compatibilidad para get_active_context_id original."""
    return get_context_adapter().get_active_context_id(user_id)


def detect_new_topic(user_input: str) -> bool:
    """Función de compatibilidad para detect_new_topic original."""
    return get_context_adapter().detect_new_topic(user_input)


def list_contexts(user_id: str) -> List[tuple]:
    """Función de compatibilidad para list_contexts original."""
    return get_context_adapter().list_contexts(user_id)


def delete_context(user_id: str, context_id: str) -> bool:
    """Función de compatibilidad para delete_context original."""
    return get_context_adapter().delete_context(user_id, context_id)