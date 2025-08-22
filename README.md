# Chatbot_IA

Este repositorio implementa un modelo de chatbot inteligente que puede interactuar con usuarios a través de WhatsApp y Telegram, procesar archivos (PDF, DOCX, imágenes, audio), mantener contexto de conversación y aprovechar modelos de IA de OpenAI para generar respuestas avanzadas.

## Características principales

- **Integración con WhatsApp y Telegram:** Recibe y responde mensajes automáticamente en ambas plataformas.
- **Procesamiento asíncrono distribuido:** Sistema RQ Worker + Redis para manejar tareas pesadas sin bloquear webhooks.
- **Procesamiento de archivos:** Extrae texto de PDFs, DOCX, imágenes (OCR) y audios (STT).
- **Gestión de contexto:** Mantiene el historial de conversación por usuario y por tema.
- **Respuestas inteligentes:** Utiliza modelos de OpenAI (GPT-4o) para generar respuestas contextuales y analizar imágenes.
- **Soporte multilenguaje:** Responde en el idioma detectado del usuario (por defecto español).
- **API REST con Flask:** Expone endpoints para recibir mensajes y subir archivos.
- **Concurrencia:** Maneja múltiples usuarios y plataformas simultáneamente sin degradación de performance.

## Arquitectura del Sistema

### Componentes Principales

- **App Container**: Recibe webhooks de WhatsApp/Telegram y responde inmediatamente
- **RQ Worker Container**: Procesa tareas pesadas (OCR, transcripción, análisis) de forma asíncrona
- **Redis**: Cola de mensajes para comunicación entre containers
- **Volúmenes compartidos**: Base de datos SQLite y archivos subidos

### Flujo de Procesamiento

```
Webhook → App → Respuesta inmediata → Redis Queue → RQ Worker → Procesamiento → Respuesta final
```

## Estructura del repositorio

- `openIAService/main.py`: Punto de entrada principal de la API Flask.
- `openIAService/routes/`: Rutas para WhatsApp, Telegram y carga de archivos.
- `openIAService/services/`: Lógica de negocio para mensajería, procesamiento de archivos, contexto y conexión con OpenAI.
  - `task_queue_service.py`: Gestión de cola Redis RQ para procesamiento asíncrono
  - `tasks.py`: Funciones de procesamiento de archivos ejecutadas por el worker
- `openIAService/config.py`: Configuración de variables de entorno y rutas.
- `docker-compose.yml`: Orquestación de containers (app, rq-worker, redis)
- `Dockerfile`: Imagen principal de la aplicación
- `Dockerfile.rq`: Imagen dedicada para el RQ worker
- `local/uploads/`: Carpeta donde se almacenan archivos subidos temporalmente.
- `local/contextos.db`: Base de datos SQLite para almacenar el contexto de conversación.

## Instalación y Despliegue

### Opción 1: Docker Compose (Recomendado)

1. **Clona el repositorio**
   ```bash
   git clone <url-del-repo>
   cd Chatbot_IA
   ```

2. **Configura las variables de entorno**  
   Crea un archivo `.env` con tus claves:
   ```
   SECRET_KEY=tu_clave_secreta
   TOKEN_WHATSAPP=tu_token_whatsapp
   OPENAI_API_KEY=tu_api_key_openai
   TELEGRAM_TOKEN=tu_token_telegram
   REDIS_URL=redis://redis:6379/0
   ```

3. **Construye e inicia los servicios**
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Monitorea los logs**
   ```bash
   # Ver logs de la aplicación
   docker compose logs -f app
   
   # Ver logs del worker
   docker compose logs -f rq-worker
   
   # Ver todos los logs
   docker compose logs -f
   ```

### Opción 2: Instalación Local

1. **Instala las dependencias**
   ```bash
   pip install -r requirements.txt
   pip install rq redis
   ```

2. **Inicia Redis**
   ```bash
   redis-server
   ```

3. **Inicia el worker RQ**
   ```bash
   rq worker --url redis://localhost:6379/0
   ```

4. **Ejecuta el servidor**
   ```bash
   python openIAService/main.py
   ```

## Uso

- **WhatsApp:**  
  Configura el webhook de WhatsApp Business API para apuntar a `/whatsapp`. El bot procesará mensajes de texto, imágenes, audios y documentos.

- **Telegram:**  
  Configura el webhook de tu bot de Telegram para apuntar a `/webhook/telegram`.

- **Carga de archivos PDF:**  
  Puedes subir PDFs a través del endpoint `/upload-pdf/` para extraer y procesar su contenido.

## Ejemplo de flujo con procesamiento asíncrono

### Procesamiento de Imagen
1. Usuario envía imagen por WhatsApp/Telegram
2. **App responde inmediatamente**: "Procesando tu imagen..."
3. **Worker procesa**: OCR, análisis de contenido
4. **Respuesta final**: Descripción y análisis de la imagen

### Procesamiento de Audio
1. Usuario envía audio por WhatsApp/Telegram
2. **App responde inmediatamente**: "Procesando tu audio..."
3. **Worker procesa**: Transcripción de voz a texto
4. **Respuesta final**: Transcripción y respuesta contextual

### Procesamiento de Documento
1. Usuario envía PDF/DOCX por WhatsApp/Telegram
2. **App responde inmediatamente**: "Procesando tu documento..."
3. **Worker procesa**: Extracción de texto, análisis
4. **Respuesta final**: Resumen y capacidad de Q&A sobre el contenido

## Monitoreo y Debugging

### Logs Estructurados
El sistema incluye logs detallados para debugging:

```bash
# En app container
[ENQUEUE] WA image recipient=584128281479 context_id=default file_path=local/uploads/image.jpg

# En rq-worker container
[TASK-QUEUE] Enqueued RQ job func=openIAService.services.tasks.process_whatsapp_image job_id=abc123
[TASK] WA image START recipient=584128281479 context_id=default file_path=local/uploads/image.jpg
[TASK] WA image DONE recipient=584128281479 context_id=default
```

### Verificación de Estado
```bash
# Ver estado de servicios
docker compose ps

# Ver cola Redis
docker compose exec redis redis-cli
> LLEN default  # Ver trabajos pendientes
> KEYS *        # Ver todas las claves
```

## Ejemplos para probar el flujo MCP y el flujo estándar

**Caso 1: Activación del flujo MCP (búsqueda web + ChatGPT)**

Pregunta:
```
buscar: ¿Quién es el actual presidente de Francia?
```
*La IA debe activar el flujo MCP, buscar en la web y luego resumir la respuesta con ChatGPT.*

---

**Caso 2: Flujo estándar (solo ChatGPT, sin búsqueda web)**

Pregunta:
```
Explícame cómo funciona la fotosíntesis en las plantas.
```
*La IA debe responder usando solo ChatGPT y el contexto de conversación.*

## Personalización

Puedes modificar los servicios en `openIAService/services/` para agregar nuevas funcionalidades, como integración con otras plataformas, análisis de sentimiento, respuestas multimedia, etc.

## Contribuciones

¡Las contribuciones son bienvenidas! Abre un issue o pull request para sugerir mejoras.

---
