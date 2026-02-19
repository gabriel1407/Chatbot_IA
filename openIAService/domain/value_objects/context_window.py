"""
Value Object ContextWindow - Gestiona la ventana de contexto para LLM.
Inmutable y con lógica de negocio para gestión de tokens.
"""
from dataclasses import dataclass
from typing import List, Optional
from domain.entities.message import Message


@dataclass(frozen=True)
class ContextWindow:
    """
    Value Object que representa una ventana de contexto optimizada.
    
    Attributes:
        messages: Lista de mensajes en la ventana
        max_tokens: Límite máximo de tokens
        current_tokens: Tokens actuales estimados
    """
    messages: tuple  # Inmutable
    max_tokens: int
    current_tokens: int
    
    def __post_init__(self):
        """Validaciones."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens debe ser mayor a 0")
        
        if self.current_tokens < 0:
            raise ValueError("current_tokens no puede ser negativo")
        
        if self.current_tokens > self.max_tokens:
            raise ValueError("current_tokens excede max_tokens")
    
    @classmethod
    def create(
        cls,
        messages: List[Message],
        max_tokens: int = 4000,
        token_estimator=None
    ) -> 'ContextWindow':
        """
        Factory method para crear una ventana de contexto.
        
        Args:
            messages: Lista de mensajes
            max_tokens: Límite máximo de tokens
            token_estimator: Función para estimar tokens (opcional)
            
        Returns:
            Nueva instancia de ContextWindow
        """
        if token_estimator is None:
            # Estimación simple: ~4 caracteres por token
            token_estimator = lambda msg: len(msg.content) // 4
        
        current_tokens = sum(token_estimator(msg) for msg in messages)
        
        return cls(
            messages=tuple(messages),
            max_tokens=max_tokens,
            current_tokens=current_tokens
        )
    
    def is_full(self) -> bool:
        """Verifica si la ventana está llena."""
        return self.current_tokens >= self.max_tokens
    
    def get_available_tokens(self) -> int:
        """Retorna los tokens disponibles."""
        return max(0, self.max_tokens - self.current_tokens)
    
    def get_usage_percentage(self) -> float:
        """Retorna el porcentaje de uso de la ventana."""
        return (self.current_tokens / self.max_tokens) * 100
    
    def needs_truncation(self) -> bool:
        """Verifica si necesita truncamiento."""
        return self.current_tokens > self.max_tokens
    
    def to_dict(self) -> dict:
        """Convierte a dict para logging/debugging."""
        return {
            "message_count": len(self.messages),
            "max_tokens": self.max_tokens,
            "current_tokens": self.current_tokens,
            "available_tokens": self.get_available_tokens(),
            "usage_percentage": round(self.get_usage_percentage(), 2),
            "needs_truncation": self.needs_truncation()
        }
