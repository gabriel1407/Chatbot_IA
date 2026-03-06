"""
tools/context.py
Herramientas MCP para gestión de contextos de conversación:
  - get_context_stats   : Estadísticas de conversaciones en base de datos.
  - get_context_status  : Estado del servicio de limpieza de contextos.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_server.context")

APP_BASE_URL = os.getenv("APP_URL", "http://app:8082")


def register(mcp: FastMCP) -> None:
    """Registra las tools de contexto en la instancia FastMCP."""

    @mcp.tool()
    async def get_context_stats() -> str:
        """
        Obtiene estadísticas de las conversaciones almacenadas en la base de datos.

        Returns:
            Estadísticas de contextos: total de conversaciones, mensajes, etc.
        """
        logger.info("[get_context_stats] obteniendo estadísticas de contextos...")

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/context/stats",
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error obteniendo estadísticas de contexto: {exc}"

        stats = data.get("data", {})
        if not stats:
            return "No se obtuvieron estadísticas del sistema de contextos."

        lines = ["📊 Estadísticas de Contextos (Conversaciones):\n"]
        for key, value in stats.items():
            label = key.replace("_", " ").capitalize()
            lines.append(f"  • {label}: {value}")

        return "\n".join(lines)

    @mcp.tool()
    async def get_context_status() -> str:
        """
        Obtiene el estado del sistema de limpieza de contextos y la salud del servicio.

        Returns:
            Estado del servicio de contextos y configuración de limpieza automática.
        """
        logger.info("[get_context_status] verificando estado del sistema de contextos...")

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/context/status",
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error obteniendo estado del sistema de contextos: {exc}"

        status = data.get("data", {})
        is_running = status.get("is_running", False)
        threshold = status.get("threshold_hours", "?")
        interval = status.get("cleanup_interval_hours", "?")

        return (
            f"🔄 Estado del Sistema de Contextos:\n"
            f"  • Limpieza automática: {'✅ activa' if is_running else '⚠️ inactiva'}\n"
            f"  • Umbral de expiración: {threshold}h\n"
            f"  • Intervalo de limpieza: {interval}h\n"
            f"  • Estrategia: {status.get('strategy', 'N/A')}"
        )
