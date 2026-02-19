"""
Admin Routes - Endpoints operativos y de diagnóstico.
Separa responsabilidades de rutas para mantener claridad arquitectónica.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify

from application.dto.channel_requests import SendMessageRequest
from application.dto.ai_requests import OllamaGenerationRequest
from core.ai.factory import get_ai_provider
from services.channel_adapters import get_unified_channel_service
from core.exceptions.custom_exceptions import APIException
from core.auth.jwt_middleware import require_jwt
from core.logging.logger import get_app_logger


admin_bp = Blueprint('admin', __name__, url_prefix='/api/v2')
logger = get_app_logger()

# Proteger todos los endpoints con JWT (health_check queda excluido en el middleware)
@admin_bp.before_request
def auth_check():
    return require_jwt()


def build_success_response(*, data=None, message=None, status_code=200):
    payload = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
    }
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return payload, status_code


@admin_bp.route('/channels/status', methods=['GET'])
def get_channels_status():
    """Obtiene el estado de todos los canales de comunicación."""
    unified_service = get_unified_channel_service()
    stats = unified_service.get_channel_stats()
    payload, status_code = build_success_response(data=stats)
    return jsonify(payload), status_code


@admin_bp.route('/conversation/<user_id>/summary', methods=['GET'])
def get_conversation_summary_v2(user_id: str):
    """Obtiene un resumen de la conversación de un usuario."""
    unified_service = get_unified_channel_service()
    context_id = request.args.get('context_id')
    summary = unified_service.message_handler.get_conversation_summary(user_id, context_id)
    payload, status_code = build_success_response(data=summary)
    return jsonify(payload), status_code


@admin_bp.route('/message/send', methods=['POST'])
def send_message_v2():
    """Endpoint para enviar mensajes programáticamente."""
    unified_service = get_unified_channel_service()
    data = request.get_json(silent=True)
    if not data:
        raise APIException(
            message="No se proporcionaron datos JSON",
            status_code=400,
            code="INVALID_JSON",
        )

    try:
        request_dto = SendMessageRequest.from_dict(data)
    except ValueError as validation_error:
        raise APIException(
            message=str(validation_error),
            status_code=400,
            code="VALIDATION_ERROR",
        )

    success, message, response_status = unified_service.send_outgoing_message(
        channel_name=request_dto.channel,
        recipient_id=request_dto.recipient_id,
        content=request_dto.content,
    )

    if not success:
        raise APIException(
            message=message,
            status_code=response_status,
            code="MESSAGE_SEND_ERROR",
        )

    payload, status_code = build_success_response(message=message, status_code=response_status)
    return jsonify(payload), status_code


@admin_bp.route('/health', methods=['GET'])
def health_check_v2():
    """Health check completo del sistema."""
    unified_service = get_unified_channel_service()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "components": {}
    }

    try:
        channel_stats = unified_service.get_channel_stats()
        health_status["components"]["channels"] = {
            "status": "healthy",
            "data": channel_stats
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["channels"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    try:
        unified_service.message_handler.get_conversation_summary("health_check")
        health_status["components"]["message_handler"] = {
            "status": "healthy",
            "test_completed": True
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["message_handler"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    try:
        from services.context_cleanup_service import create_context_cleanup_service
        cleanup_service = create_context_cleanup_service()
        cleanup_status = cleanup_service.get_status()
        health_status["components"]["context_cleanup"] = {
            "status": "healthy",
            "data": cleanup_status
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["context_cleanup"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@admin_bp.route('/architecture/info', methods=['GET'])
def get_architecture_info():
    """Obtiene información sobre la arquitectura implementada."""
    architecture_info = {
        "version": "2.0",
        "architecture": "Clean Architecture + SOLID",
        "patterns_implemented": [
            "Repository Pattern",
            "Strategy Pattern",
            "Adapter Pattern",
            "Factory Pattern",
            "Dependency Injection",
            "Use Cases (Clean Architecture)"
        ],
        "solid_principles": {
            "S": "Single Responsibility - Cada clase tiene una responsabilidad",
            "O": "Open/Closed - Extensible sin modificación",
            "L": "Liskov Substitution - Implementaciones intercambiables",
            "I": "Interface Segregation - Interfaces específicas",
            "D": "Dependency Inversion - Dependencias a abstracciones"
        },
        "layers": {
            "domain": "Entidades y lógica de negocio",
            "application": "Casos de uso y servicios",
            "infrastructure": "Implementaciones concretas",
            "presentation": "API y interfaces"
        },
        "improvements": [
            "Limpieza automática de contextos cada 24 horas",
            "Logging centralizado y estructurado",
            "Manejo unificado de múltiples canales",
            "Procesamiento de mensajes con estrategias",
            "Inyección de dependencias",
            "Testing más fácil y mantenible"
        ],
        "compatibility": "Mantiene compatibilidad con código existente mediante adaptadores",
        "migration_status": "Fase 4 en progreso - hardening y estandarización de respuestas"
    }

    payload, status_code = build_success_response(data=architecture_info)
    return jsonify(payload), status_code


@admin_bp.route('/ai/ollama/thinking', methods=['POST'])
def ollama_thinking_v2():
    """Prueba thinking en proveedor IA actual (idealmente Ollama)."""
    data = request.get_json(silent=True)
    if not data:
        raise APIException(
            message="No se proporcionaron datos JSON",
            status_code=400,
            code="INVALID_JSON",
        )

    try:
        request_dto = OllamaGenerationRequest.from_dict(data)
    except ValueError as validation_error:
        raise APIException(
            message=str(validation_error),
            status_code=400,
            code="VALIDATION_ERROR",
        )

    provider = get_ai_provider()
    result = provider.generate_text_with_thinking(
        prompt=request_dto.prompt,
        model=request_dto.model,
        temperature=request_dto.temperature,
        max_tokens=request_dto.max_tokens,
        think=request_dto.think,
    )

    payload, status_code = build_success_response(
        data={
            "provider": provider.__class__.__name__,
            "supports_thinking": provider.supports_thinking(),
            "result": result,
        }
    )
    return jsonify(payload), status_code


@admin_bp.route('/ai/ollama/stream', methods=['POST'])
def ollama_stream_v2():
    """Prueba streaming en proveedor IA actual (idealmente Ollama)."""
    data = request.get_json(silent=True)
    if not data:
        raise APIException(
            message="No se proporcionaron datos JSON",
            status_code=400,
            code="INVALID_JSON",
        )

    try:
        request_dto = OllamaGenerationRequest.from_dict(data)
    except ValueError as validation_error:
        raise APIException(
            message=str(validation_error),
            status_code=400,
            code="VALIDATION_ERROR",
        )

    provider = get_ai_provider()
    stream_chunks = provider.generate_text_stream(
        prompt=request_dto.prompt,
        model=request_dto.model,
        temperature=request_dto.temperature,
        max_tokens=request_dto.max_tokens,
        think=request_dto.think,
        stream=True,
    )

    max_chunks = int(data.get("max_chunks", 200) or 200)
    if max_chunks <= 0:
        max_chunks = 200

    chunks = []
    content_acc = ""
    thinking_acc = ""

    for index, chunk in enumerate(stream_chunks, start=1):
        if index > max_chunks:
            break
        chunk_dict = chunk.to_dict()
        chunks.append(chunk_dict)
        content_acc += chunk_dict.get("content", "")
        thinking_acc += chunk_dict.get("thinking", "")

    payload, status_code = build_success_response(
        data={
            "provider": provider.__class__.__name__,
            "supports_streaming": provider.supports_streaming(),
            "supports_thinking": provider.supports_thinking(),
            "chunks_count": len(chunks),
            "content": content_acc,
            "thinking": thinking_acc,
            "chunks": chunks,
        }
    )
    return jsonify(payload), status_code
