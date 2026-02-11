from flask import Blueprint, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from core.logging.logger import get_app_logger
from core.config.dependencies import DependencyContainer

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")
logger = get_app_logger()


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
    try:
        user_id = request.form.get("user_id")
        text = request.form.get("text")
        title = request.form.get("title")
        document_id = str(uuid.uuid4())

        if not user_id or not text:
            return jsonify({"error": "user_id y text son requeridos"}), 400

        rag = _get_rag_service()
        count = rag.ingest_text(user_id=user_id, document_id=document_id, text=text, title=title)
        return jsonify({"ok": True, "document_id": document_id, "chunks_indexed": count}), 200
    except Exception as e:
        logger.exception("Error en /api/rag/ingest")
        return jsonify({"ok": False, "error": str(e)}), 500


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
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Falta el campo 'file' en form-data"}), 400

        file = request.files['file']
        user_id = request.form.get('user_id')
        title = request.form.get('title')

        if not user_id:
            return jsonify({"error": "user_id es requerido"}), 400

        if not file or file.filename == '':
            return jsonify({"error": "Archivo no proporcionado"}), 400

        # Generar document_id automático
        document_id = str(uuid.uuid4())
        
        filename = secure_filename(file.filename)
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
            return jsonify({"error": f"Extensión no soportada: {ext}"}), 400

        if not text or not text.strip():
            return jsonify({"error": "No se pudo extraer texto del archivo"}), 400

        rag = _get_rag_service()
        count = rag.ingest_text(user_id=user_id, document_id=document_id, text=text, title=title)

        return jsonify({
            "ok": True,
            "document_id": document_id,
            "filename": filename,
            "chunks_indexed": count
        }), 200
    except Exception as e:
        logger.exception("Error en /api/rag/ingest/file")
        return jsonify({"ok": False, "error": str(e)}), 500


@rag_bp.route("/search", methods=["GET"])
def search():
    """
    Busca en el RAG.
    
    Query params:
    - query: texto a buscar (requerido)
    - user_id: filtrar por usuario (opcional, busca globalmente si no se proporciona)
    - top_k: número de resultados (opcional)
    """
    try:
        query_text = request.args.get("query")
        user_id = request.args.get("user_id")  # Opcional
        top_k = request.args.get("top_k", type=int)
        min_similarity = request.args.get("min_similarity", type=float)

        if not query_text:
            return jsonify({"error": "query es requerido"}), 400

        from core.config.settings import settings
        if not settings.rag_enabled:
            return jsonify({"ok": False, "error": "RAG está deshabilitado por configuración"}), 503

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
    except Exception as e:
        logger.exception("Error en /api/rag/search")
        return jsonify({"ok": False, "error": str(e)}), 500


@rag_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    try:
        rag = _get_rag_service()
        ok = rag.delete_document(doc_id)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.exception("Error en DELETE /api/rag/documents/<id>")
        return jsonify({"ok": False, "error": str(e)}), 500
