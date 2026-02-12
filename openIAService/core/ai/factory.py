"""
Fábrica para obtener el proveedor de IA configurado.
"""
from typing import Optional

from core.ai.providers import AIProvider
from core.config.settings import settings
from infrastructure.ai.openai_adapter import OpenAIAdapter
from infrastructure.ai.gemini_adapter import GeminiAdapter
from infrastructure.ai.ollama_adapter import OllamaAdapter


def get_ai_provider() -> AIProvider:
    """Devuelve una instancia de `AIProvider` según la configuración.

    - Lee `settings.ai_provider` y crea el adaptador correspondiente.
    - Por defecto devuelve `OpenAIAdapter`.
    """
    provider = (settings.ai_provider or "openai").lower()
    if provider == "openai":
        return OpenAIAdapter(settings)
    if provider == "gemini":
        return GeminiAdapter(settings)
    if provider == "ollama":
        return OllamaAdapter(settings)

    # Fallback
    return OpenAIAdapter(settings)
