"""
Interface MessagingService - Define el contrato para servicios de mensajería.
Abstracción para múltiples canales (Telegram, WhatsApp, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional


class MessagingService(ABC):
    """
    Interface para servicios de mensajería.
    Permite abstraer el canal específico (Telegram, WhatsApp, etc.).
    """
    
    @abstractmethod
    def send_message(self, recipient_id: str, message: str) -> bool:
        """
        Envía un mensaje de texto.
        
        Args:
            recipient_id: ID del destinatario
            message: Contenido del mensaje
            
        Returns:
            True si se envió exitosamente
        """
        pass
    
    @abstractmethod
    def download_media(
        self,
        media_id: str,
        media_type: str
    ) -> Optional[str]:
        """
        Descarga un archivo multimedia.
        
        Args:
            media_id: ID del archivo
            media_type: Tipo de archivo (image, audio, document)
            
        Returns:
            Ruta del archivo descargado o None
        """
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Retorna el nombre del canal.
        
        Returns:
            Nombre del canal (ej: "telegram", "whatsapp")
        """
        pass
