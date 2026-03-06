FROM python:3.12-slim

# Evita archivos .pyc y activa salida sin buffer (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt

# Copiar código del servidor y el paquete de tools
COPY server.py ./
COPY tools/ ./tools/


# Puerto SSE del servidor MCP
EXPOSE 8083

# Healthcheck: comprueba que el puerto SSE esté escuchando.
# curl -f sobre /sse cuelga (SSE es streaming) → usamos TCP socket con Python.
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=15s \
    CMD python -c "\
import socket, sys; \
s = socket.socket(); \
s.settimeout(3); \
code = s.connect_ex(('localhost', 8083)); \
s.close(); \
sys.exit(0 if code == 0 else 1)"


CMD ["python", "server.py"]
