"""
Value Object SearchQuery - Representa una consulta de búsqueda semántica.
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class SearchQuery:
    """
    Value Object que representa una consulta de búsqueda.
    
    Attributes:
        query_text: Texto de la consulta
        top_k: Número de resultados a retornar
        filters: Filtros adicionales (user_id, document_type, etc.)
        min_similarity: Similitud mínima requerida (0-1)
    """
    query_text: str
    top_k: int = 5
    filters: Optional[dict] = None
    min_similarity: float = 0.7
    
    def __post_init__(self):
        """Validaciones."""
        if not self.query_text or not self.query_text.strip():
            raise ValueError("query_text no puede estar vacío")
        
        if self.top_k <= 0:
            raise ValueError("top_k debe ser mayor a 0")
        
        if not 0 <= self.min_similarity <= 1:
            raise ValueError("min_similarity debe estar entre 0 y 1")
    
    def get_normalized_query(self) -> str:
        """Retorna la consulta normalizada (sin espacios extras)."""
        return " ".join(self.query_text.split())
    
    def to_dict(self) -> dict:
        """Convierte a dict."""
        return {
            "query_text": self.query_text,
            "top_k": self.top_k,
            "filters": self.filters,
            "min_similarity": self.min_similarity
        }
