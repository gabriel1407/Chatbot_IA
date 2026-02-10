from flask import Blueprint, request, jsonify
from core.logging.logger import get_app_logger
from core.config.dependencies import DependencyContainer

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")
logger = get_app_logger()


def _get_rag_service():
    return DependencyContainer.get("RAGService")


@rag_bp.route("/ingest", methods=["POST"])
def ingest_text():
    try:
        data = request.get_json(force=True)
        user_id = data.get("user_id")
        document_id = data.get("document_id")
        text = data.get("text")
        title = data.get("title")
        metadata = data.get("metadata", {})

        if not user_id or not document_id or not text:
            return jsonify({"error": "user_id, document_id y text son requeridos"}), 400

        rag = _get_rag_service()
        count = rag.ingest_text(user_id=user_id, document_id=document_id, text=text, title=title, metadata=metadata)
        return jsonify({"ok": True, "chunks_indexed": count})
    except Exception as e:
        logger.exception("Error en /api/rag/ingest")
        return jsonify({"ok": False, "error": str(e)}), 500


@rag_bp.route("/search", methods=["GET"])
def search():
    try:
        user_id = request.args.get("user_id")
        query_text = request.args.get("query")
        top_k = request.args.get("top_k", type=int)

        if not user_id or not query_text:
            return jsonify({"error": "user_id y query son requeridos"}), 400

        rag = _get_rag_service()
        results = rag.retrieve(user_id=user_id, query_text=query_text, top_k=top_k)
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
