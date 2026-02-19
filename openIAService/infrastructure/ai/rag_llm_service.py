"""
Servicio que integra RAG con LLM.
Busca información en el RAG y la pasa como contexto al proveedor IA configurado.
"""
from typing import Optional, List
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger

logger = get_infrastructure_logger()


class RAGLLMService:
    """
    Integración RAG + LLM.
    Busca información en RAG llamando directamente al servicio Python (sin HTTP).
    """

    def __init__(self):
        self.logger = get_infrastructure_logger()

    def _get_rag_service(self):
        """Obtiene el RAGService del contenedor de dependencias."""
        from core.config.dependencies import DependencyContainer
        return DependencyContainer.get("RAGService")

    def search_rag(self, user_id: str, query: str, top_k: Optional[int] = None, min_similarity: Optional[float] = None) -> List[dict]:
        """
        Busca información en el RAG directamente en el servicio Python.
        Sin llamadas HTTP — evita problemas de autenticación y latencia.
        """
        try:
            if not settings.rag_enabled:
                return []

            rag_service = self._get_rag_service()
            effective_top_k = top_k or getattr(settings, "rag_chat_top_k", None) or settings.rag_top_k
            effective_sim = min_similarity if min_similarity is not None else settings.rag_global_min_similarity

            results = rag_service.retrieve(
                query_text=query,
                top_k=effective_top_k,
                min_similarity=effective_sim,
            )

            return [
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": float(score),
                }
                for chunk, score in results
            ]

        except Exception as e:
            self.logger.error(f"Error buscando en RAG: {e}")
            return []
    
    def build_context_prompt(self, query: str, rag_results: List[dict]) -> str:
        """
        Construye el prompt con contexto del RAG.
        
        Args:
            query: Pregunta del usuario
            rag_results: Resultados del RAG
            
        Returns:
            Prompt complementado con contexto
        """
        if not rag_results:
            return f"Pregunta del usuario: {query}\n\nNota: No hay información en la base de conocimientos para esta consulta."
        
        context_str = "Información relevante de la base de conocimientos:\n"
        for i, result in enumerate(rag_results, 1):
            content = result.get("content", "")
            similarity = result.get("similarity", 0)
            doc_id = result.get("document_id", "")
            context_str += f"\n[{i}] (Similitud: {similarity:.2f}) Doc: {doc_id}\n{content}\n"
        
        prompt = f"""Contexto del usuario:
{context_str}

Pregunta del usuario: {query}

Por favor, responde basándote en la información proporcionada anteriormente. 
Si la pregunta no se puede responder con la información disponible, indícalo claramente."""
        
        return prompt
    
    def generate_rag_response(
        self, 
        user_id: str, 
        query: str, 
        system_prompt: Optional[str] = None,
        top_k: int = 5,
        temperature: float = 0.7
    ) -> str:
        """
        Genera respuesta usando RAG + OpenAI.
        
        Args:
            user_id: ID del usuario/cliente
            query: Pregunta del usuario
            system_prompt: Prompt del sistema personalizado
            top_k: Número de chunks a buscar en RAG
            temperature: Creatividad de OpenAI (0.0-1.0)
            
        Returns:
            Respuesta del modelo
        """
        try:
            # 1. Buscar en RAG (usar settings si no se especifica)
            rag_results = self.search_rag(user_id, query, top_k=top_k, min_similarity=settings.rag_global_min_similarity)
            
            # 2. Construir prompt con contexto
            context_prompt = self.build_context_prompt(query, rag_results)
            
            # 3. Llamar al proveedor configurado (a través de la fábrica)
            from core.ai.factory import get_ai_provider

            provider = get_ai_provider()
            system_message = system_prompt or "Eres un asistente útil basado en la información de la base de conocimientos del usuario."

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": context_prompt},
            ]

            # Delegar en provider; se asume que provider.generate_text admite 'messages' en kwargs
            answer = provider.generate_text(prompt=context_prompt, messages=messages, temperature=temperature)

            # Log de la búsqueda
            self.logger.info(f"RAG+LLM response for user {user_id}: {len(rag_results)} chunks used, {len(answer)} chars response")

            return answer
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta RAG+LLM: {e}")
            raise
