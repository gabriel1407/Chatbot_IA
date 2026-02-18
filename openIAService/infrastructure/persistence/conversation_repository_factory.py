"""
Factory para crear repositorios de conversaciones según configuración.
"""
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
from infrastructure.persistence.sqlite_conversation_repository import SQLiteConversationRepository
from infrastructure.persistence.mysql_conversation_repository import MySQLConversationRepository


logger = get_infrastructure_logger()


def create_conversation_repository(db_path: str | None = None):
    """
    Crea la implementación de ConversationRepository adecuada.

    Prioridad:
    1) DATABASE_URL (si existe y es MySQL)
    2) SQLite con db_path recibido
    3) SQLite con settings.db_path
    """
    database_url = getattr(settings, "database_url", None)

    if database_url and database_url.lower().startswith("mysql"):
        logger.info("Usando MySQLConversationRepository")
        return MySQLConversationRepository(database_url=database_url)

    effective_db_path = db_path or settings.db_path
    logger.info(f"Usando SQLiteConversationRepository con db_path={effective_db_path}")
    return SQLiteConversationRepository(effective_db_path)
