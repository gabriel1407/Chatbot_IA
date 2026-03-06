"""
tools/tenant.py
Herramientas MCP para gestión de tenants:
  - list_tenants  : Lista todos los tenants registrados.
  - get_tenant    : Obtiene la configuración de un tenant específico.

Usan el middleware de autenticación (middleware/auth.py) que genera
y refresca automáticamente el JWT con APP_USERNAME + APP_PASSWORD.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP
from middleware.auth import get_auth_headers

logger = logging.getLogger("mcp_server.tenant")

APP_BASE_URL = os.getenv("APP_URL", "http://app:8082")


def register(mcp: FastMCP) -> None:
    """Registra las tools de tenant en la instancia FastMCP."""

    @mcp.tool()
    async def list_tenants() -> str:
        """
        Lista todos los tenants registrados en el sistema.

        Returns:
            Lista con tenant_id, nombre del bot y estado activo de cada tenant.
        """
        logger.info("[list_tenants] listando todos los tenants...")

        headers = await get_auth_headers()
        if not headers:
            return "❌ No se pudo autenticar. Verifica APP_USERNAME y APP_PASSWORD en las variables de entorno."

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/tenant/",
                    headers=headers,
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    return "❌ No autorizado: el token JWT no es válido o ha expirado."
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error listando tenants: {exc}"

        tenants = data.get("tenants", [])
        if not tenants:
            return "No hay tenants registrados."

        lines = [f"Se encontraron {len(tenants)} tenant(s):\n"]
        for t in tenants:
            status = "✅ activo" if t.get("is_active", True) else "⛔ inactivo"
            lines.append(
                f"  • [{t.get('tenant_id')}] {t.get('bot_name', 'Sin nombre')} — {status}"
                f" | AI: {t.get('ai_provider', 'global')} | RAG: {'✅' if t.get('rag_enabled') else '❌'}"
            )

        return "\n".join(lines)

    @mcp.tool()
    async def get_tenant(tenant_id: str) -> str:
        """
        Obtiene la configuración completa de un tenant específico.

        Args:
            tenant_id: ID del tenant a consultar.
        Returns:
            Configuración del tenant: nombre, proveedor AI, RAG, idioma, etc.
        """
        logger.info(f"[get_tenant] tenant_id={tenant_id}")

        headers = await get_auth_headers()
        if not headers:
            return "❌ No se pudo autenticar. Verifica APP_USERNAME y APP_PASSWORD en las variables de entorno."

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{APP_BASE_URL}/api/tenant/{tenant_id}",
                    headers=headers,
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    return "❌ No autorizado: el token JWT no es válido o ha expirado."
                if exc.response.status_code == 404:
                    return f"❌ Tenant '{tenant_id}' no encontrado."
                return f"Error HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:
                return f"Error obteniendo tenant: {exc}"

        t = data.get("tenant", {})
        return (
            f"📋 Configuración de tenant '{tenant_id}':\n"
            f"  • Nombre bot:   {t.get('bot_name', 'N/A')}\n"
            f"  • Persona:      {t.get('bot_persona', 'N/A')}\n"
            f"  • Idioma:       {t.get('language', 'es')}\n"
            f"  • AI provider:  {t.get('ai_provider', 'global')}\n"
            f"  • AI model:     {t.get('ai_model', 'global')}\n"
            f"  • RAG enabled:  {'✅' if t.get('rag_enabled') else '❌'}\n"
            f"  • RAG top_k:    {t.get('rag_top_k', 5)}\n"
            f"  • Web search:   {'✅' if t.get('web_search_enabled') else '❌'}\n"
            f"  • Estado:       {'✅ activo' if t.get('is_active', True) else '⛔ inactivo'}"
        )
