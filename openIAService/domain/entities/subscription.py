"""
domain/entities/subscription.py
Entidades de dominio para planes y suscripciones de usuarios.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SubscriptionStatus(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    CANCELLED = "cancelled"
    EXPIRED   = "expired"


@dataclass
class SubscriptionPlan:
    """Define un plan de suscripción disponible."""
    id:             int
    name:           str          # 'Free', 'Starter', 'Pro', 'Enterprise'
    price_usd:      float
    max_tenants:    int          # Número máximo de tenants
    max_messages:   Optional[int]  # None = ilimitado
    rag_enabled:    bool
    web_search:     bool
    description:    str = ""
    is_active:      bool = True
    created_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "name":          self.name,
            "price_usd":     float(self.price_usd),
            "max_tenants":   self.max_tenants,
            "max_messages":  self.max_messages,
            "rag_enabled":   self.rag_enabled,
            "web_search":    self.web_search,
            "description":   self.description,
            "is_active":     self.is_active,
        }


@dataclass
class UserSubscription:
    """Suscripción activa de un usuario a un plan."""
    id:         int
    username:   str
    plan_id:    int
    status:     SubscriptionStatus
    starts_at:  Optional[datetime]
    expires_at: Optional[datetime]  # None = sin expiración
    created_at: datetime = field(default_factory=datetime.now)
    plan:       Optional[SubscriptionPlan] = None  # join opcional

    def is_active(self) -> bool:
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "username":   self.username,
            "plan_id":    self.plan_id,
            "status":     self.status.value,
            "starts_at":  self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "plan":       self.plan.to_dict() if self.plan else None,
        }
