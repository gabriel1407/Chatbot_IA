"""
ChromaVectorStoreRepository - Implementación del VectorStoreRepository usando ChromaDB.
Soporta aislamiento multi-tenant mediante colecciones dinámicas por tenant_id.
"""
from typing import List, Tuple, Optional, Dict

import chromadb
from chromadb.config import Settings as ChromaSettings

from core.config.settings import settings
from core.logging.logger import get_infrastructure_logger
from core.exceptions.custom_exceptions import VectorStoreException
from domain.entities.document import DocumentChunk
from domain.value_objects.search_query import SearchQuery
from domain.repositories.vector_store_repository import VectorStoreRepository
from application.services.embedding_service import EmbeddingService


class ChromaVectorStoreRepository(VectorStoreRepository):
    """
    Implementación de VectorStoreRepository usando ChromaDB con aislamiento multi-tenant.

    Cada tenant tiene su propia colección: tenant_{tenant_id}_chunks
    Las colecciones se cachean para evitar recrearlas en cada operación.
    """

    # Prefijo para nombres de colecciones de tenant
    TENANT_COLLECTION_PREFIX = "tenant_"
    COLLECTION_SUFFIX = "_chunks"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self._logger = get_infrastructure_logger()
        self._host = host or "chroma"
        self._port = port or 8000
        self._embedding_service = embedding_service

        # Cache de colecciones por tenant_id
        self._collections: Dict[str, chromadb.Collection] = {}

        # Cliente ChromaDB compartido
        try:
            self._client = chromadb.HttpClient(
                host=self._host,
                port=self._port,
                settings=ChromaSettings(allow_reset=False),
            )
            self._logger.info(f"ChromaDB conectado en http://{self._host}:{self._port}")
        except Exception as e:
            self._logger.error(f"Error conectando a ChromaDB: {e}")
            raise

    def _get_collection_name(self, tenant_id: str) -> str:
        """
        Genera el nombre de colección para un tenant.

        Args:
            tenant_id: ID del tenant

        Returns:
            Nombre de la colección: tenant_{tenant_id}_chunks
        """
        # Sanitizar tenant_id para que sea válido como nombre de colección
        safe_tenant_id = tenant_id.replace("-", "_").replace(" ", "_").lower()
        return f"{self.TENANT_COLLECTION_PREFIX}{safe_tenant_id}{self.COLLECTION_SUFFIX}"

    def _get_or_create_collection(self, tenant_id: str) -> chromadb.Collection:
        """
        Obtiene la colección del tenant, creándola si no existe.
        Usa cache para evitar llamadas repetidas a ChromaDB.

        Args:
            tenant_id: ID del tenant

        Returns:
            Colección de ChromaDB para el tenant
        """
        if tenant_id in self._collections:
            return self._collections[tenant_id]

        collection_name = self._get_collection_name(tenant_id)

        try:
            collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "tenant_id": tenant_id},
            )
            self._collections[tenant_id] = collection
            self._logger.debug(f"Colección {collection_name} lista para tenant {tenant_id}")
            return collection
        except Exception as e:
            self._logger.error(f"Error creando/obteniendo colección {collection_name}: {e}")
            raise VectorStoreException(f"Error accediendo colección del tenant: {e}")

    def _build_ids(self, chunks: List[DocumentChunk]) -> List[str]:
        """Construye IDs únicos para los chunks."""
        return [f"{c.document_id}:{c.chunk_index}" for c in chunks]

    def _build_metadatas(self, chunks: List[DocumentChunk], tenant_id: str) -> List[dict]:
        """
        Construye metadata para los chunks incluyendo tenant_id.

        Args:
            chunks: Lista de chunks
            tenant_id: ID del tenant para incluir en metadata

        Returns:
            Lista de diccionarios de metadata
        """
        metas: List[dict] = []
        for c in chunks:
            meta = {
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "tenant_id": tenant_id,  # Asegurar que tenant_id esté en metadata
                **(c.metadata or {}),
            }
            metas.append(meta)
        return metas

    def add_chunks(self, chunks: List[DocumentChunk], tenant_id: str) -> bool:
        """
        Agrega chunks a la colección del tenant especificado.

        Args:
            chunks: Lista de chunks a agregar
            tenant_id: ID del tenant (aislamiento multi-tenant)

        Returns:
            True si se agregaron exitosamente
        """
        try:
            if not chunks:
                return True

            collection = self._get_or_create_collection(tenant_id)

            ids = self._build_ids(chunks)
            documents = [c.content for c in chunks]
            embeddings = [c.embedding for c in chunks] if chunks[0].embedding is not None else None
            metadatas = self._build_metadatas(chunks, tenant_id)

            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            self._logger.info(f"Agregados {len(ids)} chunks a colección del tenant {tenant_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error agregando chunks a ChromaDB para tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))

    def search(self, query: SearchQuery, tenant_id: str) -> List[Tuple[DocumentChunk, float]]:
        """
        Busca en la colección del tenant especificado.

        Args:
            query: Consulta de búsqueda
            tenant_id: ID del tenant (aislamiento multi-tenant)

        Returns:
            Lista de tuplas (chunk, similarity_score)
        """
        try:
            collection = self._get_or_create_collection(tenant_id)

            # Generar embedding de la query
            query_embedding = None
            if self._embedding_service:
                query_embedding = self._embedding_service.generate_embedding(
                    query.get_normalized_query()
                )

            # El aislamiento por tenant ya lo garantiza la colección separada.
            # Solo aplicar where si hay filtros adicionales reales (user_id, etc.)
            # ChromaDB lanza excepción con where={} vacío.
            where_filter = {k: v for k, v in (query.filters or {}).items() if k != "tenant_id"}
            use_where = where_filter or None

            # Ejecutar búsqueda
            if query_embedding:
                res = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=query.top_k,
                    where=use_where,
                    include=["documents", "metadatas", "distances"],
                )
            else:
                res = collection.query(
                    query_texts=[query.get_normalized_query()],
                    n_results=query.top_k,
                    where=use_where,
                    include=["documents", "metadatas", "distances"],
                )

            results: List[Tuple[DocumentChunk, float]] = []
            if not res or not res.get("documents"):
                return results

            docs = res["documents"][0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            # Convertir distancia a similitud (cosine: 1 - distancia)
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
            self._logger.error(f"Error en búsqueda ChromaDB para tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))

    def delete_by_document_id(self, document_id: str, tenant_id: str) -> bool:
        """
        Elimina todos los chunks de un documento en la colección del tenant.

        Args:
            document_id: ID del documento
            tenant_id: ID del tenant

        Returns:
            True si se eliminaron
        """
        try:
            collection = self._get_or_create_collection(tenant_id)
            # Filtrar solo por document_id; la colección ya aísla por tenant
            collection.delete(where={"document_id": document_id})
            self._logger.info(f"Documento {document_id} eliminado del tenant {tenant_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando documento {document_id} en tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))

    def delete_tenant_collection(self, tenant_id: str) -> bool:
        """
        Elimina TODA la colección del tenant de ChromaDB (borrado completo).

        Args:
            tenant_id: ID del tenant

        Returns:
            True si se eliminó correctamente
        """
        try:
            collection_name = self._get_collection_name(tenant_id)
            self._client.delete_collection(collection_name)
            # Limpiar caché interno
            self._collections.pop(tenant_id, None)
            self._logger.info(f"Colección '{collection_name}' eliminada para tenant '{tenant_id}'")
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando colección del tenant '{tenant_id}': {e}")
            raise VectorStoreException(str(e))

    def delete_by_user_id(self, user_id: str, tenant_id: str) -> bool:
        """
        Elimina todos los chunks de un usuario en la colección del tenant.

        Args:
            user_id: ID del usuario
            tenant_id: ID del tenant

        Returns:
            True si se eliminaron
        """
        try:
            collection = self._get_or_create_collection(tenant_id)
            collection.delete(where={"user_id": user_id, "tenant_id": tenant_id})
            self._logger.info(f"Chunks del usuario {user_id} eliminados del tenant {tenant_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando chunks del usuario {user_id} en tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))

    def count_chunks(self, tenant_id: str, user_id: Optional[str] = None) -> int:
        """
        Cuenta el número de chunks en la colección del tenant.

        Args:
            tenant_id: ID del tenant
            user_id: ID del usuario (opcional, para filtrar dentro del tenant)

        Returns:
            Número de chunks
        """
        try:
            collection = self._get_or_create_collection(tenant_id)

            if user_id:
                res = collection.get(where={"user_id": user_id, "tenant_id": tenant_id}, include=[])
            else:
                res = collection.get(include=[])

            return len(res.get("ids", [])) if res else 0
        except Exception as e:
            self._logger.error(f"Error contando chunks para tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))

    # === Métodos de utilidad para administración ===

    def list_tenant_collections(self) -> List[str]:
        """
        Lista todas las colecciones de tenants existentes.

        Returns:
            Lista de nombres de colecciones de tenants
        """
        try:
            all_collections = self._client.list_collections()
            tenant_collections = [
                c.name for c in all_collections
                if c.name.startswith(self.TENANT_COLLECTION_PREFIX) and c.name.endswith(self.COLLECTION_SUFFIX)
            ]
            return tenant_collections
        except Exception as e:
            self._logger.error(f"Error listando colecciones: {e}")
            return []

    def delete_tenant_collection(self, tenant_id: str) -> bool:
        """
        Elimina completamente la colección de un tenant.
        Útil para limpieza o reset de un tenant específico.

        Args:
            tenant_id: ID del tenant

        Returns:
            True si se eliminó la colección
        """
        try:
            collection_name = self._get_collection_name(tenant_id)
            self._client.delete_collection(collection_name)

            # Limpiar cache
            if tenant_id in self._collections:
                del self._collections[tenant_id]

            self._logger.info(f"Colección {collection_name} eliminada para tenant {tenant_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error eliminando colección del tenant {tenant_id}: {e}")
            raise VectorStoreException(str(e))