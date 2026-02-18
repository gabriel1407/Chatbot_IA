from flask import Blueprint, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from core.logging.logger import get_app_logger
from core.config.dependencies import DependencyContainer
from core.exceptions.custom_exceptions import APIException
from core.auth.jwt_middleware import require_jwt

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")
logger = get_app_logger()

# Proteger ingesta y gestión de documentos con JWT
rag_bp.before_request(require_jwt)


def _get_rag_service():
    return DependencyContainer.get("RAGService")


# Carpeta de subidas (coherente con otros módulos)
UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@rag_bp.route("/ingest", methods=["POST"])
def ingest_text():
    """
    Ingesta texto directo al RAG como form-data.
    Form-data esperado:
    - user_id: identificador de usuario/cliente (requerido)
    - text: contenido de texto a indexar (requerido)
    - title: (opcional)
    """
    user_id = request.form.get("user_id")
    text = request.form.get("text")
    title = request.form.get("title")
    document_id = str(uuid.uuid4())

    if not user_id or not text:
        raise APIException(
            message="user_id y text son requeridos",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    rag = _get_rag_service()
    count = rag.ingest_text(user_id=user_id, document_id=document_id, text=text, title=title)
    return jsonify({"ok": True, "document_id": document_id, "chunks_indexed": count}), 200


@rag_bp.route("/ingest/file", methods=["POST"])
def ingest_file():
    """
    Ingresa un archivo (PDF/DOCX/TXT) al RAG.
    Form-data esperado:
    - file: archivo
    - user_id: identificador de usuario/cliente (requerido)
    - title: (opcional)
    
    Genera automáticamente un document_id único (UUID).
    """
    if 'file' not in request.files:
        raise APIException(
            message="Falta el campo 'file' en form-data",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    file = request.files['file']
    user_id = request.form.get('user_id')
    title = request.form.get('title')

    if not user_id:
        raise APIException(
            message="user_id es requerido",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    if not file or file.filename == '':
        raise APIException(
            message="Archivo no proporcionado",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    document_id = str(uuid.uuid4())

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

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
    count = rag.ingest_text(user_id=user_id, document_id=document_id, text=text, title=title)

    return jsonify({
        "ok": True,
        "document_id": document_id,
        "filename": filename,
        "chunks_indexed": count
    }), 200


@rag_bp.route("/search", methods=["GET"])
def search():
    """
    Busca en el RAG.
    
    Query params:
    - query: texto a buscar (requerido)
    - user_id: filtrar por usuario (opcional, busca globalmente si no se proporciona)
    - top_k: número de resultados (opcional)
    """
    query_text = request.args.get("query")
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
    results = rag.retrieve(query_text=query_text, top_k=top_k, user_id=user_id, min_similarity=min_similarity)
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
    return jsonify({"ok": True, "results": payload})


@rag_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    rag = _get_rag_service()
    ok = rag.delete_document(doc_id)
    return jsonify({"ok": ok})
