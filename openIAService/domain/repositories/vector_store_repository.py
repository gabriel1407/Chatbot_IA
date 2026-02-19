"""
Interface VectorStoreRepository - Define el contrato para búsqueda vectorial (RAG).
Soporta aislamiento multi-tenant mediante tenant_id.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from domain.entities.document import DocumentChunk
from domain.value_objects.search_query import SearchQuery


class VectorStoreRepository(ABC):
    """
    Interface para repositorio de vectores (embeddings).
    Usado para búsqueda semántica en RAG.

    Soporta aislamiento multi-tenant: cada tenant tiene su propia colección de vectores.
    """

    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk], tenant_id: str) -> bool:
        """
        Agrega chunks con sus embeddings al vector store del tenant.

        Args:
            chunks: Lista de chunks a agregar
            tenant_id: ID del tenant (aislamiento multi-tenant)

        Returns:
            True si se agregaron exitosamente
        """
        pass

    @abstractmethod
    def search(
        self,
        query: SearchQuery,
        tenant_id: str
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Realiza búsqueda semántica en la colección del tenant.

        Args:
            query: Consulta de búsqueda
            tenant_id: ID del tenant (aislamiento multi-tenant)

        Returns:
            Lista de tuplas (chunk, similarity_score)
        """
        pass

    @abstractmethod
    def delete_by_document_id(self, document_id: str, tenant_id: str) -> bool:
        """
        Elimina todos los chunks de un documento en la colección del tenant.

        Args:
            document_id: ID del documento
            tenant_id: ID del tenant

        Returns:
            True si se eliminaron
        """
        pass

    @abstractmethod
    def delete_by_user_id(self, user_id: str, tenant_id: str) -> bool:
        """
        Elimina todos los chunks de un usuario en la colección del tenant.

        Args:
            user_id: ID del usuario
            tenant_id: ID del tenant

        Returns:
            True si se eliminaron
        """
        pass

    @abstractmethod
    def count_chunks(self, tenant_id: str, user_id: Optional[str] = None) -> int:
        """
        Cuenta el número de chunks almacenados en la colección del tenant.

        Args:
            tenant_id: ID del tenant
            user_id: ID del usuario (opcional, para filtrar dentro del tenant)

        Returns:
            Número de chunks
        """
        pass
