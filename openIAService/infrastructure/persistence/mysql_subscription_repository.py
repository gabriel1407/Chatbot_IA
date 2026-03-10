"""
infrastructure/persistence/mysql_subscription_repository.py

Gestiona las tablas subscription_plans y user_subscriptions.
Incluye seed automático de los 4 planes al arrancar.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from core.logging.logger import get_infrastructure_logger

logger = get_infrastructure_logger()

# ─── DDL ────────────────────────────────────────────────────────────────────

_CREATE_PLANS = text("""
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        name          VARCHAR(50)    NOT NULL,
        description   TEXT           NULL,
        price_usd     DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
        max_tenants   INT            NOT NULL DEFAULT 1,
        max_messages  INT            NULL,
        rag_enabled   TINYINT(1)     NOT NULL DEFAULT 0,
        web_search    TINYINT(1)     NOT NULL DEFAULT 0,
        is_active     TINYINT(1)     NOT NULL DEFAULT 1,
        created_at    DATETIME       NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")

_CREATE_SUBSCRIPTIONS = text("""
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        username   VARCHAR(100) NOT NULL,
        plan_id    INT          NOT NULL,
        status     ENUM('pending','active','cancelled','expired') NOT NULL DEFAULT 'pending',
        starts_at  DATETIME     NULL,
        expires_at DATETIME     NULL,
        created_at DATETIME     NOT NULL,
        INDEX idx_username (username),
        INDEX idx_status   (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")

_CREATE_PAYMENT_PROOFS = text("""
    CREATE TABLE IF NOT EXISTS payment_proofs (
        id                 INT AUTO_INCREMENT PRIMARY KEY,
        username           VARCHAR(100)   NOT NULL,
        plan_id            INT            NOT NULL,
        subscription_id    INT            NULL,
        image_path         VARCHAR(500)   NOT NULL,
        ai_analysis        JSON           NULL,
        amount_detected    DECIMAL(10,2)  NULL,
        currency_detected  VARCHAR(10)    NULL,
        reference_detected VARCHAR(100)   NULL,
        bank_detected      VARCHAR(100)   NULL,
        is_valid_proof     TINYINT(1)     NOT NULL DEFAULT 0,
        status             ENUM('pending','confirmed','rejected') NOT NULL DEFAULT 'pending',
        admin_note         TEXT           NULL,
        created_at         DATETIME       NOT NULL,
        reviewed_at        DATETIME       NULL,
        reviewed_by        VARCHAR(100)   NULL,
        INDEX idx_pp_username (username),
        INDEX idx_pp_status   (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")

# Planes predefinidos
_SEED_PLANS = [
    {
        "name": "Starter",
        "description": "Para pequeñas empresas. Incluye RAG para tu base de conocimiento.",
        "price_usd": 29.00,
        "max_tenants": 1,
        "max_messages": 5000,
        "rag_enabled": 1,
        "web_search": 0,
    },
    {
        "name": "Pro",
        "description": "Para empresas en crecimiento. Múltiples tenants, RAG y búsqueda web en tiempo real.",
        "price_usd": 79.00,
        "max_tenants": 3,
        "max_messages": 25000,
        "rag_enabled": 1,
        "web_search": 1,
    },
    {
        "name": "Enterprise",
        "description": "Sin límites. Tenants ilimitados, soporte dedicado y todas las funcionalidades.",
        "price_usd": 199.00,
        "max_tenants": 9999,
        "max_messages": None,
        "rag_enabled": 1,
        "web_search": 1,
    },
]


class SubscriptionRepository:
    """Repositorio para planes y suscripciones de usuarios."""

    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=2,
            max_overflow=3,
            future=True,
        )
        self._ensure_tables()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(_CREATE_PLANS)
            conn.execute(_CREATE_SUBSCRIPTIONS)
            conn.execute(_CREATE_PAYMENT_PROOFS)
        self._seed_plans()

    def _seed_plans(self) -> None:
        """Inserta los planes predefinidos si no existen."""
        sql_check = text("SELECT COUNT(*) FROM subscription_plans")
        sql_insert = text("""
            INSERT INTO subscription_plans
                (name, description, price_usd, max_tenants, max_messages,
                 rag_enabled, web_search, is_active, created_at)
            VALUES
                (:name, :description, :price_usd, :max_tenants, :max_messages,
                 :rag_enabled, :web_search, 1, :now)
        """)
        try:
            with self.engine.begin() as conn:
                count = conn.execute(sql_check).scalar()
                if count == 0:
                    now = datetime.now()
                    for plan in _SEED_PLANS:
                        conn.execute(sql_insert, {**plan, "now": now})
                    logger.info("[Subscription] Planes predefinidos insertados (Starter/Pro/Enterprise)")
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error en seed de planes: {e}")

    # ── Plans ─────────────────────────────────────────────────────────────────

    def list_plans(self, include_inactive: bool = False) -> List[dict]:
        """Lista todos los planes disponibles."""
        where = "" if include_inactive else "WHERE is_active = 1"
        sql = text(f"""
            SELECT id, name, description, price_usd, max_tenants, max_messages,
                   rag_enabled, web_search, is_active
            FROM subscription_plans {where}
            ORDER BY price_usd ASC
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(sql).mappings().all()
            return [self._plan_to_dict(r) for r in rows]
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error listando planes: {e}")
            return []

    def get_plan(self, plan_id: int) -> Optional[dict]:
        """Obtiene un plan por ID."""
        sql = text("""
            SELECT id, name, description, price_usd, max_tenants, max_messages,
                   rag_enabled, web_search, is_active
            FROM subscription_plans WHERE id = :id
        """)
        try:
            with self.engine.connect() as conn:
                row = conn.execute(sql, {"id": plan_id}).mappings().first()
            return self._plan_to_dict(row) if row else None
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error obteniendo plan {plan_id}: {e}")
            return None

    # ── User Subscriptions ────────────────────────────────────────────────────

    def get_user_subscription(self, username: str) -> Optional[dict]:
        """Obtiene la suscripción activa (o más reciente) de un usuario."""
        sql = text("""
            SELECT s.id, s.username, s.plan_id, s.status,
                   s.starts_at, s.expires_at, s.created_at,
                   p.name as plan_name, p.description as plan_description,
                   p.price_usd, p.max_tenants, p.max_messages,
                   p.rag_enabled, p.web_search
            FROM user_subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.username = :username
            ORDER BY 
                CASE s.status
                    WHEN 'active' THEN 1
                    WHEN 'pending' THEN 2
                    ELSE 99
                END ASC,
                s.created_at DESC
            LIMIT 1
        """)
        try:
            with self.engine.connect() as conn:
                row = conn.execute(sql, {"username": username}).mappings().first()
            return self._subscription_to_dict(row) if row else None
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error obteniendo suscripción de '{username}': {e}")
            return None

    def subscribe(self, username: str, plan_id: int) -> tuple[bool, str]:
        """
        Crea o actualiza la suscripción de un usuario.
        Si el plan es Free → activa directamente.
        Si es de pago → queda en estado 'pending' hasta confirmación de pago.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return False, "Plan no encontrado"

        # Cancelar suscripción previa si existe
        self._cancel_previous(username)

        is_free = float(plan["price_usd"]) == 0.0
        status = "active" if is_free else "pending"
        starts_at = datetime.now() if is_free else None

        sql = text("""
            INSERT INTO user_subscriptions
                (username, plan_id, status, starts_at, expires_at, created_at)
            VALUES
                (:username, :plan_id, :status, :starts_at, NULL, :now)
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(sql, {
                    "username": username,
                    "plan_id": plan_id,
                    "status": status,
                    "starts_at": starts_at,
                    "now": datetime.now(),
                })
            logger.info(f"[Subscription] '{username}' → plan '{plan['name']}' (status: {status})")
            return True, status
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error suscribiendo '{username}': {e}")
            return False, str(e)

    def activate(self, subscription_id: int) -> bool:
        """Activa una suscripción pendiente (tras confirmación de pago)."""
        sql = text("""
            UPDATE user_subscriptions
            SET status = 'active', starts_at = :now
            WHERE id = :id AND status = 'pending'
        """)
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"id": subscription_id, "now": datetime.now()})
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"[Subscription] Error activando suscripción {subscription_id}: {e}")
            return False

    def cancel(self, username: str) -> bool:
        """Cancela la suscripción activa del usuario."""
        return self._cancel_previous(username)

    def _cancel_previous(self, username: str) -> bool:
        sql_sub = text("""
            UPDATE user_subscriptions
            SET status = 'cancelled'
            WHERE username = :username AND status IN ('active', 'pending')
        """)
        sql_proof = text("""
            UPDATE payment_proofs
            SET status = 'cancelled'
            WHERE username = :username AND status = 'pending'
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(sql_sub, {"username": username})
                conn.execute(sql_proof, {"username": username})
            return True
        except SQLAlchemyError as err:
            logger.error(f"[Subscription] Error cancelando suscripciones de '{username}': {err}")
            return False

    # ── Payment Proofs ────────────────────────────────────────────────────────

    def create_payment_proof(self, username: str, plan_id: int,
                             image_path: str, analysis: dict,
                             subscription_id: int = None) -> int:
        """
        Guarda un comprobante de pago con el resultado del análisis de IA.
        Retorna el ID del comprobante creado.
        """
        import json as _json
        sql = text("""
            INSERT INTO payment_proofs
                (username, plan_id, subscription_id, image_path, ai_analysis,
                 amount_detected, currency_detected, reference_detected,
                 bank_detected, is_valid_proof, status, created_at)
            VALUES
                (:username, :plan_id, :sub_id, :image_path, :ai_analysis,
                 :amount, :currency, :reference,
                 :bank, :is_valid, 'pending', :now)
        """)
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {
                    "username":   username,
                    "plan_id":    plan_id,
                    "sub_id":     subscription_id,
                    "image_path": image_path,
                    "ai_analysis": _json.dumps(analysis),
                    "amount":     analysis.get("amount"),
                    "currency":   analysis.get("currency"),
                    "reference":  analysis.get("reference"),
                    "bank":       analysis.get("bank"),
                    "is_valid":   int(bool(analysis.get("is_valid_proof", False))),
                    "now":        datetime.now(),
                })
                return result.lastrowid
        except SQLAlchemyError as e:
            logger.error(f"[PaymentProof] Error guardando comprobante: {e}")
            return 0

    def get_pending_proofs(self) -> List[dict]:
        """Lista todos los comprobantes pendientes de revisión (admin)."""
        sql = text("""
            SELECT pp.id, pp.username, pp.plan_id, pp.subscription_id,
                   pp.amount_detected, pp.currency_detected, pp.reference_detected,
                   pp.bank_detected, pp.is_valid_proof, pp.status,
                   pp.created_at, pp.reviewed_at, pp.reviewed_by, pp.admin_note,
                   p.name as plan_name, p.price_usd
            FROM payment_proofs pp
            JOIN subscription_plans p ON p.id = pp.plan_id
            WHERE pp.status = 'pending'
            ORDER BY pp.created_at DESC
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(sql).mappings().all()
            return [self._proof_to_dict(r) for r in rows]
        except SQLAlchemyError as e:
            logger.error(f"[PaymentProof] Error listando comprobantes: {e}")
            return []

    def get_proof(self, proof_id: int) -> Optional[dict]:
        """Obtiene un comprobante por ID."""
        sql = text("""
            SELECT pp.*, p.name as plan_name, p.price_usd
            FROM payment_proofs pp
            JOIN subscription_plans p ON p.id = pp.plan_id
            WHERE pp.id = :id
        """)
        try:
            with self.engine.connect() as conn:
                row = conn.execute(sql, {"id": proof_id}).mappings().first()
            return self._proof_to_dict(row) if row else None
        except SQLAlchemyError as e:
            logger.error(f"[PaymentProof] Error obteniendo comprobante {proof_id}: {e}")
            return None

    def update_proof_status(self, proof_id: int, status: str,
                            reviewed_by: str, note: str = None) -> bool:
        """Actualiza el estado de un comprobante (confirmed/rejected)."""
        sql = text("""
            UPDATE payment_proofs
            SET status = :status, reviewed_by = :reviewed_by,
                reviewed_at = :now, admin_note = :note
            WHERE id = :id
        """)
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {
                    "id": proof_id, "status": status,
                    "reviewed_by": reviewed_by, "now": datetime.now(),
                    "note": note,
                })
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"[PaymentProof] Error actualizando comprobante {proof_id}: {e}")
            return False

    @staticmethod
    def _proof_to_dict(row) -> dict:
        r = dict(row)
        return {
            "id":                r["id"],
            "username":          r["username"],
            "plan_id":           r["plan_id"],
            "plan_name":         r.get("plan_name"),
            "price_usd":         float(r["price_usd"]) if r.get("price_usd") else None,
            "subscription_id":   r.get("subscription_id"),
            "amount_detected":   float(r["amount_detected"]) if r.get("amount_detected") else None,
            "currency_detected": r.get("currency_detected"),
            "reference_detected":r.get("reference_detected"),
            "bank_detected":     r.get("bank_detected"),
            "is_valid_proof":    bool(r.get("is_valid_proof", False)),
            "status":            r["status"],
            "admin_note":        r.get("admin_note"),
            "created_at":        r["created_at"].isoformat() if r.get("created_at") else None,
            "reviewed_at":       r["reviewed_at"].isoformat() if r.get("reviewed_at") else None,
            "reviewed_by":       r.get("reviewed_by"),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _plan_to_dict(row) -> dict:
        r = dict(row)
        return {
            "id":           r["id"],
            "name":         r["name"],
            "description":  r["description"],
            "price_usd":    float(r["price_usd"]),
            "max_tenants":  r["max_tenants"],
            "max_messages": r["max_messages"],
            "rag_enabled":  bool(r["rag_enabled"]),
            "web_search":   bool(r["web_search"]),
            "is_active":    bool(r["is_active"]),
        }

    @staticmethod
    def _subscription_to_dict(row) -> dict:
        r = dict(row)
        return {
            "id":         r["id"],
            "username":   r["username"],
            "plan_id":    r["plan_id"],
            "status":     r["status"],
            "starts_at":  r["starts_at"].isoformat() if r.get("starts_at") else None,
            "expires_at": r["expires_at"].isoformat() if r.get("expires_at") else None,
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "plan": {
                "id":           r["plan_id"],
                "name":         r["plan_name"],
                "description":  r.get("plan_description"),
                "price_usd":    float(r["price_usd"]),
                "max_tenants":  r["max_tenants"],
                "max_messages": r["max_messages"],
                "rag_enabled":  bool(r["rag_enabled"]),
                "web_search":   bool(r["web_search"]),
            },
        }
