"""
OpenAIEmbeddingService - Implementación concreta del servicio de embeddings usando OpenAI.
Cumple con la interfaz EmbeddingService y principios SOLID.
"""
from typing import List

from openai import OpenAI

from application.services.embedding_service import EmbeddingService
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
from core.exceptions.custom_exceptions import EmbeddingServiceException


class OpenAIEmbeddingService(EmbeddingService):
    """
    Implementación concreta de EmbeddingService usando OpenAI.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._logger = get_infrastructure_logger()
        self._model = model or settings.openai_embedding_model
        api_key = api_key or settings.openai_api_key
        try:
            self._client = OpenAI(api_key=api_key)
        except Exception as e:
            self._logger.error(f"Error inicializando cliente OpenAI Embeddings: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        try:
            if not text or not text.strip():
                return []
            resp = self._client.embeddings.create(
                model=self._model,
                input=text,
            )
            return resp.data[0].embedding  # type: ignore[return-value]
        except Exception as e:
            self._logger.error(f"Error generando embedding: {e}")
            raise EmbeddingServiceException(str(e))

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            if not texts:
                return []
            resp = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            return [item.embedding for item in resp.data]  # type: ignore[list-item]
        except Exception as e:
            self._logger.error(f"Error generando embeddings batch: {e}")
            raise EmbeddingServiceException(str(e))

    def get_embedding_dimension(self) -> int:
        # text-embedding-3-small: 1536, text-embedding-3-large: 3072
        if "large" in self._model:
            return 3072
        return 1536
