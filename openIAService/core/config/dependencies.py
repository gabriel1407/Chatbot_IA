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

    # Repositorio de conversaciones (SQLite)
    from infrastructure.persistence.sqlite_conversation_repository import SQLiteConversationRepository
    DependencyContainer.register("ConversationRepository", SQLiteConversationRepository(settings.db_path))

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


def get_telegram_service():
    """Obtiene el servicio de Telegram."""
    return DependencyContainer.get("TelegramService")


def get_whatsapp_service():
    """Obtiene el servicio de WhatsApp."""
    return DependencyContainer.get("WhatsAppService")
