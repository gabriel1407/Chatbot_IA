"""
Improved Routes - Rutas mejoradas que usan la nueva arquitectura.
Implementa principios SOLID y Clean Architecture.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any

from services.channel_adapters import (
    UnifiedChannelService,
    ChannelType,
    get_unified_channel_service
)
from core.logging.logger import get_app_logger

# Blueprint para las nuevas rutas mejoradas
improved_bp = Blueprint('improved', __name__, url_prefix='/api/v2')

# Logger y servicio
logger = get_app_logger()
unified_service = get_unified_channel_service()


@improved_bp.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook_v2():
    """
    Webhook mejorado para WhatsApp que usa la nueva arquitectura.
    
    GET: Verificación del token
    POST: Procesamiento de mensajes
    """
    if request.method == 'GET':
        # Verificación del token de WhatsApp
        try:
            access_token = "E23431A21A991BE82FF3D79D5F1F8"
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            if token == access_token:
                logger.info("Token de WhatsApp verificado exitosamente")
                return challenge
            else:
                logger.warning("Token de WhatsApp inválido")
                return "Error", 400
        except Exception as e:
            logger.error(f"Error en verificación de token de WhatsApp: {e}")
            return "Error", 400
    
    elif request.method == 'POST':
        # Procesamiento de mensajes
        try:
            raw_data = request.get_json()
            if not raw_data:
                logger.warning("Webhook de WhatsApp recibido sin datos JSON")
                return jsonify({"status": "no_data"}), 200
            
            logger.info("Procesando webhook de WhatsApp con nueva arquitectura")
            
            # Usar el servicio unificado para procesar
            success = unified_service.process_webhook(ChannelType.WHATSAPP, raw_data)
            
            if success:
                logger.info("Webhook de WhatsApp procesado exitosamente")
            else:
                logger.warning("Webhook de WhatsApp procesado con errores")
            
            return jsonify({
                "status": "processed",
                "success": success,
                "timestamp": datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Error procesando webhook de WhatsApp: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500


@improved_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook_v2():
    """
    Webhook mejorado para Telegram que usa la nueva arquitectura.
    """
    try:
        raw_data = request.get_json()
        if not raw_data:
            logger.warning("Webhook de Telegram recibido sin datos JSON")
            return jsonify({"status": "no_data"}), 200
        
        logger.info("Procesando webhook de Telegram con nueva arquitectura")
        
        # Usar el servicio unificado para procesar
        success = unified_service.process_webhook(ChannelType.TELEGRAM, raw_data)
        
        if success:
            logger.info("Webhook de Telegram procesado exitosamente")
        else:
            logger.warning("Webhook de Telegram procesado con errores")
        
        return jsonify({
            "status": "processed",
            "success": success,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook de Telegram: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@improved_bp.route('/channels/status', methods=['GET'])
def get_channels_status():
    """
    Obtiene el estado de todos los canales de comunicación.
    """
    try:
        stats = unified_service.get_channel_stats()
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de canales: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@improved_bp.route('/conversation/<user_id>/summary', methods=['GET'])
def get_conversation_summary_v2(user_id: str):
    """
    Obtiene un resumen de la conversación de un usuario.
    """
    try:
        context_id = request.args.get('context_id')
        
        # Obtener resumen usando el handler mejorado
        summary = unified_service.message_handler.get_conversation_summary(user_id, context_id)
        
        return jsonify({
            "success": True,
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen de conversación: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@improved_bp.route('/message/send', methods=['POST'])
def send_message_v2():
    """
    Endpoint para enviar mensajes programáticamente.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No se proporcionaron datos JSON"
            }), 400
        
        # Validar campos requeridos
        required_fields = ['recipient_id', 'content', 'channel']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Campo requerido faltante: {field}"
                }), 400
        
        recipient_id = data['recipient_id']
        content = data['content']
        channel_name = data['channel'].lower()
        
        # Determinar canal
        if channel_name == 'whatsapp':
            channel = ChannelType.WHATSAPP
        elif channel_name == 'telegram':
            channel = ChannelType.TELEGRAM
        else:
            return jsonify({
                "success": False,
                "error": f"Canal no soportado: {channel_name}"
            }), 400
        
        # Obtener adapter y enviar mensaje
        adapter = unified_service.adapters.get(channel)
        if not adapter:
            return jsonify({
                "success": False,
                "error": f"Adapter no disponible para canal {channel_name}"
            }), 500
        
        from services.channel_adapters import OutgoingMessage
        message = OutgoingMessage(
            recipient_id=recipient_id,
            content=content,
            channel=channel
        )
        
        success = adapter.send_message(message)
        
        if success:
            logger.info(f"Mensaje enviado programáticamente a {channel_name}: {recipient_id}")
        else:
            logger.error(f"Error enviando mensaje programáticamente a {channel_name}")
        
        return jsonify({
            "success": success,
            "message": "Mensaje enviado" if success else "Error enviando mensaje",
            "timestamp": datetime.now().isoformat()
        }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error en send_message_v2: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@improved_bp.route('/health', methods=['GET'])
def health_check_v2():
    """
    Health check completo del sistema mejorado.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0",
            "components": {}
        }
        
        # Verificar canales
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
        
        # Verificar handler de mensajes
        try:
            test_summary = unified_service.message_handler.get_conversation_summary("health_check")
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
        
        # Verificar contexto y limpieza
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
        
    except Exception as e:
        logger.error(f"Error en health check v2: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@improved_bp.route('/architecture/info', methods=['GET'])
def get_architecture_info():
    """
    Obtiene información sobre la nueva arquitectura implementada.
    """
    try:
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
            "migration_status": "Fase 1 completada - Nueva arquitectura funcionando"
        }
        
        return jsonify({
            "success": True,
            "data": architecture_info,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo información de arquitectura: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500