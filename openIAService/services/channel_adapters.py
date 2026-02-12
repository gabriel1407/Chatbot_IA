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
from core.config.settings import settings


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
    
    def __init__(
        self,
        message_handler: Optional[ImprovedMessageHandler] = None,
        adapters: Optional[Dict[ChannelType, ChannelAdapter]] = None,
    ):
        if message_handler is not None:
            self.message_handler = message_handler
        else:
            try:
                from core.config.dependencies import get_message_handler
                self.message_handler = get_message_handler()
            except Exception:
                self.message_handler = create_message_handler()
        self.adapters: Dict[ChannelType, ChannelAdapter] = adapters or {
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
                if self._is_ignorable_event(channel=channel, raw_data=raw_data):
                    self.logger.info(f"Evento de {channel.value} ignorado (no es mensaje de usuario)")
                    return True

                self.logger.warning(f"No se pudo parsear mensaje de {channel.value}")
                return False
            
            # Descargar archivos multimedia si es necesario
            if incoming_message.message_type != MessageType.TEXT:
                file_path = self._download_media_if_needed(adapter, incoming_message)
                if file_path:
                    incoming_message.metadata["file_path"] = file_path

            streaming_enabled = bool(
                settings.ai_provider == "ollama"
                and settings.ollama_channel_streaming_enabled
                and channel == ChannelType.TELEGRAM
            )
            thinking_enabled = bool(
                settings.ai_provider == "ollama"
                and settings.ollama_channel_thinking_enabled
            )

            traced_response = self.message_handler.handle_user_message_with_trace(
                user_id=incoming_message.user_id,
                content=incoming_message.content,
                message_type=incoming_message.message_type,
                metadata=incoming_message.metadata,
                include_thinking=thinking_enabled,
            )

            emitter = self._build_response_emitter(
                channel=channel,
                adapter=adapter,
                recipient_id=incoming_message.user_id,
                streaming_enabled=streaming_enabled,
                show_thinking=thinking_enabled,
            )

            success = emitter.emit(
                content=traced_response.get("content", ""),
                thinking=traced_response.get("thinking", ""),
            )
            
            if success:
                self.logger.info(f"Mensaje procesado exitosamente en {channel.value}")
            else:
                self.logger.error(f"Error enviando respuesta en {channel.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error procesando webhook de {channel.value}: {e}")
            return False

    def _is_ignorable_event(self, *, channel: ChannelType, raw_data: Dict[str, Any]) -> bool:
        """Determina si un webhook sin mensaje es un evento válido a ignorar."""
        try:
            if channel == ChannelType.WHATSAPP:
                entry = (raw_data.get("entry") or [])
                if not entry:
                    return False
                changes = (entry[0].get("changes") or [])
                if not changes:
                    return False
                value = changes[0].get("value", {})
                # Status updates de Meta (delivered/read/sent) y otros callbacks sin messages
                if "statuses" in value:
                    return True
                if "messages" not in value:
                    return True
                if not value.get("messages"):
                    return True
                return False

            if channel == ChannelType.TELEGRAM:
                # Telegram manda múltiples tipos de update, no solo "message"
                if "message" not in raw_data and any(
                    key in raw_data for key in (
                        "edited_message",
                        "channel_post",
                        "edited_channel_post",
                        "callback_query",
                        "my_chat_member",
                        "chat_member",
                    )
                ):
                    return True
                return False

            return False
        except Exception:
            return False

    def _build_response_emitter(
        self,
        *,
        channel: ChannelType,
        adapter: ChannelAdapter,
        recipient_id: str,
        streaming_enabled: bool,
        show_thinking: bool,
    ):
        if channel == ChannelType.TELEGRAM:
            return TelegramResponseEmitter(
                adapter=adapter,
                recipient_id=recipient_id,
                streaming_enabled=streaming_enabled,
                show_thinking=show_thinking,
            )

        return WhatsAppResponseEmitter(
            adapter=adapter,
            recipient_id=recipient_id,
            show_thinking=show_thinking,
        )
    
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

    def resolve_channel(self, channel_name: str) -> Optional[ChannelType]:
        """Resuelve el tipo de canal desde su nombre textual."""
        normalized_channel_name = str(channel_name).strip().lower()
        channel_map = {
            ChannelType.WHATSAPP.value: ChannelType.WHATSAPP,
            ChannelType.TELEGRAM.value: ChannelType.TELEGRAM,
        }
        return channel_map.get(normalized_channel_name)

    def send_outgoing_message(
        self,
        *,
        channel_name: str,
        recipient_id: str,
        content: str,
    ) -> tuple[bool, str, int]:
        """Envía un mensaje saliente abstraído por canal."""
        channel = self.resolve_channel(channel_name)
        if not channel:
            return False, f"Canal no soportado: {channel_name}", 400

        adapter = self.adapters.get(channel)
        if not adapter:
            return False, f"Adapter no disponible para canal {channel_name}", 500

        message = OutgoingMessage(
            recipient_id=recipient_id,
            content=content,
            channel=channel,
        )

        success = adapter.send_message(message)
        if success:
            self.logger.info(f"Mensaje enviado programáticamente a {channel_name}: {recipient_id}")
            return True, "Mensaje enviado", 200

        self.logger.error(f"Error enviando mensaje programáticamente a {channel_name}")
        return False, "Error enviando mensaje", 500

def get_unified_channel_service() -> UnifiedChannelService:
    """Obtiene el servicio unificado desde el container de dependencias."""
    from core.config.dependencies import get_unified_channel_service_dep

    return get_unified_channel_service_dep()


class BaseChannelResponseEmitter:
    """Interfaz base de emisión de respuestas por canal."""

    def emit(self, *, content: str, thinking: str = "") -> bool:
        raise NotImplementedError


class WhatsAppResponseEmitter(BaseChannelResponseEmitter):
    def __init__(self, *, adapter: ChannelAdapter, recipient_id: str, show_thinking: bool):
        self.adapter = adapter
        self.recipient_id = recipient_id
        self.show_thinking = show_thinking

    def emit(self, *, content: str, thinking: str = "") -> bool:
        # WhatsApp no es ideal para simular streaming por chunks en webhook estándar.
        # Se envía mensaje final y, opcionalmente, un aviso previo de procesamiento.
        if self.show_thinking and thinking:
            self.adapter.send_message(
                OutgoingMessage(
                    recipient_id=self.recipient_id,
                    content="🤔 Analizando tu consulta...",
                    channel=ChannelType.WHATSAPP,
                )
            )

        return self.adapter.send_message(
            OutgoingMessage(
                recipient_id=self.recipient_id,
                content=content,
                channel=ChannelType.WHATSAPP,
            )
        )


class TelegramResponseEmitter(BaseChannelResponseEmitter):
    def __init__(
        self,
        *,
        adapter: ChannelAdapter,
        recipient_id: str,
        streaming_enabled: bool,
        show_thinking: bool,
    ):
        self.adapter = adapter
        self.recipient_id = recipient_id
        self.streaming_enabled = streaming_enabled
        self.show_thinking = show_thinking

    def emit(self, *, content: str, thinking: str = "") -> bool:
        if not self.streaming_enabled:
            return self.adapter.send_message(
                OutgoingMessage(
                    recipient_id=self.recipient_id,
                    content=content,
                    channel=ChannelType.TELEGRAM,
                )
            )

        message_id = self._send_initial_message("⏳ Pensando...")
        if message_id is None:
            return self.adapter.send_message(
                OutgoingMessage(
                    recipient_id=self.recipient_id,
                    content=content,
                    channel=ChannelType.TELEGRAM,
                )
            )

        header = ""
        if self.show_thinking and thinking:
            clipped_thinking = thinking[:1000]
            header = f"🤔 Pensamiento:\n{clipped_thinking}\n\n✍️ Respuesta:\n"

        stream_source = content or ""
        chunk_size = max(40, int(settings.ollama_stream_chunk_size or 120))
        max_updates = max(1, int(settings.ollama_stream_max_updates or 20))

        emitted = 0
        for idx in range(0, len(stream_source), chunk_size):
            if emitted >= max_updates:
                break
            partial = stream_source[: idx + chunk_size]
            text = f"{header}{partial}" if header else partial
            if not self._edit_message(message_id=message_id, text=text):
                return self.adapter.send_message(
                    OutgoingMessage(
                        recipient_id=self.recipient_id,
                        content=content,
                        channel=ChannelType.TELEGRAM,
                    )
                )
            emitted += 1

        final_text = f"{header}{stream_source}" if header else stream_source
        return self._edit_message(message_id=message_id, text=final_text)

    def _send_initial_message(self, text: str) -> Optional[int]:
        try:
            import requests

            url = f"{self.adapter.api_url}/sendMessage"
            payload = {
                "chat_id": self.recipient_id,
                "text": text,
            }
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                return None

            data = response.json()
            if not data.get("ok"):
                return None

            return data.get("result", {}).get("message_id")
        except Exception:
            return None

    def _edit_message(self, *, message_id: int, text: str) -> bool:
        try:
            import requests

            url = f"{self.adapter.api_url}/editMessageText"
            payload = {
                "chat_id": self.recipient_id,
                "message_id": message_id,
                "text": text or " ",
            }
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception:
            return False