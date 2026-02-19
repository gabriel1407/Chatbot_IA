"""
Definición de la interfaz para proveedores de IA.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List


@dataclass(frozen=True)
class AIStreamChunk:
    """Chunk estandarizado para respuestas en streaming."""

    content: str = ""
    thinking: str = ""
    done: bool = False
    raw: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "thinking": self.thinking,
            "done": self.done,
        }


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

    def supports_streaming(self) -> bool:
        """Indica si el proveedor soporta streaming nativo."""
        return False

    def supports_thinking(self) -> bool:
        """Indica si el proveedor soporta campo de razonamiento (thinking)."""
        return False

    def generate_text_stream(self, prompt: str, **kwargs) -> Iterator[AIStreamChunk]:
        """Fallback de streaming: produce un único chunk con la respuesta completa."""
        text = self.generate_text(prompt=prompt, **kwargs)
        yield AIStreamChunk(content=text, done=True)

    def generate_text_with_thinking(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Fallback para thinking: devuelve respuesta sin traza de razonamiento."""
        text = self.generate_text(prompt=prompt, **kwargs)
        return {
            "content": text,
            "thinking": "",
            "model": kwargs.get("model"),
            "provider_supports_thinking": False,
        }
