"""
Entidad Document - Representa un documento procesado en el sistema.
Usado para RAG y búsqueda semántica.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class DocumentType(Enum):
    """Tipos de documento soportados."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"
    WEB_PAGE = "web_page"


@dataclass
class DocumentChunk:
    """
    Representa un fragmento de un documento.
    Usado para chunking en RAG.
    """
    content: str
    chunk_index: int
    document_id: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        """Validaciones."""
        if not self.content:
            raise ValueError("El contenido del chunk no puede estar vacío")
        
        if self.chunk_index < 0:
            raise ValueError("El chunk_index debe ser >= 0")


@dataclass
class Document:
    """
    Entidad que representa un documento procesado.
    
    Attributes:
        id: Identificador único del documento
        title: Título o nombre del documento
        content: Contenido completo del documento
        document_type: Tipo de documento
        user_id: ID del usuario que subió el documento
        file_path: Ruta del archivo original
        chunks: Fragmentos del documento para RAG
        created_at: Fecha de creación
        metadata: Información adicional (tamaño, páginas, etc.)
    """
    content: str
    document_type: DocumentType
    user_id: Optional[str] = None
    title: Optional[str] = None
    id: Optional[str] = None
    file_path: Optional[str] = None
    chunks: List[DocumentChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validaciones después de la inicialización."""
        if not self.content:
            raise ValueError("El contenido del documento no puede estar vacío")
    
    def add_chunk(self, chunk: DocumentChunk) -> None:
        """
        Agrega un chunk al documento.
        
        Args:
            chunk: Fragmento a agregar
        """
        if chunk.document_id != self.id:
            chunk.document_id = self.id
        
        self.chunks.append(chunk)
    
    def get_chunk_count(self) -> int:
        """Retorna el número de chunks."""
        return len(self.chunks)
    
    def get_content_preview(self, max_length: int = 200) -> str:
        """
        Obtiene una vista previa del contenido.
        
        Args:
            max_length: Longitud máxima de la vista previa
            
        Returns:
            Vista previa del contenido
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def to_dict(self) -> dict:
        """Convierte el documento a formato dict."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "document_type": self.document_type.value,
            "user_id": self.user_id,
            "file_path": self.file_path,
            "chunk_count": self.get_chunk_count(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
