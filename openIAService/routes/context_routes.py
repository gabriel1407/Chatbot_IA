"""
Context Management Routes - API para gestión y monitoreo de contextos.
Implementa Clean Code y RESTful principles.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from services.context_cleanup_service import create_context_cleanup_service
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger

context_bp = Blueprint('context', __name__, url_prefix='/api/context')
logger = get_app_logger()

# Instancia global del servicio de limpieza
cleanup_service = create_context_cleanup_service()


def build_success_response(*, data=None, status_code=200):
    payload = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
    }
    if data is not None:
        payload["data"] = data
    return payload, status_code

@context_bp.route('/status', methods=['GET'])
def get_context_status():
    """
    Obtiene el estado del sistema de contextos.
    
    Returns:
        JSON con estadísticas y estado del sistema
    """
    status = cleanup_service.get_status()
    payload, status_code = build_success_response(data=status)
    return jsonify(payload), status_code


@context_bp.route('/cleanup', methods=['POST'])
def trigger_manual_cleanup():
    """
    Ejecuta una limpieza manual de contextos.
    
    Returns:
        JSON con resultados de la limpieza
    """
    data = request.get_json(silent=True) or {}
    custom_threshold = data.get('threshold_hours')

    if custom_threshold is not None:
        try:
            threshold_value = int(custom_threshold)
            if threshold_value <= 0:
                raise ValueError("threshold_hours debe ser mayor que cero")
        except (TypeError, ValueError) as exc:
            raise APIException(
                message=f"threshold_hours inválido: {exc}",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        temp_service = create_context_cleanup_service()
        temp_service.threshold_hours = threshold_value
        cleanup_result = temp_service.cleanup_old_contexts()
    else:
        cleanup_result = cleanup_service.cleanup_old_contexts()

    payload, status_code = build_success_response(data=cleanup_result)
    return jsonify(payload), status_code


@context_bp.route('/stats', methods=['GET'])
def get_context_stats():
    """
    Obtiene estadísticas detalladas de contextos.
    
    Returns:
        JSON con estadísticas de la base de datos
    """
    stats = cleanup_service.repository.get_context_stats()
    payload, status_code = build_success_response(data=stats)
    return jsonify(payload), status_code


@context_bp.route('/config', methods=['GET'])
def get_cleanup_config():
    """
    Obtiene la configuración actual del sistema de limpieza.
    
    Returns:
        JSON con configuración actual
    """
    config = {
        "cleanup_interval_hours": cleanup_service.cleanup_interval_hours,
        "threshold_hours": cleanup_service.threshold_hours,
        "strategy": cleanup_service.cleanup_strategy.get_cleanup_description(),
        "is_running": cleanup_service._cleanup_thread is not None and cleanup_service._cleanup_thread.is_alive()
    }

    payload, status_code = build_success_response(data=config)
    return jsonify(payload), status_code


@context_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint para el sistema de contextos.
    
    Returns:
        JSON con estado de salud del sistema
    """
    is_running = cleanup_service._cleanup_thread is not None and cleanup_service._cleanup_thread.is_alive()

    try:
        cleanup_service.repository.get_context_stats()
        db_accessible = True
    except Exception as exc:
        logger.warning(f"No se pudo acceder a estadísticas de contexto: {exc}")
        db_accessible = False

    health_status = {
        "status": "healthy" if is_running and db_accessible else "unhealthy",
        "cleanup_service_running": is_running,
        "database_accessible": db_accessible,
        "last_cleanup": cleanup_service._last_cleanup.isoformat() if cleanup_service._last_cleanup else None
    }

    status_code = 200 if health_status["status"] == "healthy" else 503
    payload, _ = build_success_response(data=health_status, status_code=status_code)
    return jsonify(payload), status_code