"""
Container de inyección de dependencias.
Centraliza la creación e inyección de dependencias siguiendo DIP.
"""
from typing import Optional
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger

logger = get_infrastructure_logger()


class DependencyContainer:
    """
    Container para inyección de dependencias.
    Implementa el patrón Service Locator simplificado.
    """
    
    _instances = {}
    
    @classmethod
    def register(cls, interface_name: str, implementation):
        """
        Registra una implementación para una interface.
        
        Args:
            interface_name: Nombre de la interface
            implementation: Instancia de la implementación
        """
        cls._instances[interface_name] = implementation
        logger.info(f"Dependencia registrada: {interface_name} -> {type(implementation).__name__}")
    
    @classmethod
    def get(cls, interface_name: str):
        """
        Obtiene una implementación registrada.
        
        Args:
            interface_name: Nombre de la interface
            
        Returns:
            Implementación registrada
            
        Raises:
            KeyError: Si la dependencia no está registrada
        """
        if interface_name not in cls._instances:
            raise KeyError(f"Dependencia no registrada: {interface_name}")
        return cls._instances[interface_name]
    
    @classmethod
    def clear(cls):
        """Limpia todas las dependencias registradas."""
        cls._instances.clear()
        logger.info("Dependencias limpiadas")


def initialize_dependencies():
    """
    Inicializa todas las dependencias de la aplicación.
    Esta función se llamará al inicio de la aplicación.
    """
    logger.info("Inicializando dependencias...")

    # Repositorio de conversaciones (SQLite/MySQL por configuración)
    from infrastructure.persistence.conversation_repository_factory import create_conversation_repository
    DependencyContainer.register("ConversationRepository", create_conversation_repository(settings.db_path))

    # Handler de mensajes (application/use-cases + adapters)
    try:
        from infrastructure.persistence.topic_detection_service import TopicDetectionService
        from application.use_cases.context_use_cases import (
            RetrieveContextUseCase,
            SaveContextUseCase,
            AddMessageToContextUseCase,
        )
        from application.use_cases.response_generation_use_case import ResponseGenerationUseCase
        from services.response_generation_adapters import (
            ContextPortAdapter,
            WebAssistPortAdapter,
            AIProviderFactoryAdapter,
            RAGSearchPortAdapter,
        )
        from services.improved_message_handler import (
            MessageProcessorService,
            ImprovedMessageHandler,
        )

        conversation_repository = DependencyContainer.get("ConversationRepository")
        topic_detection_service = TopicDetectionService()
        retrieve_context_use_case = RetrieveContextUseCase(conversation_repository, topic_detection_service)
        save_context_use_case = SaveContextUseCase(conversation_repository)
        add_message_use_case = AddMessageToContextUseCase(
            conversation_repository,
            retrieve_context_use_case,
            save_context_use_case,
        )

        response_generation_use_case = ResponseGenerationUseCase(
            context_port=ContextPortAdapter(),
            web_assist_port=WebAssistPortAdapter(),
            ai_provider_factory=AIProviderFactoryAdapter(),
            rag_search_port=RAGSearchPortAdapter(),
        )
        DependencyContainer.register("ResponseGenerationUseCase", response_generation_use_case)

        message_handler = ImprovedMessageHandler(
            add_message_use_case=add_message_use_case,
            retrieve_context_use_case=retrieve_context_use_case,
            message_processor=MessageProcessorService(),
            ai_service=None,
            response_generation_use_case=response_generation_use_case,
        )
        DependencyContainer.register("MessageHandler", message_handler)

        from services.channel_adapters import (
            UnifiedChannelService,
            ChannelType,
            WhatsAppAdapter,
            TelegramAdapter,
        )

        channel_adapters = {
            ChannelType.WHATSAPP: WhatsAppAdapter(),
            ChannelType.TELEGRAM: TelegramAdapter(),
        }
        DependencyContainer.register("ChannelAdapters", channel_adapters)

        unified_channel_service = UnifiedChannelService(
            message_handler=message_handler,
            adapters=channel_adapters,
        )
        DependencyContainer.register("UnifiedChannelService", unified_channel_service)
    except Exception as e:
        logger.warning(f"MessageHandler no inicializado desde container: {e}")

    # RAG-related deps solo si está habilitado
    if getattr(settings, "rag_enabled", True):
        try:
            # Servicio de embeddings (multi-proveedor: OpenAI, Gemini, Ollama)
            from infrastructure.embeddings.ai_provider_embedding_service import AIProviderEmbeddingService
            embedding_service = AIProviderEmbeddingService()
            DependencyContainer.register("EmbeddingService", embedding_service)

            # Vector Store (ChromaDB via HTTP)
            from infrastructure.vector_store.chroma_vector_store_repository import ChromaVectorStoreRepository
            chroma_host = getattr(settings, "chroma_host", None) or "chroma"
            chroma_port = getattr(settings, "chroma_port", None) or 8000
            DependencyContainer.register(
                "VectorStoreRepository", ChromaVectorStoreRepository(host=chroma_host, port=chroma_port, embedding_service=embedding_service)
            )

            # RAG Service
            from application.services.rag_service import RAGService
            rag_service = RAGService(
                embedding_service=DependencyContainer.get("EmbeddingService"),
                vector_store=DependencyContainer.get("VectorStoreRepository"),
            )
            DependencyContainer.register("RAGService", rag_service)
        except Exception as e:
            # Si Chroma u otra dependencia falla, deshabilitamos RAG de forma segura
            logger.warning(f"RAG deshabilitado por error de inicialización: {e}")
            try:
                setattr(settings, "rag_enabled", False)
            except Exception:
                pass

    logger.info("Dependencias inicializadas correctamente")


# Funciones helper para obtener dependencias comunes
def get_llm_service():
    """Obtiene el servicio de LLM."""
    return DependencyContainer.get("LLMService")


def get_embedding_service():
    """Obtiene el servicio de embeddings."""
    return DependencyContainer.get("EmbeddingService")


def get_conversation_repository():
    """Obtiene el repositorio de conversaciones."""
    return DependencyContainer.get("ConversationRepository")


def get_document_repository():
    """Obtiene el repositorio de documentos."""
    return DependencyContainer.get("DocumentRepository")


def get_vector_store_repository():
    """Obtiene el repositorio de vector store."""
    return DependencyContainer.get("VectorStoreRepository")


def get_message_handler():
    """Obtiene el handler principal de mensajes."""
    return DependencyContainer.get("MessageHandler")


def get_unified_channel_service_dep():
    """Obtiene el servicio unificado de canales."""
    return DependencyContainer.get("UnifiedChannelService")
