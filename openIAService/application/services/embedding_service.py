"""
Interface EmbeddingService - Define el contrato para servicios de embeddings.
Usado para RAG y búsqueda semántica.
"""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingService(ABC):
    """
    Interface para servicios de embeddings.
    Permite abstraer el proveedor (OpenAI, Cohere, local, etc.).
    """
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding para un texto.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Vector de embedding
        """
        pass
    
    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos (batch).
        
        Args:
            texts: Lista de textos
            
        Returns:
            Lista de vectores de embedding
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Retorna la dimensión del embedding.
        
        Returns:
            Dimensión del vector (ej: 1536 para OpenAI)
        """
        pass
