"""
SQLite Context Repository Implementation.
Implementa el Repository pattern para el contexto de conversaciones.
Aplica principios SOLID y Clean Code.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from domain.entities.conversation import Conversation
from domain.entities.message import Message, MessageRole, MessageType
from domain.repositories.conversation_repository import ConversationRepository
from core.logging.logger import get_infrastructure_logger


class SQLiteConversationRepository(ConversationRepository):
    """
    Implementación SQLite del repositorio de conversaciones.
    Cumple con el principio de Single Responsibility.
    """
    
    def __init__(self, db_path: str = "local/contextos.db"):
        self.db_path = db_path
        self.logger = get_infrastructure_logger()
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Asegura que la base de datos y tablas existan."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_context (
                    user_id TEXT,
                    context_id TEXT,
                    context TEXT,
                    last_updated TIMESTAMP,
                    PRIMARY KEY (user_id, context_id)
                )
            """)
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene una conexión a la base de datos."""
        return sqlite3.connect(self.db_path)
    
    def save(self, conversation: Conversation) -> Conversation:
        """
        Guarda o actualiza una conversación.
        
        Args:
            conversation: Conversación a guardar
            
        Returns:
            Conversación guardada con ID asignado
        """
        try:
            # Convertir mensajes a JSON
            context_data = [msg.to_dict() for msg in conversation.messages]
            context_json = json.dumps(context_data, ensure_ascii=False)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_context 
                    (user_id, context_id, context, last_updated) 
                    VALUES (?, ?, ?, ?)
                """, (
                    conversation.user_id,
                    conversation.context_id,
                    context_json,
                    datetime.now()
                ))
                conn.commit()
            
            # Actualizar timestamp
            conversation.updated_at = datetime.now()
            
            self.logger.info(
                f"Conversación guardada: user={conversation.user_id}, "
                f"context={conversation.context_id}, messages={len(conversation.messages)}"
            )
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error guardando conversación: {e}")
            raise
    
    def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Busca una conversación por su ID.
        
        Args:
            conversation_id: ID de la conversación (formato: user_id:context_id)
            
        Returns:
            Conversación encontrada o None
        """
        try:
            # Parsear el ID compuesto
            if ':' in conversation_id:
                user_id, context_id = conversation_id.split(':', 1)
            else:
                user_id, context_id = conversation_id, "default"
            
            return self.find_by_user_and_context(user_id, context_id)
            
        except Exception as e:
            self.logger.error(f"Error buscando conversación por ID {conversation_id}: {e}")
            return None
    
    def find_by_user_and_context(
        self,
        user_id: str,
        context_id: str = "default"
    ) -> Optional[Conversation]:
        """
        Busca una conversación por usuario y contexto.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto/tema
            
        Returns:
            Conversación encontrada o None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT context, last_updated 
                    FROM user_context 
                    WHERE user_id = ? AND context_id = ?
                """, (user_id, context_id))
                
                row = cursor.fetchone()
            
            if not row:
                self.logger.info(f"No existe conversación para user={user_id}, context={context_id}")
                return None
            
            context_json, last_updated_str = row
            
            # Crear conversación
            conversation = Conversation(
                user_id=user_id,
                context_id=context_id,
                id=f"{user_id}:{context_id}",
                updated_at=datetime.fromisoformat(last_updated_str) if isinstance(last_updated_str, str) else last_updated_str
            )
            
            # Cargar mensajes si existen
            if context_json:
                try:
                    messages_data = json.loads(context_json)
                    for msg_data in messages_data:
                        message = Message(
                            content=msg_data.get("content", ""),
                            role=MessageRole(msg_data.get("role", "user")),
                            user_id=user_id,
                            conversation_id=conversation.id,
                            message_type=MessageType.TEXT  # Por defecto texto
                        )
                        conversation.add_message(message)
                        
                except Exception as e:
                    self.logger.error(f"Error decodificando mensajes: {e}")
                    # Reiniciar conversación si hay error en JSON
                    conversation.clear_messages()
                    self.save(conversation)
            
            self.logger.info(
                f"Conversación cargada: user={user_id}, context={context_id}, "
                f"messages={len(conversation.messages)}"
            )
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error cargando conversación: {e}")
            return None
    
    def find_all_by_user(self, user_id: str) -> List[Conversation]:
        """
        Busca todas las conversaciones de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT context_id, last_updated 
                    FROM user_context 
                    WHERE user_id = ? 
                    ORDER BY last_updated DESC
                """, (user_id,))
                
                rows = cursor.fetchall()
            
            conversations = []
            for context_id, last_updated_str in rows:
                conversation = self.find_by_user_and_context(user_id, context_id)
                if conversation:
                    conversations.append(conversation)
            
            self.logger.info(f"Encontradas {len(conversations)} conversaciones para user={user_id}")
            return conversations
            
        except Exception as e:
            self.logger.error(f"Error obteniendo conversaciones de usuario {user_id}: {e}")
            return []
    
    def delete(self, conversation_id: str) -> bool:
        """
        Elimina una conversación.
        
        Args:
            conversation_id: ID de la conversación (formato: user_id:context_id)
            
        Returns:
            True si se eliminó, False si no existía
        """
        try:
            # Parsear el ID compuesto
            if ':' in conversation_id:
                user_id, context_id = conversation_id.split(':', 1)
            else:
                user_id, context_id = conversation_id, "default"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM user_context 
                    WHERE user_id = ? AND context_id = ?
                """, (user_id, context_id))
                
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"Conversación eliminada: {conversation_id}")
                return True
            else:
                self.logger.warning(f"No se encontró conversación para eliminar: {conversation_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error eliminando conversación {conversation_id}: {e}")
            return False
    
    def get_active_context_id(self, user_id: str) -> str:
        """
        Obtiene el context_id más reciente de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Context ID activo o "default"
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT context_id 
                    FROM user_context 
                    WHERE user_id = ? 
                    ORDER BY last_updated DESC 
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
            
            if row and row[0]:
                self.logger.debug(f"Context activo para user={user_id}: {row[0]}")
                return row[0]
            else:
                self.logger.debug(f"No hay context activo para user={user_id}, usando 'default'")
                return "default"
                
        except Exception as e:
            self.logger.error(f"Error obteniendo context activo para user={user_id}: {e}")
            return "default"


class TopicDetectionService:
    """
    Servicio para detectar cambios de tema en conversaciones.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(self):
        self.logger = get_infrastructure_logger()
        self._topic_keywords = [
            # Español
            "nuevo tema", "hablemos de", "cambia de tema", "cambiar de tema", 
            "nueva conversación", "otro asunto", "otra pregunta", "hablemos sobre", 
            "hablar de", "nuevo tópico", "hablar ahora de", "quisiera preguntar sobre", 
            "otra cosa", "cambiar el tema", "tema diferente", "empezar otro tema",
            "quiero hablar de", "tengo otra duda", "podemos cambiar de tema",
            "ahora quiero preguntar", "otra consulta", "consultar otra cosa", 
            "otra pregunta", "cambiando de tema",
            
            # Inglés
            "start new topic", "change topic", "new conversation", "different subject", 
            "let's talk about", "can we talk about", "new subject", "another topic", 
            "move on to"
        ]
    
    def detect_new_topic(self, user_input: str) -> bool:
        """
        Detecta si el usuario quiere empezar un nuevo tema.
        
        Args:
            user_input: Entrada del usuario
            
        Returns:
            True si se detecta cambio de tema
        """
        if not user_input or not user_input.strip():
            return False
        
        lower_input = user_input.lower().strip()
        
        # Verificar palabras clave
        topic_detected = any(phrase in lower_input for phrase in self._topic_keywords)
        
        if topic_detected:
            self.logger.info(f"Nuevo tema detectado en: '{user_input[:50]}...'")
        
        return topic_detected
    
    def add_keyword(self, keyword: str) -> None:
        """Agrega una nueva palabra clave para detección de temas."""
        if keyword and keyword.lower() not in self._topic_keywords:
            self._topic_keywords.append(keyword.lower())
            self.logger.info(f"Nueva palabra clave agregada: '{keyword}'")
    
    def get_keywords(self) -> List[str]:
        """Obtiene todas las palabras clave configuradas."""
        return self._topic_keywords.copy()