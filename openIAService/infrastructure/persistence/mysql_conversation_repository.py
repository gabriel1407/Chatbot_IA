"""
MySQL Context Repository Implementation.
Implementa el Repository pattern para el contexto de conversaciones.
"""
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from domain.entities.conversation import Conversation
from domain.entities.message import Message, MessageRole, MessageType
from domain.repositories.conversation_repository import ConversationRepository
from core.logging.logger import get_infrastructure_logger


class MySQLConversationRepository(ConversationRepository):
    """
    Implementación MySQL del repositorio de conversaciones.
    Cumple el mismo contrato que SQLiteConversationRepository.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = get_infrastructure_logger()
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
        self._ensure_database_exists()

    def _ensure_database_exists(self) -> None:
        """Asegura que la tabla requerida exista."""
        create_sql = text(
            """
            CREATE TABLE IF NOT EXISTS user_context (
                user_id VARCHAR(255) NOT NULL,
                context_id VARCHAR(255) NOT NULL,
                context LONGTEXT,
                last_updated DATETIME NOT NULL,
                PRIMARY KEY (user_id, context_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        with self.engine.begin() as connection:
            connection.execute(create_sql)

    def save(self, conversation: Conversation) -> Conversation:
        """Guarda o actualiza una conversación."""
        try:
            context_data = [msg.to_dict() for msg in conversation.messages]
            context_json = json.dumps(context_data, ensure_ascii=False)
            now = datetime.now()

            upsert_sql = text(
                """
                INSERT INTO user_context (user_id, context_id, context, last_updated)
                VALUES (:user_id, :context_id, :context, :last_updated)
                ON DUPLICATE KEY UPDATE
                    context = VALUES(context),
                    last_updated = VALUES(last_updated)
                """
            )

            with self.engine.begin() as connection:
                connection.execute(
                    upsert_sql,
                    {
                        "user_id": conversation.user_id,
                        "context_id": conversation.context_id,
                        "context": context_json,
                        "last_updated": now,
                    },
                )

            conversation.updated_at = now
            self.logger.info(
                f"Conversación guardada (MySQL): user={conversation.user_id}, "
                f"context={conversation.context_id}, messages={len(conversation.messages)}"
            )
            return conversation
        except SQLAlchemyError as e:
            self.logger.error(f"Error guardando conversación en MySQL: {e}")
            raise

    def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Busca una conversación por su ID compuesto."""
        try:
            if ':' in conversation_id:
                user_id, context_id = conversation_id.split(':', 1)
            else:
                user_id, context_id = conversation_id, "default"

            return self.find_by_user_and_context(user_id, context_id)
        except Exception as e:
            self.logger.error(f"Error buscando conversación por ID {conversation_id}: {e}")
            return None

    def find_by_user_and_context(self, user_id: str, context_id: str = "default") -> Optional[Conversation]:
        """Busca una conversación por usuario y contexto."""
        try:
            select_sql = text(
                """
                SELECT context, last_updated
                FROM user_context
                WHERE user_id = :user_id AND context_id = :context_id
                """
            )
            with self.engine.connect() as connection:
                row = connection.execute(
                    select_sql,
                    {"user_id": user_id, "context_id": context_id},
                ).first()

            if not row:
                self.logger.info(f"No existe conversación para user={user_id}, context={context_id}")
                return None

            context_json = row[0]
            last_updated = row[1]

            conversation = Conversation(
                user_id=user_id,
                context_id=context_id,
                id=f"{user_id}:{context_id}",
                updated_at=last_updated if isinstance(last_updated, datetime) else datetime.now(),
            )

            if context_json:
                try:
                    messages_data = json.loads(context_json)
                    for msg_data in messages_data:
                        message = Message(
                            content=msg_data.get("content", ""),
                            role=MessageRole(msg_data.get("role", "user")),
                            user_id=user_id,
                            conversation_id=conversation.id,
                            message_type=MessageType.TEXT,
                        )
                        conversation.add_message(message)
                except Exception as e:
                    self.logger.error(f"Error decodificando mensajes en MySQL: {e}")
                    conversation.clear_messages()
                    self.save(conversation)

            self.logger.info(
                f"Conversación cargada (MySQL): user={user_id}, context={context_id}, "
                f"messages={len(conversation.messages)}"
            )
            return conversation
        except SQLAlchemyError as e:
            self.logger.error(f"Error cargando conversación desde MySQL: {e}")
            return None

    def find_all_by_user(self, user_id: str) -> List[Conversation]:
        """Busca todas las conversaciones de un usuario."""
        try:
            select_sql = text(
                """
                SELECT context_id
                FROM user_context
                WHERE user_id = :user_id
                ORDER BY last_updated DESC
                """
            )
            with self.engine.connect() as connection:
                rows = connection.execute(select_sql, {"user_id": user_id}).fetchall()

            conversations = []
            for row in rows:
                conversation = self.find_by_user_and_context(user_id, row[0])
                if conversation:
                    conversations.append(conversation)

            self.logger.info(f"Encontradas {len(conversations)} conversaciones para user={user_id}")
            return conversations
        except SQLAlchemyError as e:
            self.logger.error(f"Error obteniendo conversaciones de usuario {user_id}: {e}")
            return []

    def delete(self, conversation_id: str) -> bool:
        """Elimina una conversación."""
        try:
            if ':' in conversation_id:
                user_id, context_id = conversation_id.split(':', 1)
            else:
                user_id, context_id = conversation_id, "default"

            delete_sql = text(
                """
                DELETE FROM user_context
                WHERE user_id = :user_id AND context_id = :context_id
                """
            )
            with self.engine.begin() as connection:
                result = connection.execute(
                    delete_sql,
                    {"user_id": user_id, "context_id": context_id},
                )

            if result.rowcount and result.rowcount > 0:
                self.logger.info(f"Conversación eliminada: {conversation_id}")
                return True

            self.logger.warning(f"No se encontró conversación para eliminar: {conversation_id}")
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Error eliminando conversación {conversation_id}: {e}")
            return False

    def get_active_context_id(self, user_id: str) -> str:
        """Obtiene el context_id más reciente de un usuario."""
        try:
            select_sql = text(
                """
                SELECT context_id
                FROM user_context
                WHERE user_id = :user_id
                ORDER BY last_updated DESC
                LIMIT 1
                """
            )
            with self.engine.connect() as connection:
                row = connection.execute(select_sql, {"user_id": user_id}).first()

            if row and row[0]:
                return row[0]
            return "default"
        except SQLAlchemyError as e:
            self.logger.error(f"Error obteniendo context activo para user={user_id}: {e}")
            return "default"
