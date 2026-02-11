"""
Servicio que integra RAG con LLM (OpenAI).
Busca información en el RAG y la pasa como contexto a OpenAI.
"""
from typing import Optional, List
from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
import requests

logger = get_infrastructure_logger()


class RAGLLMService:
    """
    Integración RAG + LLM.
    Busca información en RAG y genera respuesta contextualizada con OpenAI.
    """
    
    def __init__(self, rag_base_url: str = "http://127.0.0.1:9001"):
        self.rag_base_url = rag_base_url
        self.logger = get_infrastructure_logger()
    
    def search_rag(self, user_id: str, query: str, top_k: Optional[int] = None, min_similarity: Optional[float] = None) -> List[dict]:
        """
        Busca información en el RAG.
        Búsqueda GLOBAL - sin filtrar por user_id.
        
        Args:
            user_id: ID del usuario (para logging, no para filtrado)
            query: Pregunta o texto a buscar
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de chunks encontrados con contenido y similitud
        """
        try:
            if not settings.rag_enabled:
                return []
            url = f"{self.rag_base_url}/api/rag/search"
            params = {
                "query": query,
                "top_k": top_k or settings.rag_chat_top_k or settings.rag_top_k,
                "min_similarity": (min_similarity if min_similarity is not None else settings.rag_global_min_similarity),
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("ok"):
                return data.get("results", [])
            else:
                self.logger.warning(f"RAG search failed: {data.get('error')}")
                return []
                
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
            
            # 3. Llamar a OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            
            system_message = system_prompt or "Eres un asistente útil basado en la información de la base de conocimientos del usuario."
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # Log de la búsqueda
            self.logger.info(f"RAG+LLM response for user {user_id}: {len(rag_results)} chunks used, {len(answer)} chars response")
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta RAG+LLM: {e}")
            raise
