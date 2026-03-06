"""
middleware/auth.py
Middleware de autenticación JWT para el MCP Server.

Gestiona automáticamente:
  1. Login inicial con usuario/contraseña desde variables de entorno.
  2. Caché del access_token en memoria.
  3. Refresco automático del token cuando está próximo a vencer,
     usando el refresh_token sin volver a pedir contraseña.
  4. Re-login completo si el refresh_token también expira.

Variables de entorno requeridas:
  APP_URL       — URL base de la app Flask (ej: http://app:8082)
  APP_USERNAME  — Usuario admin del chatbot (ej: admin)
  APP_PASSWORD  — Contraseña del usuario

Uso:
    from middleware.auth import get_auth_headers

    headers = await get_auth_headers()
    # {"Authorization": "Bearer eyJ..."}
"""

import os
import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger("mcp_server.auth")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
APP_BASE_URL  = os.getenv("APP_URL", "http://app:8082")
APP_USERNAME  = os.getenv("APP_USERNAME", "")
APP_PASSWORD  = os.getenv("APP_PASSWORD", "")

_LOGIN_URL   = f"{APP_BASE_URL}/api/auth/login"
_REFRESH_URL = f"{APP_BASE_URL}/api/auth/refresh"

# Margen de seguridad: refrescar el token N segundos ANTES de que venza
_REFRESH_MARGIN_SECONDS = 60

# ---------------------------------------------------------------------------
# Estado interno (singleton en memoria)
# ---------------------------------------------------------------------------
_access_token:  Optional[str] = None
_refresh_token: Optional[str] = None
_token_expires_at: float = 0.0       # timestamp Unix cuando expira el access_token
_lock = asyncio.Lock()


def _is_expired() -> bool:
    """True si el access_token está vencido o a punto de vencer."""
    return time.time() >= (_token_expires_at - _REFRESH_MARGIN_SECONDS)


# ---------------------------------------------------------------------------
# Operaciones de autenticación
# ---------------------------------------------------------------------------

async def _do_login() -> bool:
    """
    Hace login con usuario/contraseña y almacena los tokens en memoria.
    Retorna True si el login fue exitoso.
    """
    global _access_token, _refresh_token, _token_expires_at

    if not APP_USERNAME or not APP_PASSWORD:
        logger.error(
            "[Auth] APP_USERNAME y APP_PASSWORD no están configurados. "
            "Configúralos en las variables de entorno del servicio mcp_server."
        )
        return False

    logger.info(f"[Auth] Iniciando sesión como '{APP_USERNAME}'...")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                _LOGIN_URL,
                json={"username": APP_USERNAME, "password": APP_PASSWORD},
                timeout=10.0,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[Auth] Login fallido (HTTP {exc.response.status_code}): {exc.response.text[:200]}"
            )
            return False
        except Exception as exc:
            logger.error(f"[Auth] Error de conexión en login: {exc}")
            return False

    _access_token  = data.get("access_token", "")
    _refresh_token = data.get("refresh_token", "")
    expires_in     = data.get("expires_in", 1800)        # segundos

    _token_expires_at = time.time() + expires_in
    logger.info(f"[Auth] Login exitoso. Token válido por {expires_in}s.")
    return True


async def _do_refresh() -> bool:
    """
    Refresca el access_token usando el refresh_token almacenado.
    Si falla, intenta hacer login completo.
    Retorna True si el refresco fue exitoso.
    """
    global _access_token, _token_expires_at

    if not _refresh_token:
        logger.warning("[Auth] No hay refresh_token disponible. Haciendo login completo...")
        return await _do_login()

    logger.info("[Auth] Refrescando access_token...")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                _REFRESH_URL,
                json={"refresh_token": _refresh_token},
                timeout=10.0,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"[Auth] Refresco fallido (HTTP {exc.response.status_code}). "
                "Intentando login completo..."
            )
            return await _do_login()
        except Exception as exc:
            logger.error(f"[Auth] Error de conexión refrescando token: {exc}")
            return False

    _access_token  = data.get("access_token", "")
    expires_in     = data.get("expires_in", 1800)
    _token_expires_at = time.time() + expires_in
    logger.info(f"[Auth] Token refrescado. Válido por {expires_in}s.")
    return True


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

async def get_auth_headers() -> dict:
    """
    Retorna los headers de autenticación con un JWT válido.

    Gestiona automáticamente:
      - Login inicial si no hay token.
      - Refresco si el token está próximo a vencer.
      - Re-login si el refresco falla.

    Returns:
        {"Authorization": "Bearer eyJ..."}
        Si no se puede autenticar, retorna {} y el error se loguea.
    """
    global _access_token

    async with _lock:
        need_auth = not _access_token or _is_expired()

        if need_auth:
            if _refresh_token and not _is_expired():
                # Token todavía válido (no debería llegar aquí, pero por seguridad)
                pass
            elif _refresh_token:
                # Access token vencido, intentar refresco primero
                await _do_refresh()
            else:
                # Primera vez o sin refresh_token: login completo
                await _do_login()

        if not _access_token:
            logger.error("[Auth] No se pudo obtener un token JWT válido.")
            return {}

        return {"Authorization": f"Bearer {_access_token}"}


def get_auth_headers_sync() -> dict:
    """
    Versión síncrona de get_auth_headers() para uso fuera de contexto async.
    Útil en inicialización o en código no-async.
    """
    try:
        return asyncio.run(get_auth_headers())
    except RuntimeError:
        # Ya hay un event loop corriendo (contexto async activo)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(get_auth_headers())
