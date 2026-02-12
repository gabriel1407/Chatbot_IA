"""
Adaptador para OpenAI con cliente v1+.
"""
from typing import List
from openai import OpenAI

from core.ai.providers import AIProvider
from core.config.settings import settings


class OpenAIAdapter(AIProvider):
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Genera texto usando la API de OpenAI v1+ con ChatCompletion."""
        model = kwargs.get("model", self.settings.openai_model)
        max_tokens = kwargs.get("max_tokens", self.settings.openai_max_tokens)
        temperature = kwargs.get("temperature", self.settings.openai_temperature)

        # Soportar mensajes compuestos (system + user) si se pasan
        messages = kwargs.get("messages")
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Con el cliente v1+, la estructura es: resp.choices[0].message.content
        return resp.choices[0].message.content

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = getattr(self.settings, "openai_embedding_model", "text-embedding-3-small")
        resp = self.client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in resp.data]
