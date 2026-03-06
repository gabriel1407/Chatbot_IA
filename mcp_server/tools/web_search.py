"""
tools/web_search.py
Herramienta MCP: búsqueda web usando Gemini con Google Search Grounding.

Docs: https://ai.google.dev/gemini-api/docs/grounding
El modelo utiliza Google Search automáticamente para obtener información
actualizada y la integra en su respuesta.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_server.web_search")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Lee el modelo del entorno (mismo que usa la app Flask)
# gemini-2.5-flash-lite, gemini-1.5-flash, etc.
GEMINI_MODEL   = "gemini-2.5-flash-lite"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


async def _search(query: str) -> str:
    """Llama a la Gemini API con Google Search grounding."""
    if not GEMINI_API_KEY:
        return "Búsqueda web no disponible: GEMINI_API_KEY no configurada."

    payload = {
        "contents": [
            {"parts": [{"text": query}], "role": "user"}
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "maxOutputTokens": 800,
            "temperature": 0.1,
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
                timeout=20.0,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"[web_search] Error HTTP {exc.response.status_code}: {exc.response.text[:300]}")
            return f"Error en Gemini Web Search (HTTP {exc.response.status_code})."
        except Exception as exc:
            logger.error(f"[web_search] Error de conexión: {exc}")
            return f"Error al conectar con Gemini: {exc}"

    # Extraer el texto de la respuesta
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return "No se obtuvo respuesta de Gemini."

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
    except Exception as exc:
        logger.error(f"[web_search] Error procesando respuesta: {exc}")
        return "Error procesando la respuesta de Gemini."

    if not text:
        return f"No se encontraron resultados para: '{query}'"

    # Límite de seguridad para WhatsApp (4096 chars max)
    if len(text) > 3800:
        text = text[:3800] + "\n\n[resultado truncado]"

    return text


def register(mcp: FastMCP) -> None:
    """Registra la tool web_search en la instancia FastMCP."""

    @mcp.tool()
    async def web_search(query: str) -> str:
        """
        Busca información actualizada en internet usando Gemini + Google Search.

        Args:
            query: Query de búsqueda limpia y concisa.
        Returns:
            Respuesta fundamentada en resultados reales de Google Search.
        """
        logger.info(f"[web_search] query='{query[:80]}'")
        return await _search(query)
