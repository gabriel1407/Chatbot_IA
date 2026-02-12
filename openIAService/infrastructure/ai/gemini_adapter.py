"""
Adaptador para Gemini usando la librería oficial `google-genai` (nueva API).
Esta implementación usa la new Google Generative AI SDK.
"""
from typing import List
import logging
try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - import warning handled at runtime
    genai = None
    types = None

from core.ai.providers import AIProvider
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger


_logger = get_infrastructure_logger()
 
class GeminiAdapter(AIProvider):
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.logger = _logger
        self.client = None

        # Initialize client if library available
        if genai:
            api_key = getattr(self.settings, "gemini_api_key", None)
            try:
                if api_key:
                    self.client = genai.Client(api_key=api_key)
                else:
                    self.logger.warning("Gemini adapter: No API key provided")
            except Exception as e:
                self.logger.warning(f"Gemini adapter: failed to initialize client: {e}")
        else:
            self.logger.warning("Gemini adapter: google.genai not installed or failed to import")

    def generate_text(self, prompt: str, **kwargs) -> str:
        if not self.client:
            self.logger.error("Gemini client not initialized")
            raise RuntimeError("google.genai client is not available or not initialized")

        model_name = kwargs.get("model") or self.settings.gemini_model or "gemini-2.5-flash-lite"
        
        self.logger.info(f"Gemini generate_text: model={model_name}")
        
        # If messages provided, format them properly for Gemini
        messages = kwargs.get("messages")
        if messages:
            # Format: role as label, content on same line
            parts = []
            for m in messages:
                role = m.get('role', 'user')
                content = m.get('content', '')
                if role == 'system':
                    parts.append(f"[System Instructions] {content}")
                elif role == 'user':
                    parts.append(f"User: {content}")
                elif role == 'assistant':
                    parts.append(f"Assistant: {content}")
            prompt_text = "\n\n".join(parts)
        else:
            prompt_text = prompt

        self.logger.info(f"Gemini request (first 200 chars): {prompt_text[:200]}")

        try:
            # Use new google-genai API
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    temperature=kwargs.get("temperature", 0.7),
                    max_output_tokens=kwargs.get("max_tokens", 512),
                )
            )

            # Extract text from response
            if hasattr(response, 'text') and response.text:
                return response.text.strip()
            
            # Fallback: try to access candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        parts_text = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
                        return parts_text.strip()
                    elif hasattr(candidate.content, 'text'):
                        return candidate.content.text.strip()
            
            self.logger.error(f"Gemini returned unexpected response structure: {response}")
            return "Error: Respuesta inválida de Gemini"
            
        except Exception as e:
            self.logger.error(f"Gemini generate_text error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Gemini generate_text error: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Gemini's embed_content endpoint."""
        if not self.client:
            self.logger.error("Gemini client not initialized")
            raise RuntimeError("google.genai client is not available or not initialized")
        
        try:
            # Use gemini-embedding-001 or configured embedding model
            embedding_model = getattr(self.settings, "gemini_embedding_model", "gemini-embedding-001")
            self.logger.debug(f"Generating embeddings for {len(texts)} texts using model={embedding_model}")
            
            # Gemini supports batch embeddings
            result = self.client.models.embed_content(
                model=embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",  # For RAG/document indexing
                    output_dimensionality=768  # 768 for efficiency, can use 1536 or 3072
                )
            )
            
            # Extract embeddings from result
            embeddings = []
            for emb_obj in result.embeddings:
                if hasattr(emb_obj, 'values'):
                    embeddings.append(emb_obj.values)
                else:
                    embeddings.append(list(emb_obj))
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Gemini embed_texts error: {e}")
            raise NotImplementedError(f"Gemini embeddings error: {e}")
