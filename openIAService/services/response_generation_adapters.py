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
    """Adapter de búsqueda RAG global vía endpoint HTTP."""

    def search(self, query: str, top_k: Optional[int] = None) -> Optional[List[dict]]:
        if not settings.rag_enabled:
            return None

        url = "https://optimus.pegasoconsulting.net/service_ia/api/rag/search"
        params = {
            "query": query,
            "top_k": top_k or settings.rag_chat_top_k or settings.rag_top_k,
            "min_similarity": settings.rag_global_min_similarity,
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("ok"):
            results = data.get("results", [])
            return results or None

        return None
