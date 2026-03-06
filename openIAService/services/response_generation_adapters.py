"""
Adapters de infraestructura para ResponseGenerationUseCase.
Mantiene detalles técnicos fuera de la capa application.
Soporta aislamiento multi-tenant en RAG.
"""
from typing import Optional, List

from core.ai.factory import get_ai_provider
from core.config.settings import settings
from core.logging.logger import get_app_logger
from services.context_service_adapter import load_context, save_context

_rag_logger = get_app_logger()

# Default tenant ID — configurable via DEFAULT_TENANT_ID en .env
def _default_tenant() -> str:
    return settings.default_tenant_id


class ContextPortAdapter:
    def load_context(self, user_id: str, context_id: str) -> List[dict]:
        return load_context(user_id, context_id)

    def save_context(self, user_id: str, context: List[dict], context_id: str) -> None:
        save_context(user_id, context, context_id)


class WebAssistPortAdapter:
    """
    Adapter de asistencia web.
    Usa el cliente MCP oficial para ejecutar herramientas en el MCP Server.
    Si el servidor MCP no está disponible, hace fallback al pipeline legacy.
    """

    def extract_url(self, message: str) -> Optional[str]:
        """Extrae la primera URL de un mensaje."""
        import re
        match = re.search(r'(https?://\S+)', message)
        return match.group(1) if match else None

    def summarize_link(self, url: str, question: Optional[str] = None) -> str:
        """
        Lee y resume el contenido de una URL.
        Usa la tool 'read_webpage' del MCP Server.
        """
        try:
            from core.mcp.mcp_client import get_mcp_client
            client = get_mcp_client()
            args = {"url": url}
            if question:
                args["question"] = question
            result = client.call_tool("read_webpage", args)
            _rag_logger.info(f"[WebAssist][MCP] read_webpage OK para {url}")
            return result
        except Exception as exc:
            _rag_logger.warning(f"[WebAssist][MCP] Fallback a legacy para {url}: {exc}")
            # Fallback al servicio legacy
            from services.mcp_service import link_reader_agent
            return link_reader_agent(url, question)

    def run_web_pipeline(self, query: str) -> str:
        """
        Ejecuta búsqueda web y resumen IA.
        Usa la tool 'web_search' del MCP Server.
        """
        try:
            from core.mcp.mcp_client import get_mcp_client
            client = get_mcp_client()
            result = client.call_tool("web_search", {"query": query})
            _rag_logger.info(f"[WebAssist][MCP] web_search OK para '{query[:50]}'")
            return result
        except Exception as exc:
            _rag_logger.warning(f"[WebAssist][MCP] Fallback a legacy para query '{query[:50]}': {exc}")
            # Fallback al pipeline legacy
            from services.mcp_service import mcp_pipeline
            return mcp_pipeline(query)




class AIProviderFactoryAdapter:
    def get_provider(self):
        return get_ai_provider()


class RAGSearchPortAdapter:
    """
    Adapter de búsqueda RAG con soporte multi-tenant.
    Busca en la colección del tenant especificado.
    """

    def search(
        self,
        query: str,
        tenant_id: str = None,
        top_k: Optional[int] = None,
    ) -> Optional[List[dict]]:
        """
        Busca en el RAG del tenant especificado.
        """
        if not settings.rag_enabled:
            return None

        effective_tenant_id = tenant_id or _default_tenant()

        try:
            _rag_logger.info(
                f"[RAG] Buscando en tenant='{effective_tenant_id}' query='{query[:60]}'"
            )
            from core.config.dependencies import DependencyContainer
            rag_service = DependencyContainer.get("RAGService")

            # Para búsquedas de canal usamos el umbral global (más permisivo: 0.3)
            # en vez del umbral estricto de ingestión (0.7)
            min_sim = getattr(settings, "rag_global_min_similarity", 0.3)

            results = rag_service.retrieve(
                query_text=query,
                tenant_id=effective_tenant_id,
                top_k=top_k or getattr(settings, "rag_chat_top_k", None) or settings.rag_top_k,
                min_similarity=min_sim,
            )

            if not results:
                _rag_logger.info(
                    f"[RAG] Sin resultados para tenant='{effective_tenant_id}' (min_similarity={min_sim})"
                )
                return None

            _rag_logger.info(f"[RAG] {len(results)} chunks encontrados en tenant='{effective_tenant_id}'")

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
            _rag_logger.warning(
                f"[RAGSearchPortAdapter] Error buscando en RAG para tenant '{effective_tenant_id}': {e}"
            )
            return None

    def search_with_fallback(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Optional[List[dict]]:
        """Busca en RAG con fallback a tenant configurado por defecto."""
        effective_tenant_id = tenant_id or _default_tenant()
        return self.search(query=query, tenant_id=effective_tenant_id, top_k=top_k)