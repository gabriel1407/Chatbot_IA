"""
Excepciones personalizadas del dominio.
Facilita el manejo de errores específicos del negocio.
"""


class ChatbotBaseException(Exception):
    """Excepción base para todas las excepciones del chatbot."""
    
    def __init__(self, message: str, code: str = "CHATBOT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# Excepciones de Dominio
class DomainException(ChatbotBaseException):
    """Excepción base para errores de dominio."""
    pass


class InvalidMessageException(DomainException):
    """Excepción cuando un mensaje es inválido."""
    
    def __init__(self, message: str = "Mensaje inválido"):
        super().__init__(message, "INVALID_MESSAGE")


class InvalidConversationException(DomainException):
    """Excepción cuando una conversación es inválida."""
    
    def __init__(self, message: str = "Conversación inválida"):
        super().__init__(message, "INVALID_CONVERSATION")


class InvalidDocumentException(DomainException):
    """Excepción cuando un documento es inválido."""
    
    def __init__(self, message: str = "Documento inválido"):
        super().__init__(message, "INVALID_DOCUMENT")


# Excepciones de Repositorio
class RepositoryException(ChatbotBaseException):
    """Excepción base para errores de repositorio."""
    pass


class EntityNotFoundException(RepositoryException):
    """Excepción cuando no se encuentra una entidad."""
    
    def __init__(self, entity_type: str, entity_id: str):
        message = f"{entity_type} con ID '{entity_id}' no encontrado"
        super().__init__(message, "ENTITY_NOT_FOUND")


class PersistenceException(RepositoryException):
    """Excepción cuando falla la persistencia."""
    
    def __init__(self, message: str = "Error al persistir datos"):
        super().__init__(message, "PERSISTENCE_ERROR")


# Excepciones de Servicios
class ServiceException(ChatbotBaseException):
    """Excepción base para errores de servicios."""
    pass


class LLMServiceException(ServiceException):
    """Excepción cuando falla el servicio de LLM."""
    
    def __init__(self, message: str = "Error en servicio LLM"):
        super().__init__(message, "LLM_SERVICE_ERROR")


class EmbeddingServiceException(ServiceException):
    """Excepción cuando falla el servicio de embeddings."""
    
    def __init__(self, message: str = "Error en servicio de embeddings"):
        super().__init__(message, "EMBEDDING_SERVICE_ERROR")


class MessagingServiceException(ServiceException):
    """Excepción cuando falla el servicio de mensajería."""
    
    def __init__(self, message: str = "Error en servicio de mensajería"):
        super().__init__(message, "MESSAGING_SERVICE_ERROR")


class FileProcessingException(ServiceException):
    """Excepción cuando falla el procesamiento de archivos."""
    
    def __init__(self, message: str = "Error al procesar archivo"):
        super().__init__(message, "FILE_PROCESSING_ERROR")


# Excepciones de RAG
class RAGException(ChatbotBaseException):
    """Excepción base para errores de RAG."""
    pass


class VectorStoreException(RAGException):
    """Excepción cuando falla el vector store."""
    
    def __init__(self, message: str = "Error en vector store"):
        super().__init__(message, "VECTOR_STORE_ERROR")


class SearchException(RAGException):
    """Excepción cuando falla la búsqueda semántica."""
    
    def __init__(self, message: str = "Error en búsqueda semántica"):
        super().__init__(message, "SEARCH_ERROR")


# Excepciones de Contexto
class ContextException(ChatbotBaseException):
    """Excepción base para errores de contexto."""
    pass


class ContextWindowFullException(ContextException):
    """Excepción cuando la ventana de contexto está llena."""
    
    def __init__(self, message: str = "Ventana de contexto llena"):
        super().__init__(message, "CONTEXT_WINDOW_FULL")


class InvalidContextException(ContextException):
    """Excepción cuando el contexto es inválido."""
    
    def __init__(self, message: str = "Contexto inválido"):
        super().__init__(message, "INVALID_CONTEXT")
