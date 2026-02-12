"""
Channel Service Adapters - Adaptadores para servicios de canales de comunicación.
Implementa principios SOLID y patrón Adapter.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from domain.entities.message import MessageType
from services.improved_message_handler import ImprovedMessageHandler, create_message_handler
from core.logging.logger import get_whatsapp_logger, get_telegram_logger


class ChannelType(Enum):
    """Tipos de canales de comunicación soportados."""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


@dataclass
class IncomingMessage:
    """Value Object que representa un mensaje entrante."""
    
    user_id: str
    content: str
    message_type: MessageType
    channel: ChannelType
    metadata: Dict[str, Any]
    raw_message: Dict[str, Any]


@dataclass
class OutgoingMessage:
    """Value Object que representa un mensaje saliente."""
    
    recipient_id: str
    content: str
    channel: ChannelType
    message_format: str = "text"  # text, json, etc.


class ChannelAdapter(ABC):
    """
    Adapter interface para diferentes canales de comunicación.
    Implementa Strategy Pattern para múltiples canales.
    """
    
    @abstractmethod
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parsea un mensaje entrante del canal específico."""
        pass
    
    @abstractmethod
    def send_message(self, message: OutgoingMessage) -> bool:
        """Envía un mensaje a través del canal."""
        pass
    
    @abstractmethod
    def download_media(self, media_id: str, media_type: str) -> Optional[str]:
        """Descarga archivos multimedia del canal."""
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """Retorna el nombre del canal."""
        pass


class WhatsAppAdapter(ChannelAdapter):
    """Adapter para WhatsApp Business API."""
    
    def __init__(self):
        from core.config.settings import settings
        from core.deduplication_cache import get_deduplication_cache
        self.token = settings.whatsapp_token
        self.api_url = settings.whatsapp_api_url
        self.logger = get_whatsapp_logger()
        # Deduplicación: cache compartido entre workers usando SQLite
        self._dedup_cache = get_deduplication_cache()
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Parsea mensaje entrante de WhatsApp.
        
        Args:
            raw_data: Datos crudos del webhook de WhatsApp
            
        Returns:
            IncomingMessage parseado o None si no es válido
        """
        try:
            # Extraer mensaje del JSON de WhatsApp
            if "entry" not in raw_data or not raw_data["entry"]:
                return None
            
            entry = raw_data["entry"][0]
            if "changes" not in entry or not entry["changes"]:
                return None
            
            changes = entry["changes"][0]
            value = changes.get("value", {})
            
            # Filtrar status updates (delivered, read, sent, etc.)
            if "statuses" in value:
                self.logger.debug("Ignorando status update de WhatsApp")
                return None
            
            if "messages" not in value:
                self.logger.debug("Webhook sin campo 'messages' - ignorando")
                return None
            
            messages = value["messages"]
            if not messages:
                return None
            
            message = messages[0]
            
            # Deduplicación: verificar message_id en cache compartido
            message_id = message.get("id")
            if message_id:
                if self._dedup_cache.is_processed(message_id, "whatsapp"):
                    self.logger.info(f"✓ Mensaje duplicado ignorado (cache compartido): {message_id}")
                    return None
                
                # Marcar como procesado en cache compartido
                self._dedup_cache.mark_processed(message_id, "whatsapp")
                self.logger.debug(f"✓ Mensaje marcado como procesado: {message_id}")
            
            # Extraer datos básicos
            user_id = message.get("from", "")
            if not user_id:
                return None
            
            # Determinar tipo de mensaje y extraer contenido
            content, message_type, metadata = self._extract_message_content(message)
            
            return IncomingMessage(
                user_id=user_id,
                content=content,
                message_type=message_type,
                channel=ChannelType.WHATSAPP,
                metadata=metadata,
                raw_message=message
            )
            
        except Exception as e:
            self.logger.error(f"Error parseando mensaje de WhatsApp: {e}")
            return None
    
    def _extract_message_content(self, message: Dict[str, Any]) -> Tuple[str, MessageType, Dict[str, Any]]:
        """Extrae contenido, tipo y metadatos del mensaje de WhatsApp."""
        metadata = {}
        
        if "text" in message:
            return message["text"].get("body", ""), MessageType.TEXT, metadata
        
        elif "image" in message:
            image = message["image"]
            caption = image.get("caption", "Imagen recibida")
            media_id = image.get("id", "")
            metadata.update({
                "media_id": media_id,
                "mime_type": image.get("mime_type", "image/jpeg")
            })
            return caption, MessageType.IMAGE, metadata
        
        elif "audio" in message:
            audio = message["audio"]
            media_id = audio.get("id", "")
            metadata.update({
                "media_id": media_id,
                "mime_type": audio.get("mime_type", "audio/ogg")
            })
            return "Audio recibido", MessageType.AUDIO, metadata
        
        elif "document" in message:
            document = message["document"]
            media_id = document.get("id", "")
            filename = document.get("filename", "documento")
            metadata.update({
                "media_id": media_id,
                "mime_type": document.get("mime_type", ""),
                "filename": filename
            })
            return f"Documento: {filename}", MessageType.DOCUMENT, metadata
        
        else:
            return "Mensaje no reconocido", MessageType.TEXT, metadata
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """Envía un mensaje de texto a WhatsApp."""
        try:
            import requests
            import json
            
            body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": message.recipient_id,
                "type": "text",
                "text": {"body": message.content}
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            
            response = requests.post(self.api_url, data=json.dumps(body), headers=headers)
            
            success = response.status_code == 200
            if success:
                self.logger.info(f"Mensaje enviado a WhatsApp: {message.recipient_id}")
            else:
                self.logger.error(f"Error enviando mensaje a WhatsApp: {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error en send_message de WhatsApp: {e}")
            return False
    
    def download_media(self, media_id: str, media_type: str) -> Optional[str]:
        """Descarga archivos multimedia de WhatsApp."""
        try:
            import requests
            
            # Obtener URL del archivo
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            media_url = response.json().get('url')
            if not media_url:
                return None
            
            # Descargar archivo
            media_response = requests.get(media_url, headers=headers)
            if media_response.status_code != 200:
                return None
            
            # Guardar archivo
            file_extension = media_type.split('/')[-1]
            file_path = f"local/uploads/{media_id}.{file_extension}"
            
            with open(file_path, 'wb') as f:
                f.write(media_response.content)
            
            self.logger.info(f"Archivo descargado de WhatsApp: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error descargando archivo de WhatsApp: {e}")
            return None
    
    def get_channel_name(self) -> str:
        return "WhatsApp"


class TelegramAdapter(ChannelAdapter):
    """Adapter para Telegram Bot API."""
    
    def __init__(self):
        from core.config.settings import settings
        self.token = settings.telegram_token
        self.api_url = settings.telegram_api_url
        self.logger = get_telegram_logger()
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Parsea mensaje entrante de Telegram.
        
        Args:
            raw_data: Datos crudos del webhook de Telegram
            
        Returns:
            IncomingMessage parseado o None si no es válido
        """
        try:
            message = raw_data.get("message")
            if not message:
                return None
            
            chat_id = str(message["chat"]["id"])
            
            # Determinar tipo de mensaje y extraer contenido
            content, message_type, metadata = self._extract_message_content(message)
            
            return IncomingMessage(
                user_id=chat_id,
                content=content,
                message_type=message_type,
                channel=ChannelType.TELEGRAM,
                metadata=metadata,
                raw_message=message
            )
            
        except Exception as e:
            self.logger.error(f"Error parseando mensaje de Telegram: {e}")
            return None
    
    def _extract_message_content(self, message: Dict[str, Any]) -> Tuple[str, MessageType, Dict[str, Any]]:
        """Extrae contenido, tipo y metadatos del mensaje de Telegram."""
        metadata = {}
        
        if "text" in message:
            return message["text"], MessageType.TEXT, metadata
        
        elif "photo" in message:
            photo = message["photo"][-1]  # Mejor calidad
            caption = message.get("caption", "Imagen recibida")
            file_id = photo.get("file_id", "")
            metadata.update({
                "file_id": file_id
            })
            return caption, MessageType.IMAGE, metadata
        
        elif "audio" in message or "voice" in message:
            audio = message.get("audio") or message.get("voice")
            file_id = audio.get("file_id", "")
            metadata.update({
                "file_id": file_id
            })
            return "Audio recibido", MessageType.AUDIO, metadata
        
        elif "document" in message:
            document = message["document"]
            file_id = document.get("file_id", "")
            filename = document.get("file_name", "documento")
            metadata.update({
                "file_id": file_id,
                "mime_type": document.get("mime_type", ""),
                "filename": filename
            })
            return f"Documento: {filename}", MessageType.DOCUMENT, metadata
        
        else:
            return "Mensaje no reconocido", MessageType.TEXT, metadata
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """Envía un mensaje de texto a Telegram."""
        try:
            import requests
            
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": message.recipient_id,
                "text": message.content
            }
            
            response = requests.post(url, json=payload)
            
            success = response.status_code == 200
            if success:
                self.logger.info(f"Mensaje enviado a Telegram: {message.recipient_id}")
            else:
                self.logger.error(f"Error enviando mensaje a Telegram: {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error en send_message de Telegram: {e}")
            return False
    
    def download_media(self, file_id: str, media_type: str) -> Optional[str]:
        """Descarga archivos multimedia de Telegram."""
        try:
            import requests
            
            # Obtener información del archivo
            file_info_url = f"{self.api_url}/getFile?file_id={file_id}"
            file_info_response = requests.get(file_info_url)
            
            if file_info_response.status_code != 200:
                return None
            
            file_info = file_info_response.json()
            if not file_info.get("ok"):
                return None
            
            file_path = file_info["result"]["file_path"]
            
            # Descargar archivo
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            file_response = requests.get(file_url)
            
            if file_response.status_code != 200:
                return None
            
            # Guardar archivo
            file_extension = file_path.split('.')[-1] if '.' in file_path else 'bin'
            local_path = f"local/uploads/{file_id}.{file_extension}"
            
            with open(local_path, "wb") as f:
                f.write(file_response.content)
            
            self.logger.info(f"Archivo descargado de Telegram: {local_path}")
            return local_path
            
        except Exception as e:
            self.logger.error(f"Error descargando archivo de Telegram: {e}")
            return None
    
    def get_channel_name(self) -> str:
        return "Telegram"


class UnifiedChannelService:
    """
    Servicio unificado para manejar múltiples canales de comunicación.
    Implementa Strategy Pattern y Dependency Injection.
    """
    
    def __init__(self, message_handler: Optional[ImprovedMessageHandler] = None):
        self.message_handler = message_handler or create_message_handler()
        self.adapters: Dict[ChannelType, ChannelAdapter] = {
            ChannelType.WHATSAPP: WhatsAppAdapter(),
            ChannelType.TELEGRAM: TelegramAdapter()
        }
        self.logger = get_whatsapp_logger()  # Logger general
    
    def process_webhook(self, channel: ChannelType, raw_data: Dict[str, Any]) -> bool:
        """
        Procesa un webhook de cualquier canal.
        
        Args:
            channel: Tipo de canal
            raw_data: Datos crudos del webhook
            
        Returns:
            True si se procesó exitosamente
        """
        try:
            # Obtener adapter del canal
            adapter = self.adapters.get(channel)
            if not adapter:
                self.logger.error(f"No hay adapter disponible para canal {channel.value}")
                return False
            
            # Parsear mensaje entrante
            incoming_message = adapter.parse_incoming_message(raw_data)
            if not incoming_message:
                self.logger.warning(f"No se pudo parsear mensaje de {channel.value}")
                return False
            
            # Descargar archivos multimedia si es necesario
            if incoming_message.message_type != MessageType.TEXT:
                file_path = self._download_media_if_needed(adapter, incoming_message)
                if file_path:
                    incoming_message.metadata["file_path"] = file_path
            
            # Procesar mensaje con el handler
            response = self.message_handler.handle_user_message(
                user_id=incoming_message.user_id,
                content=incoming_message.content,
                message_type=incoming_message.message_type,
                metadata=incoming_message.metadata
            )
            
            # Enviar respuesta
            outgoing_message = OutgoingMessage(
                recipient_id=incoming_message.user_id,
                content=response,
                channel=channel
            )
            
            success = adapter.send_message(outgoing_message)
            
            if success:
                self.logger.info(f"Mensaje procesado exitosamente en {channel.value}")
            else:
                self.logger.error(f"Error enviando respuesta en {channel.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error procesando webhook de {channel.value}: {e}")
            return False
    
    def _download_media_if_needed(
        self, 
        adapter: ChannelAdapter, 
        message: IncomingMessage
    ) -> Optional[str]:
        """Descarga archivos multimedia si es necesario."""
        try:
            if message.message_type == MessageType.TEXT:
                return None
            
            # Obtener ID del archivo según el canal
            if message.channel == ChannelType.WHATSAPP:
                media_id = message.metadata.get("media_id")
                media_type = message.metadata.get("mime_type", "")
            elif message.channel == ChannelType.TELEGRAM:
                media_id = message.metadata.get("file_id")
                media_type = message.metadata.get("mime_type", "")
            else:
                return None
            
            if not media_id:
                return None
            
            return adapter.download_media(media_id, media_type)
            
        except Exception as e:
            self.logger.error(f"Error descargando archivo multimedia: {e}")
            return None
    
    def get_channel_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los canales disponibles."""
        return {
            "available_channels": [channel.value for channel in self.adapters.keys()],
            "adapters": {
                channel.value: adapter.get_channel_name() 
                for channel, adapter in self.adapters.items()
            }
        }


# Instancia global del servicio unificado
_unified_service = None

def get_unified_channel_service() -> UnifiedChannelService:
    """Factory function para obtener el servicio unificado."""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedChannelService()
    return _unified_service