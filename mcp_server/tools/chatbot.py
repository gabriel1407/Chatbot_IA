"""
tools/chatbot.py
Herramientas MCP para interactuar con la app Flask del Chatbot IA:
  - chatbot_health    : Verifica el estado del servicio.
  - send_chat_message : Envía un mensaje y retorna la respuesta del chatbot.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_server.chatbot")

APP_BASE_URL = os.getenv("APP_URL", "http://app:8082")


def register(mcp: FastMCP) -> None:
    """Registra las tools de chatbot en la instancia FastMCP."""

    @mcp.tool()
    async def chatbot_health() -> str:
        """
        Verifica el estado de salud del chatbot principal (app Flask).

        Returns:
            'ok' si el servicio responde, mensaje de error en caso contrario.
        """
        logger.info("[chatbot_health] verificando app principal...")

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{APP_BASE_URL}/health", timeout=5.0)
                if r.status_code == 200:
                    return f"App principal OK (status {r.status_code})"
                return f"App principal respondió con status {r.status_code}"
            except Exception as exc:
                return f"App principal no disponible: {exc}"

    @mcp.tool()
    async def send_chat_message(message: str, tenant_id: str = "default") -> str:
        """
        Envía un mensaje al chatbot y retorna la respuesta generada.

        Args:
            message:   El mensaje a procesar.
            tenant_id: Identificador del tenant (cliente). Por defecto 'default'.
        Returns:
            Respuesta del chatbot o mensaje de error.
        """
        logger.info(
            f"[send_chat_message] tenant={tenant_id} "
            f"message='{message[:60]}{'...' if len(message) > 60 else ''}'"
        )

        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    f"{APP_BASE_URL}/api/chat",
                    json={"message": message, "tenant_id": tenant_id},
                    timeout=30.0,
                )
                r.raise_for_status()
                data = r.json()
                return data.get("response") or data.get("message") or str(data)
            except httpx.HTTPStatusError as exc:
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error al comunicarse con el chatbot: {exc}"
