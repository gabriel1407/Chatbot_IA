"""
JWTService — genera y valida tokens JWT para la API.

Tokens emitidos:
  - access_token:   corta duración (30 min por defecto), para llamar las APIs
  - refresh_token:  larga duración (7 días), solo para renovar el access_token

Algoritmo: HS256 (shared secret desde JWT_SECRET_KEY en .env)

Payload del access_token:
  {
    "sub":      "admin_username",
    "role":     "admin" | "viewer",
    "type":     "access",
    "iat":      <timestamp emisión>,
    "exp":      <timestamp expiración>
  }
"""
from __future__ import annotations

import datetime
from typing import Optional

import jwt

from core.config.settings import settings
from core.logging.logger import get_app_logger

logger = get_app_logger()

_ALGORITHM = "HS256"


class TokenError(Exception):
    """Error de validación de token JWT."""


class JWTService:
    """Servicio centralizado de creación y validación de JWT."""

    def __init__(self):
        self._secret: str = settings.effective_jwt_secret
        self._access_ttl: int = settings.jwt_access_token_ttl_minutes   # minutos
        self._refresh_ttl: int = settings.jwt_refresh_token_ttl_days     # días

    # ------------------------------------------------------------------ #
    # Generación                                                           #
    # ------------------------------------------------------------------ #

    def create_access_token(self, username: str, role: str = "admin") -> str:
        """Genera un access token válido por `jwt_access_token_ttl_minutes` minutos."""
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "sub": username,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + datetime.timedelta(minutes=self._access_ttl),
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def create_refresh_token(self, username: str, role: str = "admin") -> str:
        """Genera un refresh token válido por `jwt_refresh_token_ttl_days` días."""
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "sub": username,
            "role": role,
            "type": "refresh",
            "iat": now,
            "exp": now + datetime.timedelta(days=self._refresh_ttl),
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def create_token_pair(self, username: str, role: str = "admin") -> dict:
        """Devuelve access + refresh token en un solo dict listo para responder."""
        return {
            "access_token": self.create_access_token(username, role),
            "refresh_token": self.create_refresh_token(username, role),
            "token_type": "Bearer",
            "expires_in": self._access_ttl * 60,   # segundos
        }

    # ------------------------------------------------------------------ #
    # Validación                                                           #
    # ------------------------------------------------------------------ #

    def decode(self, token: str, expected_type: Optional[str] = None) -> dict:
        """
        Decodifica y valida un token JWT.
        Lanza `TokenError` si el token es inválido, expirado o del tipo incorrecto.

        Args:
            token:         JWT crudo (sin el prefijo "Bearer ")
            expected_type: "access" | "refresh" | None (no valida tipo)

        Returns:
            Payload decodificado como dict.
        """
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise TokenError("Token expirado.")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Token inválido: {e}")

        if expected_type and payload.get("type") != expected_type:
            raise TokenError(
                f"Se esperaba token de tipo '{expected_type}', "
                f"se recibió '{payload.get('type')}'."
            )
        return payload

    def get_username_from_token(self, token: str) -> str:
        """Extrae el campo 'sub' (username) de un access token."""
        payload = self.decode(token, expected_type="access")
        return payload["sub"]


# Instancia global (singleton) para importar directamente
jwt_service = JWTService()
