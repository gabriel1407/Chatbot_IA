"""
Interface VectorStoreRepository - Define el contrato para búsqueda vectorial (RAG).
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from domain.entities.document import DocumentChunk
from domain.value_objects.search_query import SearchQuery


class VectorStoreRepository(ABC):
    """
    Interface para repositorio de vectores (embeddings).
    Usado para búsqueda semántica en RAG.
    """
    
    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Agrega chunks con sus embeddings al vector store.
        
        Args:
            chunks: Lista de chunks a agregar
            
        Returns:
            True si se agregaron exitosamente
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: SearchQuery
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Realiza búsqueda semántica.
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            Lista de tuplas (chunk, similarity_score)
        """
        pass
    
    @abstractmethod
    def delete_by_document_id(self, document_id: str) -> bool:
        """
        Elimina todos los chunks de un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            True si se eliminaron
        """
        pass
    
    @abstractmethod
    def delete_by_user_id(self, user_id: str) -> bool:
        """
        Elimina todos los chunks de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si se eliminaron
        """
        pass
    
    @abstractmethod
    def count_chunks(self, user_id: Optional[str] = None) -> int:
        """
        Cuenta el número de chunks almacenados.
        
        Args:
            user_id: ID del usuario (opcional, para filtrar)
            
        Returns:
            Número de chunks
        """
        pass
