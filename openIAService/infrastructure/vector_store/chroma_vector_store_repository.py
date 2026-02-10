"""
ChromaVectorStoreRepository - Implementación del VectorStoreRepository usando ChromaDB.
Se conecta al servidor de Chroma por HTTP para separar responsabilidades.
"""
from typing import List, Tuple, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
from core.exceptions.custom_exceptions import VectorStoreException
from domain.entities.document import DocumentChunk
from domain.value_objects.search_query import SearchQuery
from domain.repositories.vector_store_repository import VectorStoreRepository


class ChromaVectorStoreRepository(VectorStoreRepository):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str = "chatbot_ia_chunks",
    ):
        self._logger = get_infrastructure_logger()
        self._host = host or "chroma"
        self._port = port or 8000
        self._collection_name = collection_name

        try:
            self._client = chromadb.HttpClient(
                host=self._host,
                port=self._port,
                settings=ChromaSettings(allow_reset=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._logger.info(
                f"Chroma conectado en http://{self._host}:{self._port} colección={self._collection_name}"
            )
        except Exception as e:
            self._logger.error(f"Error conectando a Chroma: {e}")
            raise

    def _build_ids(self, chunks: List[DocumentChunk]) -> List[str]:
        return [f"{c.document_id}:{c.chunk_index}" for c in chunks]

    def _build_metadatas(self, chunks: List[DocumentChunk]) -> List[dict]:
        metas: List[dict] = []
        for c in chunks:
            meta = {
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                **(c.metadata or {}),
            }
            metas.append(meta)
        return metas

    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        try:
            if not chunks:
                return True

            ids = self._build_ids(chunks)
            documents = [c.content for c in chunks]
            embeddings = [c.embedding for c in chunks] if chunks[0].embedding is not None else None
            metadatas = self._build_metadatas(chunks)

            self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
            self._logger.info(f"Agregados {len(ids)} chunks a Chroma")
            return True
        except Exception as e:
            self._logger.error(f"Error agregando chunks a Chroma: {e}")
            raise VectorStoreException(str(e))

    def search(self, query: SearchQuery) -> List[Tuple[DocumentChunk, float]]:
        try:
            res = self._collection.query(
                query_texts=[query.get_normalized_query()],
                n_results=query.top_k,
                where=query.filters or None,
                include=["documents", "metadatas", "distances"],
            )

            results: List[Tuple[DocumentChunk, float]] = []
            if not res or not res.get("documents"):
                return results

            docs = res["documents"][0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            # Convertir distancia a similitud para 'cosine' (1 - distancia)
            for i in range(len(docs)):
                meta = metas[i] or {}
                doc_text = docs[i]
                distance = dists[i] if i < len(dists) else 1.0
                similarity = 1.0 - float(distance)
                if similarity < query.min_similarity:
                    continue
                chunk = DocumentChunk(
                    content=doc_text,
                    chunk_index=int(meta.get("chunk_index", 0)),
                    document_id=str(meta.get("document_id", "unknown")),
                    metadata=meta,
                )
                results.append((chunk, similarity))

            return results
        except Exception as e:
            self._logger.error(f"Error en búsqueda Chroma: {e}")
            raise VectorStoreException(str(e))

    def delete_by_document_id(self, document_id: str) -> bool:
        try:
            self._collection.delete(where={"document_id": document_id})
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando por document_id en Chroma: {e}")
            raise VectorStoreException(str(e))

    def delete_by_user_id(self, user_id: str) -> bool:
        try:
            self._collection.delete(where={"user_id": user_id})
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando por user_id en Chroma: {e}")
            raise VectorStoreException(str(e))

    def count_chunks(self, user_id: Optional[str] = None) -> int:
        try:
            # Chroma no expone count directo con filtro via HTTP, aproximamos consultando 1
            if user_id:
                res = self._collection.get(where={"user_id": user_id}, include=[])
            else:
                res = self._collection.get(include=[])
            return len(res.get("ids", [])) if res else 0
        except Exception as e:
            self._logger.error(f"Error contando chunks: {e}")
            raise VectorStoreException(str(e))
