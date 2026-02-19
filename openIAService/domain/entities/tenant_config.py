"""
TenantConfig Entity - Configuración del bot por cliente/empresa.
Centraliza toda la personalización que antes vivía en .env
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TenantConfig:
    """
    Configuración de un tenant (empresa/cliente).
    Un tenant = una empresa que contrata el servicio del bot.
    """
    tenant_id: str                          # Identificador único del cliente (ej: "ferreteria_lopez")

    # --- Identidad del bot ---
    bot_name: str = "Asistente Virtual"
    bot_persona: str = (                    # System prompt principal
        "Eres un asistente virtual amigable y útil. "
        "Responde de forma clara, concisa y profesional. "
        "Si no sabes la respuesta a algo, dilo honestamente."
    )
    welcome_message: str = "¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
    language: str = "es"                    # Idioma principal: es, en, pt...
    out_of_scope_message: Optional[str] = None  # Mensaje cuando la pregunta sale del dominio

    # --- Proveedor IA ---
    ai_provider: Optional[str] = None       # None = usa el del .env global; o "openai"/"gemini"/"ollama"
    ai_model: Optional[str] = None          # None = usa el del proveedor por defecto

    # --- RAG ---
    rag_enabled: bool = True
    rag_top_k: int = 5
    rag_min_similarity: float = 0.3

    # --- Comportamiento ---
    max_response_tokens: int = 600
    temperature: float = 0.7
    web_search_enabled: bool = False        # Búsqueda web activa para este tenant

    # --- Estado ---
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_full_system_prompt(self) -> str:
        """
        Construye el system prompt completo combinando persona + regla de identidad.
        """
        identity_rule = (
            "Regla obligatoria: eres un asistente virtual de IA. "
            "Nunca afirmes ser una persona real. "
            f"Tu nombre es {self.bot_name}."
        )
        out_of_scope = ""
        if self.out_of_scope_message:
            out_of_scope = f"\nSi el usuario pregunta algo fuera de tu dominio, responde: '{self.out_of_scope_message}'"

        return f"{self.bot_persona}\n\n{identity_rule}{out_of_scope}"

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "bot_name": self.bot_name,
            "bot_persona": self.bot_persona,
            "welcome_message": self.welcome_message,
            "language": self.language,
            "out_of_scope_message": self.out_of_scope_message,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "rag_enabled": self.rag_enabled,
            "rag_top_k": self.rag_top_k,
            "rag_min_similarity": self.rag_min_similarity,
            "max_response_tokens": self.max_response_tokens,
            "temperature": self.temperature,
            "web_search_enabled": self.web_search_enabled,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TenantConfig":
        created = data.get("created_at")
        updated = data.get("updated_at")
        return cls(
            tenant_id=data["tenant_id"],
            bot_name=data.get("bot_name", "Asistente Virtual"),
            bot_persona=data.get("bot_persona", cls.__dataclass_fields__["bot_persona"].default),
            welcome_message=data.get("welcome_message", "¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"),
            language=data.get("language", "es"),
            out_of_scope_message=data.get("out_of_scope_message"),
            ai_provider=data.get("ai_provider"),
            ai_model=data.get("ai_model"),
            rag_enabled=bool(data.get("rag_enabled", True)),
            rag_top_k=int(data.get("rag_top_k", 5)),
            rag_min_similarity=float(data.get("rag_min_similarity", 0.3)),
            max_response_tokens=int(data.get("max_response_tokens", 600)),
            temperature=float(data.get("temperature", 0.7)),
            web_search_enabled=bool(data.get("web_search_enabled", False)),
            is_active=bool(data.get("is_active", True)),
            created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
            updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
        )
