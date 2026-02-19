"""
Rutas para conversación con RAG integrado.
Permite que el usuario hable con el modelo usando su base de conocimientos.
"""
from flask import Blueprint, request, jsonify
from infrastructure.ai.rag_llm_service import RAGLLMService
from core.logging.logger import get_app_logger
from core.exceptions.custom_exceptions import APIException

logger = get_app_logger()
rag_llm = RAGLLMService()

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/rag", methods=["POST"])
def chat_with_rag():
    """
    Conversación con RAG integrado.
    El usuario pregunta algo y el modelo busca en su base de conocimientos.
    
    Body (form-data):
    - user_id: identificador del cliente (requerido)
    - query: pregunta del usuario (requerido)
    - top_k: número de chunks a buscar (opcional, default=5)
    - system_prompt: instrucción personalizada para el modelo (opcional)
    """
    user_id = request.form.get("user_id")
    query = request.form.get("query")
    top_k = request.form.get("top_k", default=5, type=int)
    system_prompt = request.form.get("system_prompt")

    if not user_id or not query:
        raise APIException(
            message="user_id y query son requeridos",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    response = rag_llm.generate_rag_response(
        user_id=user_id,
        query=query,
        system_prompt=system_prompt,
        top_k=top_k
    )

    return jsonify({
        "ok": True,
        "user_id": user_id,
        "query": query,
        "response": response
    }), 200


@chat_bp.route("/rag/debug", methods=["POST"])
def chat_with_rag_debug():
    """
    Igual que /chat/rag pero retorna también los chunks encontrados en RAG.
    Útil para debug y validación.
    """
    user_id = request.form.get("user_id")
    query = request.form.get("query")
    top_k = request.form.get("top_k", default=5, type=int)
    system_prompt = request.form.get("system_prompt")

    if not user_id or not query:
        raise APIException(
            message="user_id y query son requeridos",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    rag_results = rag_llm.search_rag(user_id, query, top_k)

    response = rag_llm.generate_rag_response(
        user_id=user_id,
        query=query,
        system_prompt=system_prompt,
        top_k=top_k
    )

    return jsonify({
        "ok": True,
        "user_id": user_id,
        "query": query,
        "rag_chunks": rag_results,
        "chunks_count": len(rag_results),
        "response": response
    }), 200
