"""
Context Management Routes - API para gestión y monitoreo de contextos.
Implementa Clean Code y RESTful principles.
"""
from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from services.context_cleanup_service import create_context_cleanup_service

context_bp = Blueprint('context', __name__, url_prefix='/api/context')

# Instancia global del servicio de limpieza
cleanup_service = create_context_cleanup_service()

@context_bp.route('/status', methods=['GET'])
def get_context_status():
    """
    Obtiene el estado del sistema de contextos.
    
    Returns:
        JSON con estadísticas y estado del sistema
    """
    try:
        status = cleanup_service.get_status()
        return jsonify({
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo estado de contexto: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@context_bp.route('/cleanup', methods=['POST'])
def trigger_manual_cleanup():
    """
    Ejecuta una limpieza manual de contextos.
    
    Returns:
        JSON con resultados de la limpieza
    """
    try:
        # Verificar si se envió un threshold personalizado
        data = request.get_json() or {}
        custom_threshold = data.get('threshold_hours')
        
        if custom_threshold:
            # Crear servicio temporal con threshold personalizado
            temp_service = create_context_cleanup_service()
            temp_service.threshold_hours = custom_threshold
            cleanup_result = temp_service.cleanup_old_contexts()
        else:
            cleanup_result = cleanup_service.cleanup_old_contexts()
        
        return jsonify({
            "success": True,
            "data": cleanup_result,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error en limpieza manual: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@context_bp.route('/stats', methods=['GET'])
def get_context_stats():
    """
    Obtiene estadísticas detalladas de contextos.
    
    Returns:
        JSON con estadísticas de la base de datos
    """
    try:
        stats = cleanup_service.repository.get_context_stats()
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@context_bp.route('/config', methods=['GET'])
def get_cleanup_config():
    """
    Obtiene la configuración actual del sistema de limpieza.
    
    Returns:
        JSON con configuración actual
    """
    try:
        config = {
            "cleanup_interval_hours": cleanup_service.cleanup_interval_hours,
            "threshold_hours": cleanup_service.threshold_hours,
            "strategy": cleanup_service.cleanup_strategy.get_cleanup_description(),
            "is_running": cleanup_service._cleanup_thread is not None and cleanup_service._cleanup_thread.is_alive()
        }
        
        return jsonify({
            "success": True,
            "data": config,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo configuración: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@context_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint para el sistema de contextos.
    
    Returns:
        JSON con estado de salud del sistema
    """
    try:
        # Verificar estado del servicio
        is_running = cleanup_service._cleanup_thread is not None and cleanup_service._cleanup_thread.is_alive()
        
        # Verificar acceso a la base de datos
        try:
            stats = cleanup_service.repository.get_context_stats()
            db_accessible = True
        except Exception:
            db_accessible = False
        
        health_status = {
            "status": "healthy" if is_running and db_accessible else "unhealthy",
            "cleanup_service_running": is_running,
            "database_accessible": db_accessible,
            "last_cleanup": cleanup_service._last_cleanup.isoformat() if cleanup_service._last_cleanup else None
        }
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return jsonify({
            "success": True,
            "data": health_status,
            "timestamp": datetime.now().isoformat()
        }), status_code
        
    except Exception as e:
        logging.error(f"Error en health check: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500