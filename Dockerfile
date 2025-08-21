# Base image
FROM python:3.11-slim

# System deps (optional: tesseract, ffmpeg, etc., if needed by your processing)
# Install ffmpeg for pydub/audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/Chatbot_IA

# Install Python deps first for better cache
COPY Chatbot_IA/requirements.txt /app/Chatbot_IA/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the rest of the code
COPY . /app

# Expose app port
EXPOSE 8082

# Default command is the web app with Gunicorn
CMD ["gunicorn", "openIAService.main:app", "--timeout", "120", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:8082"]
