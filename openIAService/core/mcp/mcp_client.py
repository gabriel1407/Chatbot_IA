"""
core/mcp/mcp_client.py

Cliente MCP oficial para la app Flask del Chatbot IA.
Se conecta al MCP Server vía SSE (HTTP) y ejecuta herramientas
mediante session.call_tool() según la especificación oficial.

Referencia: https://modelcontextprotocol.io/docs/develop/build-client
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession
from mcp.client.sse import sse_client

from core.config.settings import settings

logger = logging.getLogger("mcp_client")


class MCPClient:
    """
    Cliente MCP que se conecta al servidor via SSE.

    Uso básico:
        client = MCPClient()
        result = client.call_tool("web_search", {"query": "..."})
    """

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or settings.mcp_server_url
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None

    @property
    def _sse_url(self) -> str:
        """URL completa del endpoint SSE: base_url/sse (requerido por sse_client)."""
        base = self.server_url.rstrip("/")
        return base if base.endswith("/sse") else f"{base}/sse"

    # ------------------------------------------------------------------
    # API pública SÍNCRONA (compatible con Flask / código síncrono)
    # ------------------------------------------------------------------

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Ejecuta una herramienta del servidor MCP y retorna el resultado como string.
        Crea una conexión nueva por llamada (sin estado persistente entre requests).
        """
        try:
            return asyncio.run(self._call_tool_async(tool_name, arguments))
        except Exception as exc:
            logger.error(f"[MCPClient] Error llamando tool '{tool_name}': {exc}")
            return f"Error ejecutando herramienta MCP '{tool_name}': {exc}"

    def list_tools(self) -> list[str]:
        """Retorna la lista de nombres de tools disponibles en el servidor."""
        try:
            return asyncio.run(self._list_tools_async())
        except Exception as exc:
            logger.error(f"[MCPClient] Error listando tools: {exc}")
            return []

    # ------------------------------------------------------------------
    # Implementación asíncrona interna
    # ------------------------------------------------------------------

    async def _call_tool_async(self, tool_name: str, arguments: dict) -> str:
        """Conecta al servidor, ejecuta la tool y retorna el contenido."""
        async with AsyncExitStack() as stack:
            transport = await stack.enter_async_context(
                sse_client(self._sse_url)
            )
            session = await stack.enter_async_context(
                ClientSession(*transport)
            )
            await session.initialize()

            logger.info(f"[MCPClient] Llamando tool='{tool_name}' args={list(arguments.keys())}")
            result = await session.call_tool(tool_name, arguments)

            # El resultado es una lista de TextContent/ImageContent etc.
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))

            return "\n".join(parts) if parts else "(sin resultado)"

    async def _list_tools_async(self) -> list[str]:
        """Conecta al servidor y lista las tools disponibles."""
        async with AsyncExitStack() as stack:
            transport = await stack.enter_async_context(
                sse_client(self._sse_url)
            )
            session = await stack.enter_async_context(
                ClientSession(*transport)
            )
            await session.initialize()

            response = await session.list_tools()
            return [tool.name for tool in response.tools]


# ---------------------------------------------------------------------------
# Instancia singleton lazy (se crea al primer uso)
# ---------------------------------------------------------------------------
_client_instance: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """
    Retorna la instancia singleton del cliente MCP.
    La instancia se crea la primera vez que se llama esta función.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = MCPClient()
        logger.info(f"[MCPClient] Inicializado con servidor={_client_instance.server_url}")
    return _client_instance
