"""
DTOs para requests de capacidades de IA (streaming/thinking).
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union


AllowedThinkType = Union[bool, str, None]
_GPT_OSS_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class OllamaGenerationRequest:
    prompt: str
    model: Optional[str]
    temperature: float
    max_tokens: int
    think: AllowedThinkType
    stream: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OllamaGenerationRequest":
        if not isinstance(data, dict):
            raise ValueError("No se proporcionaron datos JSON válidos")

        prompt = str(data.get("prompt", "")).strip()
        model = str(data.get("model", "")).strip() or None
        stream = bool(data.get("stream", False))

        try:
            temperature = float(data.get("temperature", 0.7))
        except (TypeError, ValueError):
            raise ValueError("temperature debe ser numérico")

        try:
            max_tokens = int(data.get("max_tokens", 512))
        except (TypeError, ValueError):
            raise ValueError("max_tokens debe ser entero")

        if not prompt:
            raise ValueError("Campo requerido faltante: prompt")
        if max_tokens <= 0:
            raise ValueError("max_tokens debe ser mayor que cero")

        think = data.get("think", None)
        if think is not None:
            if isinstance(think, bool):
                pass
            elif isinstance(think, str):
                normalized = think.strip().lower()
                if not normalized:
                    think = None
                elif normalized not in _GPT_OSS_LEVELS:
                    raise ValueError("think string inválido. Usa: low, medium, high")
                else:
                    think = normalized
            else:
                raise ValueError("think debe ser booleano, string (low|medium|high) o null")

        return cls(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            think=think,
            stream=stream,
        )
