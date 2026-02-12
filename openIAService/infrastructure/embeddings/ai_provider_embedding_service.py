"""
AIProviderEmbeddingService - Implementación multi-proveedor del servicio de embeddings.
Cumple con la interfaz EmbeddingService y principios SOLID (Dependency Inversion).
Soporta OpenAI, Gemini, Ollama según la configuración de ai_provider.
"""
from typing import List

from application.services.embedding_service import EmbeddingService
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
from core.exceptions.custom_exceptions import EmbeddingServiceException

from core.ai.factory import get_ai_provider


class AIProviderEmbeddingService(EmbeddingService):
    """
    Implementación de EmbeddingService que delega a un `AIProvider`.
    Esto permite intercambiar proveedores (OpenAI, Gemini, Ollama) sin cambiar
    la lógica de la aplicación, respetando el principio de inversión de dependencias.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._logger = get_infrastructure_logger()
        self._provider = get_ai_provider()
        
        # Determinar modelo según el proveedor configurado
        provider_name = (settings.ai_provider or "openai").lower()
        if model:
            self._model = model
        elif provider_name == "openai":
            self._model = settings.openai_embedding_model
        elif provider_name == "ollama":
            # Ollama needs specific embedding models (embeddinggemma, qwen3-embedding, all-minilm)
            self._model = getattr(settings, "ollama_embedding_model", "embeddinggemma")
        elif provider_name == "gemini":
            # Gemini uses gemini-embedding-001 for embeddings
            self._model = getattr(settings, "gemini_embedding_model", "gemini-embedding-001")
        else:
            self._model = settings.openai_embedding_model  # fallback
        
        self._logger.info(f"AIProviderEmbeddingService initialized: provider={provider_name}, embedding_model={self._model}")

    def generate_embedding(self, text: str) -> List[float]:
        try:
            if not text or not text.strip():
                return []
            embeddings = self._provider.embed_texts([text])
            return embeddings[0] if embeddings else []
        except NotImplementedError as e:
            self._logger.error(f"Embeddings not supported by provider: {e}")
            raise EmbeddingServiceException(str(e))
        except Exception as e:
            self._logger.error(f"Error generando embedding: {e}")
            raise EmbeddingServiceException(str(e))

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            if not texts:
                return []
            return self._provider.embed_texts(texts)
        except NotImplementedError as e:
            self._logger.error(f"Embeddings not supported by provider: {e}")
            raise EmbeddingServiceException(str(e))
        except Exception as e:
            self._logger.error(f"Error generando embeddings batch: {e}")
            raise EmbeddingServiceException(str(e))

    def get_embedding_dimension(self) -> int:
        """
        Retorna la dimensión del embedding según el proveedor y modelo configurado.
        OpenAI: 1536 (small), 3072 (large)
        Ollama: Depende del modelo (típicamente 768-4096)
        Gemini: Depende del modelo
        """
        provider_name = (settings.ai_provider or "openai").lower()
        
        if provider_name == "openai":
            if "large" in (self._model or ""):
                return 3072
            return 1536
        elif provider_name == "ollama":
            # Ollama varía según modelo, usar dimensión común
            return 768  # Valor típico para modelos como llama2
        elif provider_name == "gemini":
            return 768  # Gemini embeddings típicamente 768
        
        return 1536  # fallback
