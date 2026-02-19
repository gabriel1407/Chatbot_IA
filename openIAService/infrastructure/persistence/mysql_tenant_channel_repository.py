"""
MySQLTenantChannelRepository - Implementación MySQL del repositorio de canales.
Tabla: tenant_channels
"""
from typing import List, Optional
from datetime import datetime

from core.logging.logger import get_infrastructure_logger
from domain.entities.tenant_channel import TenantChannel
from domain.repositories.tenant_channel_repository import TenantChannelRepository


class MySQLTenantChannelRepository(TenantChannelRepository):

    def __init__(self, db_url: str):
        self._db_url = db_url
        self._logger = get_infrastructure_logger()
        self._ensure_table()

    # ------------------------------------------------------------------ #
    # Tabla                                                                #
    # ------------------------------------------------------------------ #

    def _get_connection(self):
        from sqlalchemy import create_engine
        engine = create_engine(self._db_url, pool_pre_ping=True)
        return engine.connect()

    def _ensure_table(self):
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tenant_channels (
                        tenant_id         VARCHAR(100) NOT NULL,
                        channel           VARCHAR(30)  NOT NULL,
                        token             TEXT         NOT NULL,
                        is_active         TINYINT(1)   NOT NULL DEFAULT 1,
                        phone_number_id   VARCHAR(100) NULL,
                        verify_token      VARCHAR(200) NULL,
                        bot_username      VARCHAR(100) NULL,
                        display_name      VARCHAR(200) NULL,
                        created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (tenant_id, channel),
                        INDEX idx_phone_number_id (phone_number_id),
                        INDEX idx_is_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """))
                conn.commit()
            self._logger.info("Tabla tenant_channels lista")
        except Exception as e:
            self._logger.error(f"Error creando tabla tenant_channels: {e}")
            raise

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _row_to_entity(self, row) -> TenantChannel:
        if hasattr(row, '_mapping'):
            r = dict(row._mapping)
        else:
            r = dict(row)
        return TenantChannel(
            tenant_id=r["tenant_id"],
            channel=r["channel"],
            token=r["token"],
            is_active=bool(r.get("is_active", True)),
            phone_number_id=r.get("phone_number_id"),
            verify_token=r.get("verify_token"),
            bot_username=r.get("bot_username"),
            display_name=r.get("display_name"),
            created_at=r.get("created_at") or datetime.now(),
            updated_at=r.get("updated_at") or datetime.now(),
        )

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def save(self, channel: TenantChannel) -> TenantChannel:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO tenant_channels
                        (tenant_id, channel, token, is_active, phone_number_id,
                         verify_token, bot_username, display_name)
                    VALUES
                        (:tenant_id, :channel, :token, :is_active, :phone_number_id,
                         :verify_token, :bot_username, :display_name)
                    ON DUPLICATE KEY UPDATE
                        token           = VALUES(token),
                        is_active       = VALUES(is_active),
                        phone_number_id = VALUES(phone_number_id),
                        verify_token    = VALUES(verify_token),
                        bot_username    = VALUES(bot_username),
                        display_name    = VALUES(display_name),
                        updated_at      = CURRENT_TIMESTAMP
                """), {
                    "tenant_id": channel.tenant_id,
                    "channel": channel.channel,
                    "token": channel.token,
                    "is_active": int(channel.is_active),
                    "phone_number_id": channel.phone_number_id,
                    "verify_token": channel.verify_token,
                    "bot_username": channel.bot_username,
                    "display_name": channel.display_name,
                })
                conn.commit()
            self._logger.info(f"Canal guardado: tenant={channel.tenant_id} channel={channel.channel}")
            return channel
        except Exception as e:
            self._logger.error(f"Error guardando canal: {e}")
            raise

    def find_by_tenant_and_channel(self, tenant_id: str, channel: str) -> Optional[TenantChannel]:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT * FROM tenant_channels
                    WHERE tenant_id = :tenant_id AND channel = :channel AND is_active = 1
                """), {"tenant_id": tenant_id, "channel": channel}).fetchone()
            return self._row_to_entity(row) if row else None
        except Exception as e:
            self._logger.error(f"Error buscando canal {channel} para tenant {tenant_id}: {e}")
            return None

    def find_by_phone_number_id(self, phone_number_id: str) -> Optional[TenantChannel]:
        """Lookup rápido para routing de webhooks WhatsApp entrantes."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT * FROM tenant_channels
                    WHERE phone_number_id = :phone_number_id AND is_active = 1
                    LIMIT 1
                """), {"phone_number_id": phone_number_id}).fetchone()
            return self._row_to_entity(row) if row else None
        except Exception as e:
            self._logger.error(f"Error buscando tenant por phone_number_id {phone_number_id}: {e}")
            return None

    def find_by_tenant_id(self, tenant_id: str) -> List[TenantChannel]:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT * FROM tenant_channels
                    WHERE tenant_id = :tenant_id AND is_active = 1
                """), {"tenant_id": tenant_id}).fetchall()
            return [self._row_to_entity(r) for r in rows]
        except Exception as e:
            self._logger.error(f"Error listando canales del tenant {tenant_id}: {e}")
            return []

    def find_all_active(self) -> List[TenantChannel]:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT * FROM tenant_channels WHERE is_active = 1"
                )).fetchall()
            return [self._row_to_entity(r) for r in rows]
        except Exception as e:
            self._logger.error(f"Error listando todos los canales activos: {e}")
            return []

    def delete(self, tenant_id: str, channel: str) -> bool:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE tenant_channels SET is_active = 0
                    WHERE tenant_id = :tenant_id AND channel = :channel
                """), {"tenant_id": tenant_id, "channel": channel})
                conn.commit()
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando canal {channel} del tenant {tenant_id}: {e}")
            return False
