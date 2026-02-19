FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalación de dependencias (seleccionable por ARG)
ARG REQUIREMENTS_FILE=requirements-base.txt
COPY ${REQUIREMENTS_FILE} /tmp/requirements.txt
RUN echo "Usando archivo de dependencias: ${REQUIREMENTS_FILE}" \
    && python -m pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt \
    && pip install gunicorn

# Copiar aplicación y configuración
COPY openIAService/ ./openIAService/
COPY monitor_logs.sh ./
COPY gunicorn.conf.py ./
COPY .env ./

EXPOSE 8082

WORKDIR /app

# Config Gunicorn por defecto (puedes sobreescribir vía env)
ENV WEB_CONCURRENCY=2 \
    GTHREADS=4 \
    GUNICORN_TIMEOUT=300 \
    GUNICORN_KEEPALIVE=5

CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
