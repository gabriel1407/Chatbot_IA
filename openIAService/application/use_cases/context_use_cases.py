"""
Context Use Cases - Casos de uso para gestión de contexto de conversaciones.
Implementa Clean Architecture y principios SOLID.
"""
from datetime import datetime
from typing import Optional, List
from domain.entities.conversation import Conversation
from domain.entities.message import Message, MessageRole
from domain.repositories.conversation_repository import ConversationRepository
from infrastructure.persistence.sqlite_conversation_repository import TopicDetectionService
from core.logging.logger import get_application_logger


class RetrieveContextUseCase:
    """
    Caso de uso para recuperar el contexto de una conversación.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        topic_detection_service: TopicDetectionService
    ):
        self.conversation_repository = conversation_repository
        self.topic_detection_service = topic_detection_service
        self.logger = get_application_logger()
    
    def execute(
        self,
        user_id: str,
        context_id: Optional[str] = None,
        auto_detect_topic: bool = True,
        user_message: Optional[str] = None
    ) -> Conversation:
        """
        Ejecuta la recuperación de contexto.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto específico (opcional)
            auto_detect_topic: Si debe auto-detectar nuevo tema
            user_message: Mensaje del usuario para detectar tema
            
        Returns:
            Conversación recuperada o nueva
        """
        try:
            # Auto-detectar nuevo tema si es necesario
            if auto_detect_topic and user_message and self.topic_detection_service.detect_new_topic(user_message):
                # Crear nuevo context_id basado en timestamp
                new_context_id = f"tema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.logger.info(f"Nuevo tema detectado para user={user_id}, nuevo context={new_context_id}")
                context_id = new_context_id
            
            # Usar context_id proporcionado o obtener el activo
            if context_id is None:
                context_id = self.conversation_repository.get_active_context_id(user_id)
            
            # Buscar conversación existente
            conversation = self.conversation_repository.find_by_user_and_context(user_id, context_id)
            
            # Crear nueva conversación si no existe
            if conversation is None:
                conversation = Conversation(
                    user_id=user_id,
                    context_id=context_id,
                    id=f"{user_id}:{context_id}"
                )
                self.logger.info(f"Nueva conversación creada: user={user_id}, context={context_id}")
            else:
                self.logger.info(f"Conversación existente recuperada: user={user_id}, context={context_id}")
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error en RetrieveContextUseCase: {e}")
            # Retornar conversación por defecto en caso de error
            return Conversation(
                user_id=user_id,
                context_id="default",
                id=f"{user_id}:default"
            )


class SaveContextUseCase:
    """
    Caso de uso para guardar el contexto de una conversación.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(self, conversation_repository: ConversationRepository):
        self.conversation_repository = conversation_repository
        self.logger = get_application_logger()
    
    def execute(self, conversation: Conversation) -> bool:
        """
        Ejecuta el guardado de contexto.
        
        Args:
            conversation: Conversación a guardar
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Validar conversación
            if not conversation or not conversation.user_id:
                self.logger.error("Conversación inválida para guardar")
                return False
            
            # Guardar en repositorio
            saved_conversation = self.conversation_repository.save(conversation)
            
            if saved_conversation:
                self.logger.info(
                    f"Contexto guardado exitosamente: user={conversation.user_id}, "
                    f"context={conversation.context_id}, messages={len(conversation.messages)}"
                )
                return True
            else:
                self.logger.error("Error guardando contexto: repositorio retornó None")
                return False
                
        except Exception as e:
            self.logger.error(f"Error en SaveContextUseCase: {e}")
            return False


class AddMessageToContextUseCase:
    """
    Caso de uso para agregar un mensaje al contexto de conversación.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        retrieve_context_use_case: RetrieveContextUseCase,
        save_context_use_case: SaveContextUseCase
    ):
        self.conversation_repository = conversation_repository
        self.retrieve_context_use_case = retrieve_context_use_case
        self.save_context_use_case = save_context_use_case
        self.logger = get_application_logger()
    
    def execute(
        self,
        user_id: str,
        message_content: str,
        message_role: MessageRole,
        context_id: Optional[str] = None,
        auto_detect_topic: bool = True
    ) -> Conversation:
        """
        Ejecuta la adición de mensaje al contexto.
        
        Args:
            user_id: ID del usuario
            message_content: Contenido del mensaje
            message_role: Rol del mensaje (user, assistant, system)
            context_id: ID del contexto específico (opcional)
            auto_detect_topic: Si debe auto-detectar nuevo tema
            
        Returns:
            Conversación actualizada
        """
        try:
            # Recuperar o crear conversación
            user_message = message_content if message_role == MessageRole.USER else None
            conversation = self.retrieve_context_use_case.execute(
                user_id=user_id,
                context_id=context_id,
                auto_detect_topic=auto_detect_topic,
                user_message=user_message
            )
            
            # Crear mensaje
            message = Message(
                content=message_content,
                role=message_role,
                user_id=user_id,
                conversation_id=conversation.id
            )
            
            # Agregar mensaje a conversación
            conversation.add_message(message)
            
            # Guardar conversación actualizada
            save_success = self.save_context_use_case.execute(conversation)
            
            if save_success:
                self.logger.info(
                    f"Mensaje agregado al contexto: user={user_id}, role={message_role.value}, "
                    f"context={conversation.context_id}"
                )
            else:
                self.logger.warning(f"Error guardando mensaje en contexto para user={user_id}")
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error en AddMessageToContextUseCase: {e}")
            # Retornar conversación por defecto en caso de error
            return Conversation(user_id=user_id, context_id="default")


class ListUserContextsUseCase:
    """
    Caso de uso para listar todos los contextos de un usuario.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(self, conversation_repository: ConversationRepository):
        self.conversation_repository = conversation_repository
        self.logger = get_application_logger()
    
    def execute(self, user_id: str) -> List[Conversation]:
        """
        Ejecuta la lista de contextos de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de conversaciones del usuario
        """
        try:
            conversations = self.conversation_repository.find_all_by_user(user_id)
            
            self.logger.info(f"Listados {len(conversations)} contextos para user={user_id}")
            return conversations
            
        except Exception as e:
            self.logger.error(f"Error en ListUserContextsUseCase: {e}")
            return []


class DeleteContextUseCase:
    """
    Caso de uso para eliminar un contexto específico.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(self, conversation_repository: ConversationRepository):
        self.conversation_repository = conversation_repository
        self.logger = get_application_logger()
    
    def execute(self, user_id: str, context_id: str) -> bool:
        """
        Ejecuta la eliminación de un contexto.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            conversation_id = f"{user_id}:{context_id}"
            deleted = self.conversation_repository.delete(conversation_id)
            
            if deleted:
                self.logger.info(f"Contexto eliminado: user={user_id}, context={context_id}")
            else:
                self.logger.warning(f"Contexto no encontrado para eliminar: user={user_id}, context={context_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error en DeleteContextUseCase: {e}")
            return False


class GetActiveContextUseCase:
    """
    Caso de uso para obtener el contexto activo de un usuario.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(self, conversation_repository: ConversationRepository):
        self.conversation_repository = conversation_repository
        self.logger = get_application_logger()
    
    def execute(self, user_id: str) -> str:
        """
        Ejecuta la obtención del contexto activo.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            ID del contexto activo
        """
        try:
            context_id = self.conversation_repository.get_active_context_id(user_id)
            
            self.logger.debug(f"Contexto activo para user={user_id}: {context_id}")
            return context_id
            
        except Exception as e:
            self.logger.error(f"Error en GetActiveContextUseCase: {e}")
            return "default"