"""
middleware/auth.py
Middleware de autenticación JWT para el MCP Server.

Genera un "service token" directamente usando el mismo JWT_SECRET_KEY
que la app Flask usa para verificar tokens.
NO requiere usuario/contraseña ni llamadas HTTP.

Variables de entorno:
  JWT_SECRET_KEY  — Mismo secreto que usa la app Flask (REQUERIDO)
  JWT_ALGORITHM   — Algoritmo de firma (default: HS256)
  JWT_TTL_SECONDS — Duración del token en segundos (default: 3600)

Uso:
    from middleware.auth import get_auth_headers

    headers = await get_auth_headers()
    # {"Authorization": "Bearer eyJ..."}
"""

import os
import logging
import time
import datetime
from typing import Optional

import jwt  # PyJWT

logger = logging.getLogger("mcp_server.auth")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_JWT_SECRET    = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "")
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_TTL       = int(os.getenv("JWT_TTL_SECONDS", "3600"))   # 1 hora por defecto

# Identidad del servicio MCP en el payload JWT
_SERVICE_SUB  = "mcp_service"
_SERVICE_ROLE = "admin"

# Margen de seguridad: renovar el token N segundos ANTES de que venza
_REFRESH_MARGIN = 60

# ---------------------------------------------------------------------------
# Estado interno (singleton)
# ---------------------------------------------------------------------------
_access_token:     Optional[str] = None
_token_expires_at: float = 0.0


def _is_expired() -> bool:
    """True si el token está vencido o a punto de vencer."""
    return time.time() >= (_token_expires_at - _REFRESH_MARGIN)


def _generate_token() -> str:
    """
    Genera un JWT de servicio firmado con JWT_SECRET_KEY.
    Mismo formato que espera la app Flask (HS256, payload con sub/role/type).
    """
    if not _JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY no está configurado en las variables de entorno "
            "del servicio mcp_server. Debe coincidir con el SECRET_KEY de la app Flask."
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub":  _SERVICE_SUB,
        "role": _SERVICE_ROLE,
        "type": "access",
        "iat":  now,
        "exp":  now + datetime.timedelta(seconds=_JWT_TTL),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    logger.info(
        f"[Auth] Service token generado para '{_SERVICE_SUB}' "
        f"(válido {_JWT_TTL}s, expira en {datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=_JWT_TTL)})"
    )
    return token


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

async def get_auth_headers() -> dict:
    """
    Retorna los headers de autenticación con un JWT de servicio válido.

    Genera un nuevo token solo cuando el actual está vencido o a punto de vencer.
    No requiere usuario, contraseña ni llamadas HTTP.

    Returns:
        {"Authorization": "Bearer eyJ..."}
        Si JWT_SECRET_KEY no está configurado, retorna {} y loguea el error.
    """
    global _access_token, _token_expires_at

    if not _access_token or _is_expired():
        try:
            _access_token     = _generate_token()
            _token_expires_at = time.time() + _JWT_TTL
        except RuntimeError as exc:
            logger.error(f"[Auth] {exc}")
            return {}

    return {"Authorization": f"Bearer {_access_token}"}
