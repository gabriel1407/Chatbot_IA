"""
RAGService - Orquesta ingestión y recuperación para RAG.
Separa responsabilidades: chunking, embeddings, almacenamiento, retrieval.
"""
from typing import List, Tuple, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config.settings import settings
from core.logging.logger import get_application_logger, get_rag_logger
from domain.entities.document import Document, DocumentChunk, DocumentType
from domain.value_objects.search_query import SearchQuery

from application.services.embedding_service import EmbeddingService
from domain.repositories.vector_store_repository import VectorStoreRepository


class RAGService:
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

    # Ingestión
    def ingest_text(
        self,
        user_id: str,
        document_id: str,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Ingiere texto plano como documento en el vector store. Retorna número de chunks indexados."""
        metadata = metadata or {}
        doc = Document(
            id=document_id,
            title=title,
            content=text,
            document_type=DocumentType.TXT,
            user_id=user_id,
            metadata={**metadata, "user_id": user_id},
        )

        texts = self._splitter.split_text(text)
        chunks: List[DocumentChunk] = []
        for idx, chunk_text in enumerate(texts):
            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    chunk_index=idx,
                    document_id=doc.id or document_id,
                    metadata={"user_id": user_id, "title": title or ""},
                )
            )

        # Embeddings por batch
        embeddings = self._embedding.generate_embeddings_batch([c.content for c in chunks])
        for i, emb in enumerate(embeddings):
            chunks[i].embedding = emb

        self._vs.add_chunks(chunks)
        self._logger.info(f"Documento {document_id} ingerido con {len(chunks)} chunks")
        return len(chunks)

    def delete_document(self, document_id: str) -> bool:
        return self._vs.delete_by_document_id(document_id)

    # Recuperación
    def retrieve(self, query_text: str, top_k: Optional[int] = None, user_id: Optional[str] = None, min_similarity: Optional[float] = None) -> List[Tuple[DocumentChunk, float]]:
        """
        Busca documentos en el vector store.
        
        Args:
            query_text: Texto a buscar
            top_k: Número de resultados (opcional)
            user_id: Filtrar por usuario (opcional, por defecto busca globalmente)
            
        Returns:
            Lista de chunks encontrados con similitud
        """
        filters = {}
        if user_id:
            filters = {"user_id": user_id}
        
        sq = SearchQuery(
            query_text=query_text,
            top_k=top_k or settings.rag_top_k,
            filters=filters,
            min_similarity=min_similarity if min_similarity is not None else settings.rag_min_similarity,
        )
        return self._vs.search(sq)
