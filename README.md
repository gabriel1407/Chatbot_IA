# Chatbot_IA

Este repositorio implementa un modelo de chatbot inteligente que puede interactuar con usuarios a través de WhatsApp y Telegram, procesar archivos (PDF, DOCX, imágenes, audio), mantener contexto de conversación y aprovechar modelos de IA de OpenAI para generar respuestas avanzadas.

## Características principales

- **Integración con WhatsApp y Telegram:** Recibe y responde mensajes automáticamente en ambas plataformas.
- **Procesamiento de archivos:** Extrae texto de PDFs, DOCX, imágenes (OCR) y audios (STT).
- **Gestión de contexto:** Mantiene el historial de conversación por usuario y por tema.
- **Respuestas inteligentes:** Utiliza modelos de OpenAI (GPT-4o) para generar respuestas contextuales y analizar imágenes.
- **Soporte multilenguaje:** Responde en el idioma detectado del usuario (por defecto español).
- **API REST con Flask:** Expone endpoints para recibir mensajes y subir archivos.

## Estructura del repositorio

- `openIAService/main.py`: Punto de entrada principal de la API Flask.
- `openIAService/routes/`: Rutas para WhatsApp, Telegram y carga de archivos.
- `openIAService/services/`: Lógica de negocio para mensajería, procesamiento de archivos, contexto y conexión con OpenAI.
- `openIAService/config.py`: Configuración de variables de entorno y rutas.
- `local/uploads/`: Carpeta donde se almacenan archivos subidos temporalmente.
- `local/contextos.db`: Base de datos SQLite para almacenar el contexto de conversación.

## Instalación

1. **Clona el repositorio**
   ```bash
   git clone <url-del-repo>
   cd Chatbot_IA
   ```

2. **Instala las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura las variables de entorno**  
   Crea un archivo `.env` con tus claves:
   ```
   SECRET_KEY=tu_clave_secreta
   TOKEN_WHATSAPP=tu_token_whatsapp
   OPENAI_API_KEY=tu_api_key_openai
   TELEGRAM_TOKEN=tu_token_telegram
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

## Ejemplo de flujo

1. El usuario envía un mensaje o archivo por WhatsApp o Telegram.
2. El bot procesa el mensaje, mantiene el contexto y responde usando OpenAI.
3. Si el usuario envía un archivo, el bot extrae el texto y lo utiliza para responder preguntas sobre su contenido.

## Personalización

Puedes modificar los servicios en `openIAService/services/` para agregar nuevas funcionalidades, como integración con otras plataformas, análisis de sentimiento, respuestas multimedia, etc.

## Contribuciones

¡Las contribuciones son bienvenidas! Abre un issue o pull request para sugerir mejoras.

---
