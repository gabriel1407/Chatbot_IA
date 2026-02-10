# 🤖 Chatbot IA - WhatsApp & Telegram

## 🚀 Sistema Inteligente de Chatbot con IA

Chatbot avanzado que integra **OpenAI GPT-4** para conversaciones inteligentes a través de WhatsApp y Telegram, con arquitectura limpia, principios SOLID y sistema automático de limpieza de contexto.

---

## ✨ Características Principales

### 🤖 **Inteligencia Artificial**
- **OpenAI GPT-4o** para conversaciones naturales
- **GPT-4o-mini** para respuestas rápidas
- **Análisis de imágenes** con visión por computadora
- **Procesamiento de documentos** (PDF, Word, texto)
- **Búsqueda web** integrada con SerpAPI

### 💬 **Multi-Canal**
- **WhatsApp** - Integración completa con Meta API
- **Telegram** - Bot nativo con todas las funciones
- **Adaptadores unificados** para manejo consistente

### 🏗️ **Arquitectura Avanzada**
- **Clean Architecture** con separación por capas
- **Principios SOLID** aplicados completamente
- **Repository Pattern** para persistencia
- **Dependency Injection** para bajo acoplamiento
- **Strategy Pattern** para algoritmos intercambiables

### 🧹 **Gestión de Contexto**
- **Limpieza automática** cada 24 horas
- **Contexto persistente** para conversaciones largas
- **Memoria vectorial** para búsqueda semántica
- **Optimización de tokens** para mejor rendimiento

---

## 🛠️ Instalación Rápida

### 1. **Clonar y preparar entorno**
```bash
git clone <repository-url>
cd Chatbot_IA
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2. **Configurar variables de entorno**
```bash
# Copia y edita las variables necesarias
cp .env.example .env
nano .env
```

**Variables requeridas:**
```bash
OPENAI_API_KEY=tu-clave-openai
TOKEN_WHATSAPP=tu-token-whatsapp
PHONE_NUMBER_ID=tu-numero-whatsapp
TELEGRAM_TOKEN=tu-token-telegram
SERPAPI_KEY=tu-clave-serpapi
```

### 3. **Ejecutar la aplicación**
```bash
cd openIAService
python main.py
```

### 4. (Opcional) Ejecutar con Docker Compose
```bash
cp .env.example .env
docker compose up --build
```
Servicios:
- App Flask: http://localhost:9001
- ChromaDB: http://localhost:9000 (vector store para RAG)

Nota sobre dependencias en Docker
- La imagen Docker usa un set mínimo en `requirements-base.txt` para garantizar builds estables (Flask, OpenAI, OCR/documentos, Telegram, ChromaDB, RAG).
- El archivo `requirements.txt` contiene librerías opcionales adicionales (MCP, FastAPI stack, proveedores extra) que pueden tener conflictos entre sí. Si necesitas incluirlas en la imagen, avísame y preparo perfiles/targets de build específicos.

---

## 📊 Monitoreo y Logs

### 🔍 **Monitor de Logs**
```bash
# Monitorear log principal
./monitor_logs.sh app

# Monitorear Telegram
./monitor_logs.sh telegram

# Monitorear WhatsApp  
./monitor_logs.sh whatsapp

# Ver todos los logs
./monitor_logs.sh all

# Estado de logs
./monitor_logs.sh status
```

### 📁 **Ubicación de Logs**
- **`openIAService/logs/app.log`** - Log principal
- **`openIAService/logs/telegram.log`** - Eventos Telegram
- **`openIAService/logs/whatsapp.log`** - Eventos WhatsApp

---

## 🌐 API Endpoints

### 📱 **Webhooks**
```bash
POST /webhook/whatsapp    # Webhook WhatsApp (v1)
POST /webhook/telegram    # Webhook Telegram (v1)
POST /api/v2/webhook/whatsapp  # Webhook WhatsApp mejorado
POST /api/v2/webhook/telegram  # Webhook Telegram mejorado
```

### 📊 **Monitoreo**
```bash
GET /api/v2/health               # Estado del sistema
GET /api/context/status          # Estado de contextos
POST /api/context/cleanup        # Limpiar contextos manualmente
GET /api/v2/architecture/info    # Información de arquitectura
```

### 📂 **Archivos**
```bash
POST /upload_file                # Subir archivos
GET /uploaded_files             # Lista de archivos
```

### 🔎 RAG (Retrieval Augmented Generation)
```bash
POST /api/rag/ingest            # Ingestar texto al vector store
GET  /api/rag/search            # Buscar contexto semántico
DELETE /api/rag/documents/:id   # Eliminar documento indexado
```
Ejemplos:
```bash
curl -X POST http://localhost:9001/api/rag/ingest \
	-H 'Content-Type: application/json' \
	-d '{"user_id":"u1","document_id":"doc-1","title":"Manual","text":"contenido a indexar"}'

curl 'http://localhost:9001/api/rag/search?user_id=u1&query=consulta'

Integración con Nginx del servidor (externo)
Si tienes un Nginx frontal (por ejemplo optimus.pegasoconsulting.net) y quieres publicar el servicio bajo /service_ia/, usa algo como:

location /service_ia/ {
		rewrite ^/service_ia/(.*)$ /$1 break;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
		proxy_read_timeout 300s;
		proxy_pass http://127.0.0.1:9001/;
}

Rendimiento y límites de recursos
- El contenedor ejecuta Gunicorn con worker_class gthread (óptimo para E/S: llamadas OpenAI, I/O).
- Ajusta concurrencia vía variables de entorno en docker-compose:
	- WEB_CONCURRENCY: número de workers (por defecto ~CPU/2 o 2)
	- GTHREADS: threads por worker (por defecto 4)
	- GUNICORN_TIMEOUT: timeout en segundos (por defecto 300)
	- GUNICORN_KEEPALIVE: keepalive en segundos (por defecto 5)
- Límites de recursos (opcionales) en docker-compose bajo deploy.resources.limits (cpus/memory).
```

---

## 🔧 Características Técnicas

### 📦 **Stack Tecnológico**
- **Python 3.12+**
- **Flask** - Framework web
- **SQLite** - Base de datos (contexto conversacional)
- **ChromaDB** - Vector DB (RAG)
- **OpenAI API** - Inteligencia artificial
- **Pydantic** - Validación de datos
- **Beautiful Soup** - Procesamiento HTML

### 🏛️ **Arquitectura**
```
openIAService/
├── domain/              # Entidades de negocio
├── application/         # Casos de uso
├── infrastructure/      # Implementaciones técnicas
│   ├── embeddings/      # OpenAI embeddings
│   └── vector_store/    # ChromaDB repository
├── core/               # Configuración y utilidades
├── services/           # Servicios de aplicación
└── routes/             # Endpoints API
```

### 🔄 **Patrones Implementados**
- **Repository** - Abstracción de datos
- **Factory** - Creación de objetos
- **Strategy** - Algoritmos intercambiables
- **Adapter** - Unificación de interfaces
- **Dependency Injection** - Inversión de dependencias

---

## 🚀 Uso del Sistema

### 💬 **Comandos de Chat**
El chatbot responde a mensajes naturales en español e inglés:

```
Usuario: "Hola, ¿cómo estás?"
Bot: "¡Hola! Estoy aquí para ayudarte..."

Usuario: "Analiza esta imagen" + [imagen]
Bot: [Análisis detallado de la imagen]

Usuario: "Busca información sobre Python"
Bot: [Resultados de búsqueda web + respuesta]
```

### 📄 **Procesamiento de Documentos**
- Sube PDFs, documentos Word o archivos de texto
- El sistema extrae y analiza el contenido
- Responde preguntas sobre el documento

### 🔍 **Búsqueda Web**
- Búsquedas automáticas cuando se necesita información actualizada
- Integración transparente con SerpAPI
- Resultados procesados y resumidos por IA

---

## 🛡️ Seguridad y Rendimiento

### 🔒 **Seguridad**
- Validación de tokens para todos los webhooks
- Sanitización de inputs de usuario
- Logs de auditoría completos
- Variables de entorno para credenciales

### ⚡ **Rendimiento**
- Limpieza automática de contexto (24h)
- Optimización de tokens para reducir costos
- Cache de respuestas frecuentes
- Logging asíncrono para no bloquear

---

## 📈 Métricas y Monitoreo

### 📊 **Métricas Disponibles**
- Número de conversaciones activas
- Uso de tokens OpenAI
- Tiempo de respuesta promedio
- Errores y excepciones

### 🔍 **Comandos de Diagnóstico**
```bash
# Ver estadísticas de contexto
curl http://localhost:8082/api/context/status

# Forzar limpieza de contextos
curl -X POST http://localhost:8082/api/context/cleanup

# Estado general del sistema
curl http://localhost:8082/api/v2/health
```

---

## 🤝 Contribución

### 📝 **Para Desarrolladores**
1. Fork del repositorio
2. Crear rama de feature
3. Seguir principios SOLID
4. Mantener cobertura de tests
5. Documentar cambios

### 🐛 **Reportar Issues**
- Incluir logs relevantes
- Describir pasos para reproducir
- Especificar versión de Python
- Adjuntar configuración (sin credenciales)

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 📞 Soporte

- **📧 Email**: carvajalgabriel1407@gmail.com
- **🐙 GitHub**: [gabriel1407](https://github.com/gabriel1407)
- **📁 Proyecto**: [Chatbot_IA](https://github.com/gabriel1407/Chatbot_IA)

---

*Última actualización: Noviembre 2025*