"""
Repositorio MySQL para usuarios administradores.
Tabla: admin_users

Cada registro es un usuario que puede hacer login y recibir JWT para
llamar las APIs protegidas (/api/tenant, /api/v2, /api/rag).
"""
import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from core.logging.logger import get_infrastructure_logger

logger = get_infrastructure_logger()

_CREATE_TABLE = text("""
    CREATE TABLE IF NOT EXISTS admin_users (
        username      VARCHAR(100)  NOT NULL,
        password_hash VARCHAR(256)  NOT NULL,
        password_salt VARCHAR(64)   NOT NULL,
        role          VARCHAR(50)   NOT NULL DEFAULT 'admin',
        is_active     TINYINT(1)    NOT NULL DEFAULT 1,
        created_at    DATETIME      NOT NULL,
        last_login    DATETIME      NULL,
        PRIMARY KEY (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")


class AdminUserRepository:
    """Gestión de usuarios administradores con contraseñas hasheadas (PBKDF2-SHA256)."""

    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=2,
            max_overflow=3,
            future=True,
        )
        self._ensure_table()

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    def _ensure_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(_CREATE_TABLE)

    # ------------------------------------------------------------------ #
    # Seguridad de contraseñas                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """PBKDF2-HMAC-SHA256 con 260 000 iteraciones."""
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=260_000,
        )
        return dk.hex()

    @staticmethod
    def _generate_salt() -> str:
        return secrets.token_hex(32)

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def create_user(self, username: str, password: str, role: str = "admin") -> bool:
        """
        Crea un nuevo usuario admin.
        Retorna False si el username ya existe.
        """
        salt = self._generate_salt()
        pw_hash = self._hash_password(password, salt)
        now = datetime.now()

        sql = text("""
            INSERT IGNORE INTO admin_users
                (username, password_hash, password_salt, role, is_active, created_at)
            VALUES
                (:username, :pw_hash, :salt, :role, 1, :now)
        """)
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {
                    "username": username,
                    "pw_hash": pw_hash,
                    "salt": salt,
                    "role": role,
                    "now": now,
                })
            created = result.rowcount > 0
            if created:
                logger.info(f"[AdminUser] Usuario '{username}' creado con rol '{role}'")
            else:
                logger.warning(f"[AdminUser] Usuario '{username}' ya existe, no se creó")
            return created
        except SQLAlchemyError as e:
            logger.error(f"[AdminUser] Error creando usuario '{username}': {e}")
            return False

    def verify_password(self, username: str, password: str) -> Optional[dict]:
        """
        Verifica credenciales.
        Retorna el registro del usuario (dict) si son correctas, o None.
        Actualiza last_login si el login es exitoso.
        """
        sql = text("""
            SELECT username, password_hash, password_salt, role, is_active
            FROM admin_users
            WHERE username = :username
        """)
        try:
            with self.engine.connect() as conn:
                row = conn.execute(sql, {"username": username}).mappings().first()
        except SQLAlchemyError as e:
            logger.error(f"[AdminUser] Error consultando usuario '{username}': {e}")
            return None

        if row is None:
            return None

        row = dict(row)
        if not row["is_active"]:
            logger.warning(f"[AdminUser] Usuario '{username}' está inactivo")
            return None

        expected_hash = self._hash_password(password, row["password_salt"])
        if not secrets.compare_digest(expected_hash, row["password_hash"]):
            return None

        # Actualizar last_login en background sin bloquear
        self._update_last_login(username)
        return {"username": row["username"], "role": row["role"]}

    def _update_last_login(self, username: str) -> None:
        sql = text("UPDATE admin_users SET last_login = :now WHERE username = :username")
        try:
            with self.engine.begin() as conn:
                conn.execute(sql, {"now": datetime.now(), "username": username})
        except SQLAlchemyError:
            pass  # No crítico

    def list_users(self) -> List[dict]:
        sql = text("""
            SELECT username, role, is_active, created_at, last_login
            FROM admin_users ORDER BY username
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(sql).mappings().all()
            return [dict(r) for r in rows]
        except SQLAlchemyError as e:
            logger.error(f"[AdminUser] Error listando usuarios: {e}")
            return []

    def set_active(self, username: str, is_active: bool) -> bool:
        sql = text("UPDATE admin_users SET is_active = :active WHERE username = :username")
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"active": int(is_active), "username": username})
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"[AdminUser] Error actualizando estado de '{username}': {e}")
            return False

    def change_password(self, username: str, new_password: str) -> bool:
        salt = self._generate_salt()
        pw_hash = self._hash_password(new_password, salt)
        sql = text("""
            UPDATE admin_users
            SET password_hash = :pw_hash, password_salt = :salt
            WHERE username = :username
        """)
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"pw_hash": pw_hash, "salt": salt, "username": username})
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"[AdminUser] Error cambiando contraseña de '{username}': {e}")
            return False

    def ensure_default_admin(self, default_password: str) -> None:
        """
        Crea el usuario 'admin' con la contraseña dada si no existe ningún usuario.
        Se llama al arrancar la app para garantizar que siempre haya un admin.
        """
        try:
            users = self.list_users()
            if not users:
                created = self.create_user("admin", default_password, role="admin")
                if created:
                    logger.info(
                        "[AdminUser] Usuario 'admin' inicial creado. "
                        "¡Cambia la contraseña con PATCH /api/auth/me/password!"
                    )
        except Exception as e:
            logger.warning(f"[AdminUser] No se pudo verificar admin inicial: {e}")
