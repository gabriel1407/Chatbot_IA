# 🤖 Chatbot IA - WhatsApp & Telegram

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.0-lightgrey.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![AI](https://img.shields.io/badge/AI-OpenAI%20%7C%20Gemini%20%7C%20Ollama-orange.svg)

## 🚀 Sistema Inteligente de Chatbot Multi-Proveedor con IA

Chatbot avanzado con soporte para **múltiples proveedores de IA** (OpenAI, Gemini, Ollama) para conversaciones inteligentes a través de WhatsApp y Telegram, con arquitectura limpia, principios SOLID, RAG (Retrieval Augmented Generation) y sistema automático de limpieza de contexto.

---

## ✨ Características Principales

### 🤖 **Inteligencia Artificial Multi-Proveedor**
- **OpenAI GPT-4o** / **GPT-4o-mini** - Conversaciones naturales con el modelo líder
- **Google Gemini 2.5** - IA multimodal de próxima generación
- **Ollama** - Modelos locales y en la nube (soporte para modelos customizados)
- **Cambio dinámico de proveedor** - Configurable via variable de entorno
- **Análisis de imágenes** con visión por computadora
- **Procesamiento de documentos** (PDF, Word, texto)
- **Búsqueda web** integrada con SerpAPI

### 🎯 **RAG (Retrieval Augmented Generation)**
- **Embeddings multi-proveedor**:
  - OpenAI: `text-embedding-3-small` (1536 dims)
  - Gemini: `gemini-embedding-001` (768 dims)
  - Ollama: `embeddinggemma`, `qwen3-embedding` (768 dims)
- **ChromaDB** como vector store
- **Búsqueda semántica** para contexto relevante
- **Indexación automática** de documentos

### 💬 **Multi-Canal**
- **WhatsApp** - Integración completa con Meta API
- **Telegram** - Bot nativo con todas las funciones

### 🏗️ **Arquitectura Avanzada**
- **Clean Architecture** con separación por capas (Domain, Application, Infrastructure)
- **Principios SOLID** aplicados completamente
- **Dependency Injection** para bajo acoplamiento
- **Strategy Pattern** para algoritmos intercambiables
- **Factory Pattern** para creación de proveedores
- **Adapter Pattern** para unificación de interfaces
- **Memoria vectorial** para búsqueda semántica
- **Optimización de tokens** para mejor rendimiento
---

## 🔄 Cambiar entre Proveedores de IA

El sistema soporta **3 proveedores de IA** con cambio dinámico mediante configuración:

### 📊 **Comparativa de Proveedores**

| Característica | OpenAI | Gemini | Ollama |
|---------------|--------|---------|---------|
| **Texto** | gpt-4o-mini<br>gpt-4o | gemini-2.5-flash-lite<br>gemini-2.0-flash | Modelos locales<br>(llama2, mistral, etc.) |
| **Embeddings** | text-embedding-3-small<br>(1536 dims) | gemini-embedding-001<br>(768 dims) | embeddinggemma<br>qwen3-embedding<br>(768 dims) |
| **Latencia** | 1-3s | 1-2s | Variable<br>(depende del hardware) |
| **Costo** | $$$ | $$ | Gratis (local)<br>$ (cloud) |
| **Offline** | ❌ No | ❌ No | ✅ Sí (local) |
| **Visión** | ✅ Sí | ✅ Sí | ⚠️ Algunos modelos |
| **RAG** | ✅ Sí | ✅ Sí | ✅ Sí |

### ⚙️ **Configuración por Proveedor**

#### **OpenAI**
```bash
# .env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### **Google Gemini**
```bash
# .env
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

#### **Ollama (Local)**
```bash
# .env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=embeddinggemma

# Asegúrate de tener Ollama corriendo:
# ollama serve
# ollama pull llama2
# ollama pull embeddinggemma
```

#### **Ollama (Cloud)**
```bash
# .env
AI_PROVIDER=ollama
OLLAMA_URL=https://api.ollama.com
OLLAMA_MODEL=tu-modelo-cloud
OLLAMA_EMBEDDING_MODEL=embeddinggemma
OLLAMA_API_KEY=tu-api-key
```

### 🔄 **Cambio en Tiempo Real**
```bash
# Cambiar proveedor (requiere reiniciar contenedor)
docker compose down
# Editar .env con nuevo AI_PROVIDER
docker compose up -d
```

---

## 🎯 RAG (Retrieval Augmented Generation)

### 📚 **Cómo Funciona**

1. **Indexación**: Los documentos se dividen en chunks y se generan embeddings
2. **Búsqueda**: Las consultas se convierten en embeddings y se buscan chunks similares
3. **Generación**: El LLM usa los chunks relevantes como contexto para responder

### 🔧 **Configuración RAG**

```bash
# .env
RAG_ENABLED=True
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=5
RAG_MIN_SIMILARITY=0.7
```

### 📝 **Ingestar Documentos**

```bash
# Texto directo
curl -X POST http://localhost:9001/service_ia/api/rag/ingest \
  -F "user_id=user123" \
  -F "text=Contenido del documento..." \
  -F "title=Mi Documento"

# Archivo PDF/DOCX
curl -X POST http://localhost:9001/service_ia/api/rag/ingest/file \
  -F "user_id=user123" \
  -F "file=@documento.pdf" \
  -F "title=Manual de Usuario"
```

### 🔍 **Buscar Contexto**

```bash
# Búsqueda semántica
curl "http://localhost:9001/service_ia/api/rag/search?query=¿Cómo+configurar+el+sistema?&top_k=5"

# Búsqueda por usuario
curl "http://localhost:9001/service_ia/api/rag/search?user_id=user123&query=mi+consulta"
```

### 🗑️ **Eliminar Documentos**

```bash
curl -X DELETE http://localhost:9001/service_ia/api/rag/documents/doc-id-123
```

### 🎯 **Embeddings por Proveedor**

El sistema **automáticamente usa el modelo de embeddings** correspondiente al proveedor seleccionado:

- **OpenAI**: Usa `text-embedding-3-small` para generar vectores de 1536 dimensiones
- **Gemini**: Usa `gemini-embedding-001` optimizado para RAG (768 dims)
- **Ollama**: Usa modelos específicos como `embeddinggemma` o `qwen3-embedding` (768 dims)

**Ejemplo de configuración mixta** (no recomendado):
```bash
# Si quieres usar OpenAI para chat pero Ollama para embeddings,
# necesitarías dos instancias o modificar el código.
# Por defecto, ambos usan el mismo proveedor configurado en AI_PROVIDER.
```

---

## 🛠️ Instalación Rápida

git clone <repository-url>
cd Chatbot_IA
source env/bin/activate
pip install -r requirements.txt
```

### 2. **Configurar variables de entorno**
```bash
# Copia y edita las variables necesarias
cp .env.example .env
nano .env
```

**Variables principales:**
```bash
# Selección de proveedor de IA (openai, gemini, ollama)
AI_PROVIDER=gemini

# OpenAI (si usas AI_PROVIDER=openai)
OPENAI_API_KEY=tu-clave-openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Google Gemini (si usas AI_PROVIDER=gemini)
GEMINI_API_KEY=tu-clave-gemini
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

# Ollama (si usas AI_PROVIDER=ollama)
OLLAMA_URL=http://localhost:11434  # o https://api.ollama.com para cloud
OLLAMA_MODEL=llama2  # Modelo para generación de texto
OLLAMA_EMBEDDING_MODEL=embeddinggemma  # Modelo para embeddings
OLLAMA_API_KEY=tu-api-key-opcional  # Solo si usas Ollama Cloud

# Canales de mensajería
TOKEN_WHATSAPP=tu-token-whatsapp
PHONE_NUMBER_ID=tu-numero-whatsapp
TELEGRAM_TOKEN=tu-token-telegram

# Búsqueda web (opcional)
SERPAPI_KEY=tu-clave-serpapi

# RAG (Retrieval Augmented Generation)
RAG_ENABLED=True
CHROMA_HOST=chroma
CHROMA_PORT=8000
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
./monitor_logs.sh telegram


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
GET /api/v2/channels/status      # Estado de canales (admin)
GET /api/v2/conversation/:id/summary # Resumen por usuario (admin)
POST /api/v2/message/send        # Envío programático (admin)
POST /api/v2/ai/ollama/thinking  # Prueba thinking del proveedor IA actual
POST /api/v2/ai/ollama/stream    # Prueba streaming del proveedor IA actual
GET /api/context/status          # Estado de contextos
POST /api/context/cleanup        # Limpiar contextos manualmente
GET /api/v2/architecture/info    # Información de arquitectura
```

### 🧾 Contrato de Respuestas y Errores

Todas las rutas HTTP nuevas/refactorizadas usan formato homogéneo.

Respuesta exitosa:
```json
{
  "success": true,
  "data": {},
  "timestamp": "2026-02-12T12:00:00"
}
```

Respuesta de error (global handler):
```json
{
  "success": false,
  "error": "mensaje descriptivo",
  "code": "VALIDATION_ERROR",
  "timestamp": "2026-02-12T12:00:00"
}
```

Códigos frecuentes:
- `VALIDATION_ERROR`
- `INVALID_JSON`
- `RAG_DISABLED`
- `MESSAGE_SEND_ERROR`
- `UNSUPPORTED_FILE_EXTENSION`
- `UNHANDLED_ERROR`

### 🧠 Ollama Thinking + Streaming en canales

Flags de activación:
```bash
OLLAMA_CHANNEL_STREAMING_ENABLED=True
OLLAMA_CHANNEL_THINKING_ENABLED=False
OLLAMA_STREAM_CHUNK_SIZE=120
OLLAMA_STREAM_MAX_UPDATES=20
```

Comportamiento por canal:
- **Telegram**: simula streaming editando un único mensaje (`Pensando...` → texto parcial → respuesta final).
- **WhatsApp**: envía respuesta final; opcionalmente puede enviar aviso de procesamiento antes del resultado.

Nota: mostrar el campo `thinking` al usuario final no suele ser recomendado en producción. Se puede mantener para debug/admin.

### 📂 **Archivos**
```bash
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
- **Flask** + **Gunicorn** - Framework web y WSGI server
- **SQLite** - Base de datos (contexto conversacional)
- **ChromaDB** - Vector DB (RAG)
- **Proveedores de IA**:
  - **OpenAI API** (gpt-4o, gpt-4o-mini)
  - **Google Gemini API** (gemini-2.5-flash-lite)
  - **Ollama** (llama2, mistral, modelos customizados)
- **Pydantic** - Validación de datos y settings
- **Beautiful Soup** - Procesamiento HTML
- **PyMuPDF** - Extracción de texto de PDFs
- **python-docx** - Procesamiento de documentos Word

### 🏛️ **Arquitectura (Clean Architecture + SOLID)**
```
openIAService/
├── domain/                    # 🔵 CAPA DE DOMINIO
│   ├── entities/              # Entidades de negocio
│   ├── repositories/          # Interfaces de repositorios
│   └── value_objects/         # Objetos de valor
│
├── application/               # 🟢 CAPA DE APLICACIÓN
│   ├── dto/                   # Data Transfer Objects
│   ├── services/              # Servicios de aplicación
│   └── use_cases/             # Casos de uso
│
├── infrastructure/            # 🟡 CAPA DE INFRAESTRUCTURA
│   ├── ai/                    # Adaptadores de proveedores IA
│   │   ├── openai_adapter.py
│   │   ├── gemini_adapter.py
│   │   └── ollama_adapter.py
│   ├── embeddings/            # Servicio de embeddings multi-proveedor
│   ├── vector_store/          # ChromaDB repository
│   ├── persistence/           # SQLite repository
│   ├── messaging/             # WhatsApp, Telegram adapters
│   └── web_search/            # SerpAPI integration
│
├── core/                      # ⚙️ CORE
│   ├── config/                # Settings, dependencies
│   │   ├── settings.py        # Pydantic settings
│   │   └── dependencies.py    # DI container
│   ├── ai/
│   │   ├── providers.py       # AIProvider interface
│   │   └── factory.py         # get_ai_provider() factory
│   ├── exceptions/            # Custom exceptions
│   └── logging/               # Structured logging
│
├── services/                  # 🔧 SERVICIOS
│   ├── openia_service.py      # Orquestación IA
│   ├── channel_adapters.py    # WhatsApp/Telegram unificado
│   └── context_cleanup_service.py
│
└── routes/                    # 🌐 API ENDPOINTS
    ├── whatsapp_routes.py
    ├── telegram_routes.py
    ├── rag_routes.py          # RAG endpoints
    └── chat_routes.py         # Chat con RAG
```

### 🔄 **Patrones de Diseño Implementados**
- **Repository Pattern** - Abstracción de datos (SQLite, ChromaDB)
- **Factory Pattern** - Creación de proveedores IA (`get_ai_provider()`)
- **Strategy Pattern** - Algoritmos intercambiables (limpieza, procesamiento)
- **Adapter Pattern** - Unificación de interfaces (OpenAI, Gemini, Ollama)
- **Dependency Injection** - Inversión de dependencias (DI Container)
- **Service Locator** - Registro centralizado de servicios

---

## 🚀 Uso del Sistema

### 💬 **Comandos de Chat**
El chatbot responde a mensajes naturales en español e inglés con cualquier proveedor:

```
Usuario: "Hola, ¿cómo estás?"
Bot: "¡Hola! Estoy aquí para ayudarte..."

Usuario: "Analiza esta imagen" + [imagen]
Bot: [Análisis detallado de la imagen] (OpenAI/Gemini)

Usuario: "Busca información sobre Python"
Bot: [Resultados de búsqueda web + respuesta]

Usuario: "Resume este documento" + [documento]
Bot: [Resumen generado usando RAG si está habilitado]
```

### 📄 **Procesamiento de Documentos con RAG**
1. Sube PDFs, documentos Word o archivos de texto vía `/api/rag/ingest/file`
2. El sistema:
   - Extrae el texto
   - Lo divide en chunks
   - Genera embeddings con el proveedor configurado
   - Indexa en ChromaDB
3. Las consultas posteriores buscan en el contexto indexado
4. El LLM genera respuestas basadas en el contenido real del documento

### 🔍 **Búsqueda Web**
- Búsquedas automáticas cuando se necesita información actualizada
- Integración transparente con SerpAPI
- Resultados procesados y resumidos por IA

### 🎯 **Características Avanzadas**

#### **Fast-Path para Preguntas Simples**
El sistema detecta preguntas triviales y responde sin LLM para reducir latencia:
- "Hola", "Buenas", "Quien eres"
- Respuestas instantáneas en < 100ms

#### **Optimización de Contexto**
- Limpieza automática cada 24 horas
- Resumen de conversaciones largas
- Gestión de tokens para reducir costos

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

## 🔧 Troubleshooting

### ❌ **Problemas Comunes**

#### **Error 401 con Ollama embeddings**
```bash
# Problema: unauthorized (status code: 401)
# Causa: Modelo de embeddings no disponible o API key incorrecta

# Solución 1: Verificar que el modelo esté descargado (local)
ollama pull embeddinggemma
ollama list  # Verificar que aparece embeddinggemma

# Solución 2: Verificar API key (cloud)
# Asegúrate de que OLLAMA_API_KEY esté configurada correctamente en .env

# Solución 3: Usar modelos alternativos
OLLAMA_EMBEDDING_MODEL=qwen3-embedding  # o all-minilm
```

#### **Gemini: "model is required"**
```bash
# Problem: El modelo está vacío
# Solución: Agregar explícitamente en .env
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

#### **RAG no encuentra resultados**
```bash
# Verificar que RAG esté habilitado
RAG_ENABLED=True

# Verificar que ChromaDB esté corriendo
docker compose ps  # Debe mostrar 'chroma' como 'running'

# Ver logs de ChromaDB
docker compose logs chroma

# Reiniciar ChromaDB
docker compose restart chroma
```

#### **Cambio de proveedor no surte efecto**
```bash
# Asegúrate de reiniciar el contenedor
docker compose down
docker compose up -d

# Verificar logs de inicialización
docker compose logs app | grep "initialized"
# Debe mostrar: "Ollama adapter initialized" o "Gemini generate_text"
```

### 🐛 **Debug Logs**

```bash
# Ver logs en tiempo real
docker compose logs -f app

# Buscar errores específicos
docker compose logs app | grep ERROR

# Ver inicialización de proveedores
docker compose logs app | grep -A3 "Inicializando dependencias"
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

*Última actualización: Febrero 2026*

## 📄 Changelog Reciente

### v2.1.0 (Febrero 2026)
- ✅ **Fase 3 completada**: extracción de generación de respuestas a `ResponseGenerationUseCase`
- ✅ **DI centralizado** para `MessageHandler` y `UnifiedChannelService`
- ✅ **Fase 4 iniciada y aplicada**: manejo global de errores HTTP con `APIException`
- ✅ **Rutas homogeneizadas**: `admin_routes`, `rag_routes`, `chat_routes`, `context_routes`, `file_routes`
- ✅ **Semántica HTTP consistente** en validaciones y errores de negocio

### v2.0.0 (Febrero 2026)
- ✅ **Soporte multi-proveedor**: OpenAI, Gemini, Ollama
- ✅ **RAG mejorado** con embeddings específicos por proveedor
- ✅ **Arquitectura SOLID** completamente refactorizada
- ✅ **Dependency Injection** con container centralizado
- ✅ **Fast-path** para preguntas simples
- ✅ **Ollama adapter** usando librería oficial
- ✅ **Gemini embeddings** con gemini-embedding-001

### v1.0.0 (Noviembre 2025)
- ✅ Chatbot básico con OpenAI
- ✅ WhatsApp y Telegram integrados
- ✅ Procesamiento de documentos
- ✅ Sistema de limpieza de contexto