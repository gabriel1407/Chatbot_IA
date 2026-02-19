from flask import Flask, request
from routes.whatsapp_routes import whatsapp_bp
from routes.telegram_routes import telegram_bp
from routes.file_routes import file_bp
from routes.context_routes import context_bp
from routes.improved_routes import improved_bp
from routes.admin_routes import admin_bp
from routes.rag_routes import rag_bp
from routes.chat_routes import chat_bp
from routes.tenant_routes import tenant_bp
from routes.auth_routes import auth_bp
from routes.tenant_channel_routes import tenant_channel_bp
from core.config.settings import settings
from services.context_cleanup_service import create_context_cleanup_service
import logging
import atexit
from core.config.dependencies import initialize_dependencies
from core.exceptions.http_handlers import register_http_error_handlers

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config['UPLOAD_FOLDER'] = settings.upload_folder

register_http_error_handlers(app)

app.register_blueprint(whatsapp_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(file_bp)
app.register_blueprint(context_bp)
app.register_blueprint(improved_bp)  # Nueva arquitectura
app.register_blueprint(admin_bp)  # Endpoints operativos v2
app.register_blueprint(rag_bp)  # Endpoints RAG
app.register_blueprint(chat_bp)  # Chat con RAG integrado
app.register_blueprint(tenant_bp)  # Configuración de tenants (clientes)
app.register_blueprint(auth_bp)  # Autenticación JWT
app.register_blueprint(tenant_channel_bp)  # Canales por tenant (multi-tenant routing)

# Inicializar dependencias al importar el módulo (útil para WSGI/Gunicorn)
initialize_dependencies()

# Log de configuración RAG a inicio
logging.info(
    f"[Settings] RAG_ENABLED={settings.rag_enabled}, RAG_CHAT_TOP_K={getattr(settings, 'rag_chat_top_k', None)}, RAG_GLOBAL_MIN_SIMILARITY={getattr(settings, 'rag_global_min_similarity', None)}"
)

# Inicializar servicio de limpieza automática de contextos
cleanup_service = create_context_cleanup_service()

# Función para limpiar al cerrar la aplicación
def cleanup_on_exit():
    """Detiene servicios de background al cerrar la aplicación."""
    logging.info("Cerrando aplicación...")
    cleanup_service.stop_automatic_cleanup()
    logging.info("Servicios de background detenidos")

# Registrar función de limpieza al cerrar
atexit.register(cleanup_on_exit)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Loggear cada request entrante (método, ruta, IP) para depurar webhooks
@app.before_request
def log_request_info():
    try:
        logging.info(f"Incoming {request.method} {request.path} from {request.remote_addr}")
    except Exception:
        pass

if __name__ == '__main__':
    # Iniciar limpieza automática de contextos
    logging.info("Iniciando servicio de limpieza automática de contextos...")
    cleanup_service.start_automatic_cleanup()
    
    # Ejecutar limpieza inicial
    initial_cleanup = cleanup_service.cleanup_old_contexts()
    logging.info(f"Limpieza inicial: {initial_cleanup}")
    
    app.run(host="0.0.0.0", port=8082, debug=True)
