"""
TenantChannel - Entidad que representa las credenciales de un canal de comunicación
para un tenant específico (WhatsApp, Telegram, etc.).
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TenantChannel:
    """
    Credenciales y configuración de un canal de comunicación por tenant.

    Cada tenant puede tener uno o más canales activos.
    Cuando llega un mensaje, se busca el tenant por los identificadores
    del canal (phone_number_id para WhatsApp, bot_token para Telegram).
    """
    tenant_id: str
    channel: str                          # "whatsapp" | "telegram"
    token: str                            # Token de acceso del canal
    is_active: bool = True

    # WhatsApp
    phone_number_id: Optional[str] = None  # ID del número de WhatsApp Business
    verify_token: Optional[str] = None     # Token de verificación del webhook

    # Telegram
    bot_username: Optional[str] = None     # @NombreDelBot

    # Metadata
    display_name: Optional[str] = None    # Nombre descriptivo, ej: "WhatsApp Digitel"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self, mask_token: bool = True) -> dict:
        token_display = f"{self.token[:8]}...{self.token[-4:]}" if mask_token and len(self.token) > 12 else self.token
        return {
            "tenant_id": self.tenant_id,
            "channel": self.channel,
            "token": token_display,
            "is_active": self.is_active,
            "phone_number_id": self.phone_number_id,
            "verify_token": self.verify_token,
            "bot_username": self.bot_username,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "TenantChannel":
        return TenantChannel(
            tenant_id=data["tenant_id"],
            channel=data["channel"],
            token=data["token"],
            is_active=bool(data.get("is_active", True)),
            phone_number_id=data.get("phone_number_id"),
            verify_token=data.get("verify_token"),
            bot_username=data.get("bot_username"),
            display_name=data.get("display_name"),
        )
