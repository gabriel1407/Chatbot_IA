"""
Adaptador para Ollama usando la librería oficial de Python.
Soporta autenticación mediante API key para endpoints cloud.
"""
from typing import List
import logging
import ollama
from ollama import Client

from core.ai.providers import AIProvider
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

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Ollama's official library with chat endpoint."""
        try:
            model = kwargs.get("model", self.model)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 512)
            
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
