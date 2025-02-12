from flask import Flask
from routes.whatsapp_routes import whatsapp_bp
from routes.file_routes import file_bp
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

app.register_blueprint(whatsapp_bp)
app.register_blueprint(file_bp)

# Configuración de logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8082, debug=True)
