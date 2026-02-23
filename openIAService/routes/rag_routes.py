"""
Rutas RAG - Endpoints para ingestión y búsqueda de documentos con aislamiento multi-tenant.
"""
from flask import Blueprint, request, jsonify
import hashlib
import os
import uuid
from werkzeug.utils import secure_filename
from core.logging.logger import get_app_logger
from core.config.dependencies import DependencyContainer
from core.exceptions.custom_exceptions import APIException
from core.auth.jwt_middleware import require_jwt

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")
logger = get_app_logger()

# Endpoints de escritura requieren JWT
_WRITE_ENDPOINTS = {"rag.ingest_text", "rag.ingest_file", "rag.delete_document", "rag.delete_tenant"}


@rag_bp.before_request
def auth_check():
    """Verifica JWT solo para endpoints de escritura."""
    if request.endpoint in _WRITE_ENDPOINTS:
        return require_jwt()
    return None


def _get_rag_service():
    """Obtiene el servicio RAG del contenedor de dependencias."""
    return DependencyContainer.get("RAGService")


def _get_tenant_id_from_request() -> str:
    """
    Extrae tenant_id del request.

    Orden de precedencia:
    1. Header X-Tenant-ID
    2. Form-data tenant_id
    3. Query param tenant_id

    Raises:
        APIException: Si no se encuentra tenant_id
    """
    # 1. Header
    tenant_id = request.headers.get("X-Tenant-ID")

    # 2. Form-data
    if not tenant_id and request.form:
        tenant_id = request.form.get("tenant_id")

    # 3. Query params
    if not tenant_id:
        tenant_id = request.args.get("tenant_id")

    if not tenant_id:
        raise APIException(
            message="tenant_id es requerido. Proporciónalo en header X-Tenant-ID, form-data o query param.",
            status_code=400,
            code="MISSING_TENANT_ID",
        )

    return tenant_id


# Carpeta de subidas
UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@rag_bp.route("/ingest", methods=["POST"])
def ingest_text():
    """
    Ingesta texto directo al RAG del tenant.

    Form-data esperado:
    - tenant_id: ID del tenant (REQUERIDO para aislamiento)
    - text: contenido de texto a indexar (requerido)
    - user_id: identificador de usuario (opcional)
    - title: título del documento (opcional)

    Headers alternativos:
    - X-Tenant-ID: ID del tenant
    """
    tenant_id = _get_tenant_id_from_request()
    text = request.form.get("text")
    user_id = request.form.get("user_id")
    title = request.form.get("title")
    document_id = str(uuid.uuid4())

    if not text:
        raise APIException(
            message="text es requerido",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    rag = _get_rag_service()
    count = rag.ingest_text(
        tenant_id=tenant_id,
        document_id=document_id,
        text=text,
        user_id=user_id,
        title=title,
    )

    return jsonify({
        "ok": True,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "chunks_indexed": count,
    }), 200


@rag_bp.route("/ingest/file", methods=["POST"])
def ingest_file():
    """
    Ingiere un archivo (PDF/DOCX/TXT) al RAG del tenant.

    Form-data esperado:
    - file: archivo (requerido)
    - tenant_id: ID del tenant (REQUERIDO para aislamiento)
    - user_id: identificador de usuario (opcional)
    - title: título del documento (opcional)

    Headers alternativos:
    - X-Tenant-ID: ID del tenant
    """
    tenant_id = _get_tenant_id_from_request()
    user_id = request.form.get('user_id')
    title = request.form.get('title')

    if 'file' not in request.files:
        raise APIException(
            message="Falta el campo 'file' en form-data",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    file = request.files['file']

    if not file or file.filename == '':
        raise APIException(
            message="Archivo no proporcionado",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    filename = secure_filename(file.filename)

    # ID determinístico: mismo archivo + mismo tenant = mismo document_id
    # Esto permite reemplazar automáticamente el documento si se sube de nuevo
    document_id = hashlib.md5(f"{tenant_id}:{filename}".encode()).hexdigest()

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Extraer texto según extensión
    ext = os.path.splitext(filename)[1].lower()
    text = None

    if ext == ".pdf":
        from services.files_processing_service import process_pdf as _proc
        text = _proc(file_path)
    elif ext in (".docx", ".doc"):
        from services.files_processing_service import process_docx as _proc
        text = _proc(file_path)
    elif ext in (".txt",):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    else:
        raise APIException(
            message=f"Extensión no soportada: {ext}",
            status_code=400,
            code="UNSUPPORTED_FILE_EXTENSION",
        )

    if not text or not text.strip():
        raise APIException(
            message="No se pudo extraer texto del archivo",
            status_code=400,
            code="EMPTY_EXTRACTED_TEXT",
        )

    rag = _get_rag_service()

    # Borrar chunks anteriores del mismo archivo (si existen) antes de reingestar
    replaced = rag.delete_document(document_id, tenant_id=tenant_id)
    if replaced:
        logger.info(f"[RAG] Documento '{filename}' existente reemplazado para tenant='{tenant_id}'")

    count = rag.ingest_text(
        tenant_id=tenant_id,
        document_id=document_id,
        text=text,
        user_id=user_id,
        title=title or filename,
    )

    return jsonify({
        "ok": True,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "filename": filename,
        "chunks_indexed": count,
        "replaced": replaced,
    }), 200


@rag_bp.route("/search", methods=["GET"])
def search():
    """
    Busca en el RAG del tenant.

    Query params:
    - query: texto a buscar (requerido)
    - tenant_id: ID del tenant (REQUERIDO para aislamiento)
    - user_id: filtrar por usuario dentro del tenant (opcional)
    - top_k: número de resultados (opcional)
    - min_similarity: similitud mínima (opcional)

    Headers alternativos:
    - X-Tenant-ID: ID del tenant
    """
    query_text = request.args.get("query")
    tenant_id = _get_tenant_id_from_request()
    user_id = request.args.get("user_id")
    top_k = request.args.get("top_k", type=int)
    min_similarity = request.args.get("min_similarity", type=float)

    if not query_text:
        raise APIException(
            message="query es requerido",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    from core.config.settings import settings
    if not settings.rag_enabled:
        raise APIException(
            message="RAG está deshabilitado por configuración",
            status_code=503,
            code="RAG_DISABLED",
        )

    rag = _get_rag_service()
    results = rag.retrieve(
        query_text=query_text,
        tenant_id=tenant_id,
        top_k=top_k,
        user_id=user_id,
        min_similarity=min_similarity,
    )

    payload = [
        {
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "metadata": c.metadata,
            "similarity": float(score),
        }
        for c, score in results
    ]

    return jsonify({
        "ok": True,
        "tenant_id": tenant_id,
        "results": payload,
    })


@rag_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    """
    Elimina un documento del RAG del tenant.

    Query params:
    - tenant_id: ID del tenant (REQUERIDO)

    Headers alternativos:
    - X-Tenant-ID: ID del tenant
    """
    tenant_id = _get_tenant_id_from_request()

    rag = _get_rag_service()
    ok = rag.delete_document(doc_id, tenant_id=tenant_id)

    return jsonify({
        "ok": ok,
        "document_id": doc_id,
        "tenant_id": tenant_id,
    })


@rag_bp.route("/tenant", methods=["DELETE"])
def delete_tenant():
    """
    Elimina TODOS los documentos del tenant (reset completo de la colección RAG).

    Query params / header:
    - tenant_id: ID del tenant (REQUERIDO)

    ⚠️ Esta operación es irreversible.
    """
    tenant_id = _get_tenant_id_from_request()

    from core.config.settings import settings
    if not settings.rag_enabled:
        raise APIException(
            message="RAG está deshabilitado por configuración",
            status_code=503,
            code="RAG_DISABLED",
        )

    rag = _get_rag_service()
    ok = rag.delete_tenant_data(tenant_id)

    return jsonify({
        "ok": ok,
        "tenant_id": tenant_id,
        "message": f"Todos los datos RAG del tenant '{tenant_id}' eliminados correctamente.",
    })


@rag_bp.route("/stats", methods=["GET"])
def stats():
    """
    Obtiene estadísticas del RAG del tenant.

    Query params:
    - tenant_id: ID del tenant (REQUERIDO)
    - user_id: filtrar por usuario (opcional)

    Headers alternativos:
    - X-Tenant-ID: ID del tenant
    """
    tenant_id = _get_tenant_id_from_request()
    user_id = request.args.get("user_id")

    from core.config.settings import settings
    if not settings.rag_enabled:
        raise APIException(
            message="RAG está deshabilitado por configuración",
            status_code=503,
            code="RAG_DISABLED",
        )

    rag = _get_rag_service()
    count = rag.count_chunks(tenant_id=tenant_id, user_id=user_id)

    return jsonify({
        "ok": True,
        "tenant_id": tenant_id,
        "total_chunks": count,
    })