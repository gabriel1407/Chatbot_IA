"""
Rutas para conversación con RAG integrado.
Permite que el usuario hable con el modelo usando su base de conocimientos.
"""
from flask import Blueprint, request, jsonify
from infrastructure.ai.rag_llm_service import RAGLLMService
from core.logging.logger import get_app_logger

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
    try:
        user_id = request.form.get("user_id")
        query = request.form.get("query")
        top_k = request.form.get("top_k", default=5, type=int)
        system_prompt = request.form.get("system_prompt")
        
        if not user_id or not query:
            return jsonify({"error": "user_id y query son requeridos"}), 400
        
        # Generar respuesta
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
        
    except Exception as e:
        logger.exception("Error en /api/chat/rag")
        return jsonify({"ok": False, "error": str(e)}), 500


@chat_bp.route("/rag/debug", methods=["POST"])
def chat_with_rag_debug():
    """
    Igual que /chat/rag pero retorna también los chunks encontrados en RAG.
    Útil para debug y validación.
    """
    try:
        user_id = request.form.get("user_id")
        query = request.form.get("query")
        top_k = request.form.get("top_k", default=5, type=int)
        system_prompt = request.form.get("system_prompt")
        
        if not user_id or not query:
            return jsonify({"error": "user_id y query son requeridos"}), 400
        
        # Buscar en RAG
        rag_results = rag_llm.search_rag(user_id, query, top_k)
        
        # Construir prompt
        context_prompt = rag_llm.build_context_prompt(query, rag_results)
        
        # Generar respuesta
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
        
    except Exception as e:
        logger.exception("Error en /api/chat/rag/debug")
        return jsonify({"ok": False, "error": str(e)}), 500
