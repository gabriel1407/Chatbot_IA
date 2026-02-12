"""
Definición de la interfaz para proveedores de IA.
"""
from abc import ABC, abstractmethod
from typing import List, Any


class AIProvider(ABC):
    """Interfaz mínima que deben implementar los adaptadores de proveedores IA.
    Mantener esta interfaz pequeña y orientada a los casos de uso del proyecto.
    """

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Genera una respuesta de texto a partir de un prompt."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Devuelve embeddings para una lista de textos."""
