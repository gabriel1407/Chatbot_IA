"""
Adaptador para Ollama usando la librería oficial de Python.
Soporta autenticación mediante API key para endpoints cloud.
"""
from typing import Any, Dict, Iterator, List, Optional, Union
import ollama
from ollama import Client

from core.ai.providers import AIProvider, AIStreamChunk
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger


class OllamaAdapter(AIProvider):
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.logger = get_infrastructure_logger()
        
        # Get configuration from settings
        self.host = self.settings.ollama_url or "http://localhost:11434"
        self.api_key = getattr(self.settings, "ollama_api_key", None)
        self.model = getattr(self.settings, "ollama_model", "llama2")
        
        # Initialize Ollama client with optional authentication
        client_kwargs = {"host": self.host}
        if self.api_key:
            client_kwargs["headers"] = {"Authorization": f"Bearer {self.api_key}"}
        
        self.client = Client(**client_kwargs)
        self.logger.info(f"Ollama adapter initialized: host={self.host}, model={self.model}, auth={'yes' if self.api_key else 'no'}")

    def supports_streaming(self) -> bool:
        return True

    def supports_thinking(self) -> bool:
        return True

    @staticmethod
    def _is_gpt_oss_model(model_name: str) -> bool:
        normalized = (model_name or "").strip().lower()
        return normalized.startswith("gpt-oss")

    def _normalize_think_value(
        self,
        *,
        model_name: str,
        think: Optional[Union[bool, str]],
    ) -> Optional[Union[bool, str]]:
        """Normaliza el parámetro think según modelo (nota especial para GPT-OSS)."""
        if think is None:
            return None

        is_gpt_oss = self._is_gpt_oss_model(model_name)
        if is_gpt_oss:
            if isinstance(think, bool):
                level = "medium" if think else "low"
                self.logger.info("GPT-OSS requiere think por niveles; mapeando booleano a '%s'", level)
                return level

            level = str(think).strip().lower()
            if level not in {"low", "medium", "high"}:
                self.logger.warning("think='%s' inválido para GPT-OSS; usando 'medium'", think)
                return "medium"
            return level

        if isinstance(think, str):
            level = think.strip().lower()
            if level in {"low", "medium", "high"}:
                return True
            if level in {"true", "false"}:
                return level == "true"
            return None

        return think

    @staticmethod
    def _extract_message_field(chunk: Any, field_name: str) -> str:
        if isinstance(chunk, dict):
            message = chunk.get("message", {})
            return str(message.get(field_name, "") or "")

        message = getattr(chunk, "message", None)
        if message is None:
            return ""
        return str(getattr(message, field_name, "") or "")

    @staticmethod
    def _extract_done(chunk: Any) -> bool:
        if isinstance(chunk, dict):
            return bool(chunk.get("done", False))
        return bool(getattr(chunk, "done", False))

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Ollama's official library with chat endpoint."""
        try:
            model = kwargs.get("model", self.model)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 512)
            think = self._normalize_think_value(model_name=model, think=kwargs.get("think"))
            
            # Build messages array
            messages = kwargs.get("messages")
            if messages:
                # Use provided messages directly
                chat_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
            else:
                # Convert prompt to message format
                chat_messages = [{"role": "user", "content": prompt}]
            
            self.logger.debug(f"Ollama request with model {model}, {len(chat_messages)} messages")

            # Call Ollama chat endpoint
            try:
                response = self.client.chat(
                    model=model,
                    messages=chat_messages,
                    stream=False,
                    think=think,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                )
                
                # Extract response text
                text = response.get("message", {}).get("content", "").strip()
                if not text:
                    self.logger.warning(f"Ollama returned empty response: {response}")
                    return "Error: Respuesta vacía del modelo."
                    
                return text
                
            except ollama.ResponseError as exc:
                self.logger.error(f"Ollama API error: {exc}")
                raise RuntimeError(f"Ollama error: {exc}")
            except Exception as exc:
                self.logger.error(f"Ollama client error: {exc}")
                raise RuntimeError(f"Ollama error al conectar con {self.host}: {exc}")
                
        except Exception as e:
            self.logger.error(f"Ollama generate_text error: {e}")
            raise

    def generate_text_with_thinking(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Genera respuesta no-stream devolviendo contenido final y traza thinking."""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 512)
        think = self._normalize_think_value(
            model_name=model,
            think=kwargs.get("think", True),
        )

        messages = kwargs.get("messages")
        if messages:
            chat_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        else:
            chat_messages = [{"role": "user", "content": prompt}]

        response = self.client.chat(
            model=model,
            messages=chat_messages,
            stream=False,
            think=think,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )

        content = self._extract_message_field(response, "content").strip()
        thinking = self._extract_message_field(response, "thinking")

        return {
            "content": content,
            "thinking": thinking,
            "model": model,
            "think": think,
            "provider_supports_thinking": True,
        }

    def generate_text_stream(self, prompt: str, **kwargs) -> Iterator[AIStreamChunk]:
        """Streaming nativo de Ollama con soporte para chunks de thinking/content."""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 512)
        think = self._normalize_think_value(model_name=model, think=kwargs.get("think"))

        messages = kwargs.get("messages")
        if messages:
            chat_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        else:
            chat_messages = [{"role": "user", "content": prompt}]

        stream = self.client.chat(
            model=model,
            messages=chat_messages,
            stream=True,
            think=think,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )

        for chunk in stream:
            yield AIStreamChunk(
                content=self._extract_message_field(chunk, "content"),
                thinking=self._extract_message_field(chunk, "thinking"),
                done=self._extract_done(chunk),
                raw=chunk,
            )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama's embed endpoint with embedding-specific model."""
        try:
            # Use embedding-specific model (embeddinggemma, qwen3-embedding, all-minilm)
            embedding_model = getattr(self.settings, "ollama_embedding_model", "embeddinggemma")
            self.logger.debug(f"Generating embeddings for {len(texts)} texts using model={embedding_model}")
            
            # Use client's embed method with configured host/credentials
            embeddings = []
            for text in texts:
                result = self.client.embed(model=embedding_model, input=text)
                # API returns {"embeddings": [[...]], "model": "..."}
                embedding_data = result.get("embeddings", result.get("embedding", []))
                if isinstance(embedding_data, list) and len(embedding_data) > 0:
                    embeddings.append(embedding_data[0] if isinstance(embedding_data[0], list) else embedding_data)
                else:
                    embeddings.append(embedding_data)
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Ollama embed_texts error: {e}")
            raise NotImplementedError(f"Ollama embeddings error: {e}")
