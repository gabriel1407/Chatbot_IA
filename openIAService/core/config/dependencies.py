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
    
    # TODO: Aquí registraremos las implementaciones concretas
    # cuando las creemos en las siguientes fases
    
    # Ejemplo de cómo se registrarán:
    # from infrastructure.ai.openai_llm_adapter import OpenAILLMAdapter
    # from infrastructure.persistence.sqlite_conversation_repository import SQLiteConversationRepository
    # 
    # DependencyContainer.register("LLMService", OpenAILLMAdapter(settings))
    # DependencyContainer.register("ConversationRepository", SQLiteConversationRepository(settings))
    
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
