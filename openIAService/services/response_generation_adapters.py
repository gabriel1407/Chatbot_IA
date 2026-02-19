"""
Adapters de infraestructura para ResponseGenerationUseCase.
Mantiene detalles técnicos fuera de la capa application.
"""
from typing import Optional, List

import requests

from core.ai.factory import get_ai_provider
from core.config.settings import settings
from services.context_service_adapter import load_context, save_context
from services.mcp_service import extract_url_from_message, link_reader_agent, mcp_pipeline


class ContextPortAdapter:
    def load_context(self, user_id: str, context_id: str) -> List[dict]:
        return load_context(user_id, context_id)

    def save_context(self, user_id: str, context: List[dict], context_id: str) -> None:
        save_context(user_id, context, context_id)


class WebAssistPortAdapter:
    def extract_url(self, message: str) -> Optional[str]:
        return extract_url_from_message(message)

    def summarize_link(self, url: str, question: Optional[str] = None) -> str:
        return link_reader_agent(url, question)

    def run_web_pipeline(self, query: str) -> str:
        return mcp_pipeline(query)


class AIProviderFactoryAdapter:
    def get_provider(self):
        return get_ai_provider()


class RAGSearchPortAdapter:
    """Adapter de búsqueda RAG global — llama directamente al servicio interno."""

    def search(self, query: str, top_k: Optional[int] = None) -> Optional[List[dict]]:
        if not settings.rag_enabled:
            return None
        try:
            # Llamada directa al servicio Python en lugar de HTTP para evitar overhead
            # y problemas de autenticación en llamadas internas.
            from core.config.dependencies import DependencyContainer
            rag_service = DependencyContainer.get("RAGService")
            results = rag_service.retrieve(
                query_text=query,
                top_k=top_k or getattr(settings, "rag_chat_top_k", None) or settings.rag_top_k,
                min_similarity=settings.rag_global_min_similarity,
            )
            if not results:
                return None
            return [
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": float(score),
                }
                for chunk, score in results
            ]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[RAGSearchPortAdapter] Error buscando en RAG: {e}")
            return None
