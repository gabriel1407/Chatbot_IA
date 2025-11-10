"""
Improved Message Handler Service - Servicio mejorado para manejo de mensajes.
Implementa principios SOLID y Dependency Injection.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from domain.entities.message import Message, MessageRole, MessageType
from domain.entities.conversation import Conversation
from application.use_cases.context_use_cases import (
    AddMessageToContextUseCase,
    RetrieveContextUseCase
)
from core.logging.logger import get_application_logger


class MessageProcessingStrategy(ABC):
    """
    Strategy pattern para diferentes tipos de procesamiento de mensajes.
    Implementa Open/Closed Principle.
    """
    
    @abstractmethod
    def can_handle(self, message_type: MessageType) -> bool:
        """Determina si esta estrategia puede manejar el tipo de mensaje."""
        pass
    
    @abstractmethod
    def process(self, content: str, metadata: Dict[str, Any]) -> str:
        """Procesa el contenido del mensaje."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia."""
        pass


class TextProcessingStrategy(MessageProcessingStrategy):
    """Estrategia para procesar mensajes de texto."""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.TEXT
    
    def process(self, content: str, metadata: Dict[str, Any]) -> str:
        """Procesa texto directamente."""
        return content.strip()
    
    def get_strategy_name(self) -> str:
        return "TextProcessor"


class ImageProcessingStrategy(MessageProcessingStrategy):
    """Estrategia para procesar imágenes."""
    
    def __init__(self):
        # Aquí inyectarías el servicio de procesamiento de imágenes
        pass
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.IMAGE
    
    def process(self, content: str, metadata: Dict[str, Any]) -> str:
        """Procesa imagen usando OCR o análisis visual."""
        image_path = metadata.get("file_path")
        if not image_path:
            return "Error: No se proporcionó ruta de imagen"
        
        # Aquí llamarías al servicio de procesamiento de imágenes
        try:
            # from services.files_processing_service import process_image
            # extracted_text = process_image(image_path)
            # return extracted_text or "No se pudo extraer texto de la imagen"
            return f"[Procesando imagen: {image_path}]"
        except Exception as e:
            return f"Error procesando imagen: {e}"
    
    def get_strategy_name(self) -> str:
        return "ImageProcessor"


class AudioProcessingStrategy(MessageProcessingStrategy):
    """Estrategia para procesar audio."""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.AUDIO
    
    def process(self, content: str, metadata: Dict[str, Any]) -> str:
        """Procesa audio usando speech-to-text."""
        audio_path = metadata.get("file_path")
        if not audio_path:
            return "Error: No se proporcionó ruta de audio"
        
        try:
            # from services.files_processing_service import process_audio
            # extracted_text = process_audio(audio_path, 'es')
            # return extracted_text or "No se pudo transcribir el audio"
            return f"[Procesando audio: {audio_path}]"
        except Exception as e:
            return f"Error procesando audio: {e}"
    
    def get_strategy_name(self) -> str:
        return "AudioProcessor"


class DocumentProcessingStrategy(MessageProcessingStrategy):
    """Estrategia para procesar documentos."""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.DOCUMENT
    
    def process(self, content: str, metadata: Dict[str, Any]) -> str:
        """Procesa documentos PDF/DOCX."""
        file_path = metadata.get("file_path")
        file_type = metadata.get("file_type", "")
        
        if not file_path:
            return "Error: No se proporcionó ruta de documento"
        
        try:
            # from services.files_processing_service import process_document
            # extracted_text = process_document(file_path, file_type)
            # return extracted_text or "No se pudo extraer texto del documento"
            return f"[Procesando documento {file_type}: {file_path}]"
        except Exception as e:
            return f"Error procesando documento: {e}"
    
    def get_strategy_name(self) -> str:
        return "DocumentProcessor"


@dataclass
class ProcessedMessage:
    """Value Object que representa un mensaje procesado."""
    
    original_content: str
    processed_content: str
    message_type: MessageType
    strategy_used: str
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class MessageProcessorService:
    """
    Servicio para procesar mensajes usando estrategias.
    Implementa Strategy Pattern y Dependency Injection.
    """
    
    def __init__(self, strategies: Optional[list[MessageProcessingStrategy]] = None):
        self.logger = get_application_logger()
        self.strategies = strategies or self._get_default_strategies()
    
    def _get_default_strategies(self) -> list[MessageProcessingStrategy]:
        """Obtiene las estrategias por defecto."""
        return [
            TextProcessingStrategy(),
            ImageProcessingStrategy(),
            AudioProcessingStrategy(),
            DocumentProcessingStrategy()
        ]
    
    def add_strategy(self, strategy: MessageProcessingStrategy) -> None:
        """Agrega una nueva estrategia de procesamiento."""
        self.strategies.append(strategy)
        self.logger.info(f"Nueva estrategia agregada: {strategy.get_strategy_name()}")
    
    def process_message(
        self,
        content: str,
        message_type: MessageType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedMessage:
        """
        Procesa un mensaje usando la estrategia apropiada.
        
        Args:
            content: Contenido del mensaje
            message_type: Tipo de mensaje
            metadata: Metadatos adicionales
            
        Returns:
            ProcessedMessage con el resultado
        """
        metadata = metadata or {}
        
        # Buscar estrategia apropiada
        strategy = self._find_strategy(message_type)
        
        if not strategy:
            error_msg = f"No hay estrategia disponible para tipo {message_type.value}"
            self.logger.error(error_msg)
            return ProcessedMessage(
                original_content=content,
                processed_content=content,
                message_type=message_type,
                strategy_used="None",
                metadata=metadata,
                success=False,
                error_message=error_msg
            )
        
        try:
            # Procesar mensaje
            processed_content = strategy.process(content, metadata)
            
            self.logger.info(
                f"Mensaje procesado exitosamente con estrategia {strategy.get_strategy_name()}"
            )
            
            return ProcessedMessage(
                original_content=content,
                processed_content=processed_content,
                message_type=message_type,
                strategy_used=strategy.get_strategy_name(),
                metadata=metadata,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Error procesando mensaje: {e}"
            self.logger.error(error_msg)
            
            return ProcessedMessage(
                original_content=content,
                processed_content=content,
                message_type=message_type,
                strategy_used=strategy.get_strategy_name(),
                metadata=metadata,
                success=False,
                error_message=error_msg
            )
    
    def _find_strategy(self, message_type: MessageType) -> Optional[MessageProcessingStrategy]:
        """Encuentra la estrategia apropiada para el tipo de mensaje."""
        for strategy in self.strategies:
            if strategy.can_handle(message_type):
                return strategy
        return None
    
    def get_available_strategies(self) -> list[str]:
        """Obtiene los nombres de las estrategias disponibles."""
        return [strategy.get_strategy_name() for strategy in self.strategies]


class ImprovedMessageHandler:
    """
    Manejador de mensajes mejorado que implementa principios SOLID.
    Usa Dependency Injection y Clean Architecture.
    """
    
    def __init__(
        self,
        add_message_use_case: AddMessageToContextUseCase,
        retrieve_context_use_case: RetrieveContextUseCase,
        message_processor: MessageProcessorService,
        ai_service=None  # Aquí inyectarías el servicio de IA
    ):
        self.add_message_use_case = add_message_use_case
        self.retrieve_context_use_case = retrieve_context_use_case
        self.message_processor = message_processor
        self.ai_service = ai_service
        self.logger = get_application_logger()
    
    def handle_user_message(
        self,
        user_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None
    ) -> str:
        """
        Maneja un mensaje de usuario de forma integral.
        
        Args:
            user_id: ID del usuario
            content: Contenido del mensaje
            message_type: Tipo de mensaje
            metadata: Metadatos adicionales
            context_id: ID del contexto (opcional)
            
        Returns:
            Respuesta generada
        """
        try:
            self.logger.info(f"Procesando mensaje de usuario {user_id}: {message_type.value}")
            
            # 1. Procesar mensaje según su tipo
            processed_msg = self.message_processor.process_message(content, message_type, metadata)
            
            if not processed_msg.success:
                self.logger.error(f"Error procesando mensaje: {processed_msg.error_message}")
                return f"Error procesando tu mensaje: {processed_msg.error_message}"
            
            # 2. Agregar mensaje del usuario al contexto
            conversation = self.add_message_use_case.execute(
                user_id=user_id,
                message_content=processed_msg.processed_content,
                message_role=MessageRole.USER,
                context_id=context_id,
                auto_detect_topic=True
            )
            
            # 3. Generar respuesta con IA (simulado por ahora)
            ai_response = self._generate_ai_response(conversation, processed_msg)
            
            # 4. Agregar respuesta del asistente al contexto
            updated_conversation = self.add_message_use_case.execute(
                user_id=user_id,
                message_content=ai_response,
                message_role=MessageRole.ASSISTANT,
                context_id=conversation.context_id,
                auto_detect_topic=False
            )
            
            self.logger.info(f"Mensaje procesado exitosamente para usuario {user_id}")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error en handle_user_message: {e}")
            return "Lo siento, ocurrió un error procesando tu mensaje. Por favor intenta de nuevo."
    
    def _generate_ai_response(self, conversation: Conversation, processed_msg: ProcessedMessage) -> str:
        """
        Genera respuesta usando servicio de IA.
        Por ahora simula la respuesta, pero aquí se inyectaría el servicio real.
        """
        # Aquí llamarías al servicio de IA inyectado
        if self.ai_service:
            # return self.ai_service.generate_response(conversation.get_messages_for_llm())
            pass
        
        # Respuesta simulada por ahora
        if processed_msg.message_type == MessageType.TEXT:
            return f"Entiendo tu mensaje: '{processed_msg.processed_content[:100]}...' ¿En qué más puedo ayudarte?"
        elif processed_msg.message_type == MessageType.IMAGE:
            return "He analizado tu imagen. ¿Hay algo específico que te gustaría saber sobre ella?"
        elif processed_msg.message_type == MessageType.AUDIO:
            return "He transcrito tu audio. ¿Puedo ayudarte con algo más?"
        elif processed_msg.message_type == MessageType.DOCUMENT:
            return "He procesado tu documento. ¿Tienes alguna pregunta específica sobre su contenido?"
        else:
            return "He recibido tu mensaje. ¿Cómo puedo ayudarte?"
    
    def get_conversation_summary(self, user_id: str, context_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene un resumen de la conversación."""
        try:
            conversation = self.retrieve_context_use_case.execute(
                user_id=user_id,
                context_id=context_id,
                auto_detect_topic=False
            )
            
            return {
                "user_id": conversation.user_id,
                "context_id": conversation.context_id,
                "message_count": conversation.count_messages(),
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "last_message": conversation.get_last_message().content if conversation.get_last_message() else None,
                "available_strategies": self.message_processor.get_available_strategies()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de conversación: {e}")
            return {"error": str(e)}


# Factory function para crear el handler con todas las dependencias
def create_message_handler() -> ImprovedMessageHandler:
    """
    Factory function que crea un ImprovedMessageHandler con todas sus dependencias.
    Implementa el patrón Factory y facilita la inyección de dependencias.
    """
    from infrastructure.persistence.sqlite_conversation_repository import (
        SQLiteConversationRepository,
        TopicDetectionService
    )
    
    # Crear repositorio
    conversation_repository = SQLiteConversationRepository()
    topic_detection_service = TopicDetectionService()
    
    # Crear casos de uso
    retrieve_context_use_case = RetrieveContextUseCase(
        conversation_repository,
        topic_detection_service
    )
    
    from application.use_cases.context_use_cases import SaveContextUseCase
    save_context_use_case = SaveContextUseCase(conversation_repository)
    
    add_message_use_case = AddMessageToContextUseCase(
        conversation_repository,
        retrieve_context_use_case,
        save_context_use_case
    )
    
    # Crear procesador de mensajes
    message_processor = MessageProcessorService()
    
    # Crear handler
    return ImprovedMessageHandler(
        add_message_use_case=add_message_use_case,
        retrieve_context_use_case=retrieve_context_use_case,
        message_processor=message_processor,
        ai_service=None  # Aquí inyectarías el servicio de IA real
    )