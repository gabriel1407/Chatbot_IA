"""
Interface DocumentRepository - Define el contrato para persistencia de documentos.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.document import Document


class DocumentRepository(ABC):
    """
    Interface para repositorio de documentos.
    Gestiona el almacenamiento de documentos procesados.
    """
    
    @abstractmethod
    def save(self, document: Document) -> Document:
        """
        Guarda o actualiza un documento.
        
        Args:
            document: Documento a guardar
            
        Returns:
            Documento guardado con ID asignado
        """
        pass
    
    @abstractmethod
    def find_by_id(self, document_id: str) -> Optional[Document]:
        """
        Busca un documento por su ID.
        
        Args:
            document_id: ID del documento
            
        Returns:
            Documento encontrado o None
        """
        pass
    
    @abstractmethod
    def find_by_user(self, user_id: str) -> List[Document]:
        """
        Busca todos los documentos de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de documentos
        """
        pass
    
    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """
        Elimina un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            True si se eliminó, False si no existía
        """
        pass
