"""
tools/rag.py
Herramientas MCP para Retrieval-Augmented Generation (RAG):
  - rag_search : Busca documentos relevantes en ChromaDB por tenant.
  - rag_stats  : Obtiene estadísticas de documentos indexados por tenant.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_server.rag")

APP_BASE_URL = os.getenv("APP_URL", "http://app:8082")


def register(mcp: FastMCP) -> None:
    """Registra las tools de RAG en la instancia FastMCP."""

    @mcp.tool()
    async def rag_search(
        query: str,
        tenant_id: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> str:
        """
        Busca documentos relevantes en la base de conocimiento del tenant (ChromaDB).

        Args:
            query:          Texto o pregunta a buscar.
            tenant_id:      ID del tenant cuya colección se va a buscar.
            top_k:          Número máximo de resultados (default: 5).
            min_similarity: Similitud mínima entre 0 y 1 (default: 0.3).
        Returns:
            Fragmentos de documentos relevantes con sus metadatos y score.
        """
        logger.info(f"[rag_search] tenant={tenant_id} query='{query[:60]}' top_k={top_k}")

        params = {
            "query": query,
            "tenant_id": tenant_id,
            "top_k": top_k,
            "min_similarity": min_similarity,
        }

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/rag/search",
                    params=params,
                    timeout=15.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error buscando en RAG: {exc}"

        results = data.get("results", [])
        if not results:
            return f"No se encontraron documentos relevantes para '{query}' en tenant '{tenant_id}'."

        parts = []
        for i, chunk in enumerate(results, 1):
            score = chunk.get("similarity", 0)
            content = chunk.get("content", "")
            doc_id = chunk.get("document_id", "?")
            meta = chunk.get("metadata", {})
            title = meta.get("title", doc_id)
            parts.append(
                f"[{i}] 📄 {title} (score: {score:.2f})\n{content}"
            )

        return f"Se encontraron {len(results)} fragmentos relevantes:\n\n" + "\n\n---\n\n".join(parts)

    @mcp.tool()
    async def rag_stats(tenant_id: str) -> str:
        """
        Obtiene estadísticas de los documentos indexados en el RAG del tenant.

        Args:
            tenant_id: ID del tenant a consultar.
        Returns:
            Número total de chunks indexados para ese tenant.
        """
        logger.info(f"[rag_stats] tenant={tenant_id}")

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/rag/stats",
                    params={"tenant_id": tenant_id},
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error obteniendo estadísticas RAG: {exc}"

        total = data.get("total_chunks", 0)
        return (
            f"📊 RAG Stats — Tenant: '{tenant_id}'\n"
            f"  • Chunks indexados: {total}\n"
            f"  • Estado: {'✅ con datos' if total > 0 else '⚠️ vacío, sin documentos indexados'}"
        )
