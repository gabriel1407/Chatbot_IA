"""
DTOs para requests de canales de mensajería.
Centraliza validaciones HTTP en capa application.
"""
from dataclasses import dataclass
from typing import Any, Dict


SUPPORTED_CHANNELS = {"whatsapp", "telegram"}


@dataclass(frozen=True)
class SendMessageRequest:
    recipient_id: str
    content: str
    channel: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SendMessageRequest":
        if not isinstance(data, dict):
            raise ValueError("No se proporcionaron datos JSON válidos")

        recipient_id = str(data.get("recipient_id", "")).strip()
        content = str(data.get("content", "")).strip()
        channel = str(data.get("channel", "")).strip().lower()

        if not recipient_id:
            raise ValueError("Campo requerido faltante: recipient_id")
        if not content:
            raise ValueError("Campo requerido faltante: content")
        if channel not in SUPPORTED_CHANNELS:
            raise ValueError(f"Canal no soportado: {channel}")

        return cls(recipient_id=recipient_id, content=content, channel=channel)
