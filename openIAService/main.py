from flask import Flask, jsonify
from openIAService.routes.whatsapp_routes import whatsapp_bp
from openIAService.routes.telegram_routes import telegram_bp
from openIAService.routes.file_routes import file_bp
from openIAService.config import Config
import logging
from openIAService.services.metrics_service import start_metrics_logging, get_performance_report
from openIAService.services.task_queue_service import start_worker as start_task_worker
from openIAService.services.limiter import limiter
from decouple import config

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)
# Inicializa rate limiting (Flask-Limiter) con Redis si REDIS_URL está presente
REDIS_URL = config('REDIS_URL', default='')
limiter.init_app(app)

app.register_blueprint(whatsapp_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(file_bp)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Inicia logging periódico de métricas
start_metrics_logging()

# Inicia el worker de tareas en background
start_task_worker()

# Endpoint para consultar métricas
@app.route('/metrics', methods=['GET'])
def metrics():
    report = get_performance_report()
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8082, debug=True)
