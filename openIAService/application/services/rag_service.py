"""
RAGService - Orquesta ingestión y recuperación para RAG con aislamiento multi-tenant.
Separa responsabilidades: chunking, embeddings, almacenamiento, retrieval.
"""
from typing import List, Tuple, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config.settings import settings
from core.logging.logger import get_rag_logger
from domain.entities.document import Document, DocumentChunk, DocumentType
from domain.value_objects.search_query import SearchQuery

from application.services.embedding_service import EmbeddingService
from domain.repositories.vector_store_repository import VectorStoreRepository


class RAGService:
    """
    Servicio de RAG (Retrieval Augmented Generation) con soporte multi-tenant.

    Cada operación requiere tenant_id para garantizar aislamiento de datos
    entre diferentes clientes/empresas.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreRepository,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self._embedding = embedding_service
        self._vs = vector_store
        self._chunk_size = chunk_size or settings.rag_chunk_size
        self._chunk_overlap = chunk_overlap or settings.rag_chunk_overlap
        self._logger = get_rag_logger()

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def ingest_text(
        self,
        tenant_id: str,
        document_id: str,
        text: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """
        Ingiere texto plano como documento en el vector store del tenant.

        Args:
            tenant_id: ID del tenant (OBLIGATORIO para aislamiento)
            document_id: ID único del documento
            text: Contenido textual a indexar
            user_id: ID del usuario que sube el documento (opcional)
            title: Título del documento (opcional)
            metadata: Metadatos adicionales (opcional)

        Returns:
            Número de chunks indexados
        """
        metadata = metadata or {}

        # Construir documento con metadata del tenant
        doc = Document(
            id=document_id,
            title=title,
            content=text,
            document_type=DocumentType.TXT,
            user_id=user_id,
            metadata={
                **metadata,
                "tenant_id": tenant_id,
                "user_id": user_id or "unknown",
            },
        )

        # Dividir en chunks
        texts = self._splitter.split_text(text)
        chunks: List[DocumentChunk] = []

        for idx, chunk_text in enumerate(texts):
            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    chunk_index=idx,
                    document_id=doc.id or document_id,
                    metadata={
                        "tenant_id": tenant_id,
                        "user_id": user_id or "unknown",
                        "title": title or "",
                    },
                )
            )

        # Generar embeddings por batch
        embeddings = self._embedding.generate_embeddings_batch([c.content for c in chunks])
        for i, emb in enumerate(embeddings):
            chunks[i].embedding = emb

        # Almacenar en la colección del tenant
        self._vs.add_chunks(chunks, tenant_id=tenant_id)
        self._logger.info(
            f"Documento {document_id} ingerido con {len(chunks)} chunks para tenant {tenant_id}"
        )
        return len(chunks)

    def delete_document(self, document_id: str, tenant_id: str) -> bool:
        """
        Elimina un documento de la colección del tenant.

        Args:
            document_id: ID del documento a eliminar
            tenant_id: ID del tenant

        Returns:
            True si se eliminó correctamente
        """
        return self._vs.delete_by_document_id(document_id, tenant_id=tenant_id)

    def retrieve(
        self,
        query_text: str,
        tenant_id: str,
        top_k: Optional[int] = None,
        user_id: Optional[str] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Busca documentos en el vector store del tenant.

        Args:
            query_text: Texto de la consulta
            tenant_id: ID del tenant (OBLIGATORIO para aislamiento)
            top_k: Número máximo de resultados (opcional)
            user_id: Filtrar por usuario dentro del tenant (opcional)
            min_similarity: Similitud mínima (opcional)

        Returns:
            Lista de tuplas (chunk, similarity_score)
        """
        # Construir filtros
        filters = {}
        if user_id:
            filters["user_id"] = user_id

        sq = SearchQuery(
            query_text=query_text,
            top_k=top_k or settings.rag_top_k,
            filters=filters,
            min_similarity=min_similarity if min_similarity is not None else settings.rag_min_similarity,
        )

        return self._vs.search(sq, tenant_id=tenant_id)

    def count_chunks(self, tenant_id: str, user_id: Optional[str] = None) -> int:
        """
        Cuenta chunks en la colección del tenant.

        Args:
            tenant_id: ID del tenant
            user_id: Filtrar por usuario (opcional)

        Returns:
            Número de chunks
        """
        return self._vs.count_chunks(tenant_id=tenant_id, user_id=user_id)