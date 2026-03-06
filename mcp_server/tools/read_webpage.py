"""
tools/read_webpage.py
Herramienta MCP: extrae el texto limpio de una URL.
"""

import re
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_server.read_webpage")

MAX_CHARS = 4000


async def _extract_text(url: str) -> str:
    """Descarga una URL y extrae el texto visible (sin tags HTML)."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(url, timeout=10.0)
            r.raise_for_status()
            raw_html = r.text
        except Exception as exc:
            logger.error(f"[read_webpage] Error descargando {url}: {exc}")
            return f"No se pudo descargar la página: {exc}"

    # Elimina bloques script/style y luego todas las etiquetas HTML
    text = re.sub(
        r"<(script|style|noscript)[^>]*>.*?</\1>",
        "",
        raw_html,
        flags=re.S | re.I,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:MAX_CHARS]


def register(mcp: FastMCP) -> None:
    """Registra la tool read_webpage en la instancia FastMCP."""

    @mcp.tool()
    async def read_webpage(url: str, question: str = "") -> str:
        """
        Extrae el contenido de texto de una URL.

        Args:
            url:      URL de la página a leer.
            question: (opcional) Pregunta específica sobre el contenido.
        Returns:
            El texto extraído de la página (máx. 4000 caracteres).
        """
        logger.info(f"[read_webpage] url='{url}' question='{question}'")

        if not re.match(r"https?://", url):
            return f"URL inválida: {url}"

        text = await _extract_text(url)

        if question:
            return (
                f"Contenido de {url} (primeros {MAX_CHARS} chars):\n\n{text}"
                f"\n\nPregunta: {question}"
            )
        return f"Contenido de {url}:\n\n{text}"
