"""
MySQL implementation of TenantConfigRepository.
Persiste la configuración del bot por tenant en la tabla tenant_config.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.tenant_config import TenantConfig
from domain.repositories.tenant_config_repository import TenantConfigRepository
from core.logging.logger import get_infrastructure_logger


_CREATE_TABLE_SQL = text("""
    CREATE TABLE IF NOT EXISTS tenant_config (
        tenant_id          VARCHAR(100)  NOT NULL,
        bot_name           VARCHAR(150)  NOT NULL DEFAULT 'Asistente Virtual',
        bot_persona        TEXT          NOT NULL,
        welcome_message    TEXT          NOT NULL,
        language           VARCHAR(10)   NOT NULL DEFAULT 'es',
        out_of_scope_msg   TEXT          NULL,
        ai_provider        VARCHAR(50)   NULL,
        ai_model           VARCHAR(100)  NULL,
        rag_enabled        TINYINT(1)    NOT NULL DEFAULT 1,
        rag_top_k          INT           NOT NULL DEFAULT 5,
        rag_min_similarity FLOAT         NOT NULL DEFAULT 0.3,
        max_response_tokens INT          NOT NULL DEFAULT 600,
        temperature        FLOAT         NOT NULL DEFAULT 0.7,
        web_search_enabled TINYINT(1)   NOT NULL DEFAULT 0,
        is_active          TINYINT(1)    NOT NULL DEFAULT 1,
        created_at         DATETIME      NOT NULL,
        updated_at         DATETIME      NOT NULL,
        PRIMARY KEY (tenant_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")

_UPSERT_SQL = text("""
    INSERT INTO tenant_config
        (tenant_id, bot_name, bot_persona, welcome_message, language,
         out_of_scope_msg, ai_provider, ai_model,
         rag_enabled, rag_top_k, rag_min_similarity,
         max_response_tokens, temperature, web_search_enabled,
         is_active, created_at, updated_at)
    VALUES
        (:tenant_id, :bot_name, :bot_persona, :welcome_message, :language,
         :out_of_scope_msg, :ai_provider, :ai_model,
         :rag_enabled, :rag_top_k, :rag_min_similarity,
         :max_response_tokens, :temperature, :web_search_enabled,
         :is_active, :created_at, :updated_at)
    ON DUPLICATE KEY UPDATE
        bot_name           = VALUES(bot_name),
        bot_persona        = VALUES(bot_persona),
        welcome_message    = VALUES(welcome_message),
        language           = VALUES(language),
        out_of_scope_msg   = VALUES(out_of_scope_msg),
        ai_provider        = VALUES(ai_provider),
        ai_model           = VALUES(ai_model),
        rag_enabled        = VALUES(rag_enabled),
        rag_top_k          = VALUES(rag_top_k),
        rag_min_similarity = VALUES(rag_min_similarity),
        max_response_tokens = VALUES(max_response_tokens),
        temperature        = VALUES(temperature),
        web_search_enabled = VALUES(web_search_enabled),
        is_active          = VALUES(is_active),
        updated_at         = VALUES(updated_at)
""")


class MySQLTenantConfigRepository(TenantConfigRepository):
    """Repositorio MySQL para configuración de tenants."""

    def __init__(self, database_url: str):
        self.logger = get_infrastructure_logger()
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=3,
            max_overflow=5,
            future=True,
        )
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    # ------------------------------------------------------------------
    def save(self, config: TenantConfig) -> TenantConfig:
        now = datetime.now()
        if config.created_at is None:
            config.created_at = now
        config.updated_at = now

        params = {
            "tenant_id":           config.tenant_id,
            "bot_name":            config.bot_name,
            "bot_persona":         config.bot_persona,
            "welcome_message":     config.welcome_message,
            "language":            config.language,
            "out_of_scope_msg":    config.out_of_scope_message,
            "ai_provider":         config.ai_provider,
            "ai_model":            config.ai_model,
            "rag_enabled":         int(config.rag_enabled),
            "rag_top_k":           config.rag_top_k,
            "rag_min_similarity":  config.rag_min_similarity,
            "max_response_tokens": config.max_response_tokens,
            "temperature":         config.temperature,
            "web_search_enabled":  int(config.web_search_enabled),
            "is_active":           int(config.is_active),
            "created_at":          config.created_at,
            "updated_at":          config.updated_at,
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(_UPSERT_SQL, params)
            self.logger.info(f"[TenantConfig] Guardado tenant_id={config.tenant_id}")
            return config
        except SQLAlchemyError as e:
            self.logger.error(f"[TenantConfig] Error guardando {config.tenant_id}: {e}")
            raise

    def find_by_id(self, tenant_id: str) -> Optional[TenantConfig]:
        sql = text("SELECT * FROM tenant_config WHERE tenant_id = :tid")
        try:
            with self.engine.connect() as conn:
                row = conn.execute(sql, {"tid": tenant_id}).mappings().first()
            if row is None:
                return None
            return self._row_to_entity(dict(row))
        except SQLAlchemyError as e:
            self.logger.error(f"[TenantConfig] Error buscando {tenant_id}: {e}")
            return None

    def find_all(self) -> List[TenantConfig]:
        sql = text("SELECT * FROM tenant_config ORDER BY tenant_id")
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(sql).mappings().all()
            return [self._row_to_entity(dict(r)) for r in rows]
        except SQLAlchemyError as e:
            self.logger.error(f"[TenantConfig] Error listando tenants: {e}")
            return []

    def delete(self, tenant_id: str) -> bool:
        sql = text("DELETE FROM tenant_config WHERE tenant_id = :tid")
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"tid": tenant_id})
            deleted = result.rowcount > 0
            if deleted:
                self.logger.info(f"[TenantConfig] Eliminado tenant_id={tenant_id}")
            return deleted
        except SQLAlchemyError as e:
            self.logger.error(f"[TenantConfig] Error eliminando {tenant_id}: {e}")
            return False

    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_entity(row: dict) -> TenantConfig:
        return TenantConfig(
            tenant_id=row["tenant_id"],
            bot_name=row["bot_name"],
            bot_persona=row["bot_persona"],
            welcome_message=row["welcome_message"],
            language=row["language"],
            out_of_scope_message=row.get("out_of_scope_msg"),
            ai_provider=row.get("ai_provider"),
            ai_model=row.get("ai_model"),
            rag_enabled=bool(row["rag_enabled"]),
            rag_top_k=int(row["rag_top_k"]),
            rag_min_similarity=float(row["rag_min_similarity"]),
            max_response_tokens=int(row["max_response_tokens"]),
            temperature=float(row["temperature"]),
            web_search_enabled=bool(row["web_search_enabled"]),
            is_active=bool(row["is_active"]),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
