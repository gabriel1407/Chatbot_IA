from flask import Flask
from routes.whatsapp_routes import whatsapp_bp
from routes.telegram_routes import telegram_bp
from routes.file_routes import file_bp
from routes.context_routes import context_bp
from routes.improved_routes import improved_bp
from config import Config
from services.context_cleanup_service import create_context_cleanup_service
import logging
import atexit

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

app.register_blueprint(whatsapp_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(file_bp)
app.register_blueprint(context_bp)
app.register_blueprint(improved_bp)  # Nueva arquitectura

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

if __name__ == '__main__':
    # Iniciar limpieza automática de contextos
    logging.info("Iniciando servicio de limpieza automática de contextos...")
    cleanup_service.start_automatic_cleanup()
    
    # Ejecutar limpieza inicial
    initial_cleanup = cleanup_service.cleanup_old_contexts()
    logging.info(f"Limpieza inicial: {initial_cleanup}")
    
    app.run(host="0.0.0.0", port=8082, debug=True)
