import multiprocessing
import os

# Workers y threads configurables por variables de entorno
workers = int(os.getenv("WEB_CONCURRENCY", max(1, multiprocessing.cpu_count() // 2)))
threads = int(os.getenv("GTHREADS", 4))
worker_class = os.getenv("WORKER_CLASS", "gthread")  # gthread para IO-bound
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8082")

# Cambia el directorio de trabajo a la carpeta de la app para que imports
# como 'routes', 'services', 'core' funcionen sin prefijos de paquete
chdir = "/app/openIAService"

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", 300))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))

# Estabilidad (reinicios periódicos para evitar fugas de memoria)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Logs
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# Cabeceras proxy (si se usa detrás de Nginx)
forwarded_allow_ips = "*"

