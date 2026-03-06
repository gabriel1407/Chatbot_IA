# 📋 CHANGELOG

Todos los cambios relevantes de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [4.0.0] — 2026-03-06 — MCP Integration

### ➕ Añadido

#### MCP Server (`mcp_server/`)
- **`server.py`** — Servidor MCP con FastMCP y transporte SSE (puerto 8083)
- **`Dockerfile`** — imagen Python 3.12-slim con healthcheck TCP
- **`requirements.txt`** — dependencias: `mcp[cli]`, `httpx`, `watchfiles`, `PyJWT`
- **`middleware/auth.py`** — JWT Service Token: el MCP server firma sus propios tokens con `JWT_SECRET_KEY` compartido, sin usuario ni contraseña, con renovación automática
- **`tools/web_search.py`** — búsqueda web real con Gemini Google Search grounding
- **`tools/read_webpage.py`** — extracción de contenido de URLs remotas
- **`tools/rag.py`** — `rag_search` (búsqueda semántica) + `rag_stats` (estadísticas de chunks)
- **`tools/tenant.py`** — `list_tenants` + `get_tenant` con autenticación JWT automática
- **`tools/context.py`** — `get_context_stats` + `get_context_status`
- **`tools/chatbot.py`** — `chatbot_health` + `send_chat_message`

#### MCP Client en Flask (`openIAService/core/mcp/`)
- **`mcp_client.py`** — `MCPClient` con SSE (`sse_client`), wrappers síncronos y singleton `get_mcp_client()`
- **Propiedad `_sse_url`** — añade `/sse` automáticamente al URL base para evitar 404

#### Integración Flask
- **`core/config/settings.py`** — campo `mcp_server_url` desde `MCP_SERVER_URL`
- **`services/response_generation_adapters.py`** — `WebAssistPortAdapter` usa MCP tools con fallback a legacy
- **`requirements-base.txt`** — añadido `mcp[cli]>=1.2.0`

#### Detección de intención web
- **Fast-path por keywords** en `_should_use_web_search_with_llm()` — detecta queries obvias (búsqueda explícita, deportes, noticias, precios, clima) sin llamar al LLM
- **Fix en el path RAG-enabled** — la detección web ya aplica cuando RAG está activado pero no hay resultados

#### Docker
- **Servicio `mcp_server`** en `docker-compose.yml` con hot-reload via `watchfiles`
- **Volúmenes** montados en `mcp_server/tools/` y `mcp_server/middleware/` para hot-reload sin rebuild

#### Variables de entorno
- `MCP_SERVER_URL` — URL del servidor MCP
- `JWT_SECRET_KEY` — secreto compartido para service tokens (ya existía, ahora también lo usa el MCP server)
- `GEMINI_MODEL` — pasado al MCP server para web search

### 🔄 Modificado

- **`response_generation_use_case.py`** — `generate_ai_response_with_trace()` ahora incluye detección de intención web cuando RAG está activado pero sin resultados (antes solo funcionaba con RAG deshabilitado)
- **Búsqueda web** — migrada de SerpAPI → Ollama API → OpenAI Responses API → **Gemini Google Search grounding** (actual)
- **Formato de respuesta web** — optimizado para WhatsApp: `*bold*`, sin separadores `---`, límite de 3800 chars

### 🗑️ Eliminado / Reemplazado

- **SerpAPI** — reemplazado por Gemini Google Search grounding (no requiere clave adicional)
- **`APP_JWT_TOKEN`** manual — reemplazado por JWT middleware automático
- **`APP_USERNAME/APP_PASSWORD`** — reemplazado por service token con `JWT_SECRET_KEY`

### 🐛 Bugs Corregidos

| Bug | Causa | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'tools'` | `COPY tools/` faltaba en Dockerfile | Añadido `COPY tools/ ./tools/` |
| MCP server `unhealthy` | Healthcheck `curl` colgaba en SSE | Reemplazado por healthcheck TCP Python |
| `TypeError: FastMCP.run() got unexpected keyword argument 'host'` | Args en `run()` en vez de en el constructor | `FastMCP(host=host, port=port)` |
| `GET / HTTP/1.1 404 Not Found` en MCP client | URL sin `/sse` path | Propiedad `_sse_url` añade `/sse` automáticamente |
| Web search no se ejecutaba con RAG activo | `run_web_pipeline()` solo en path RAG-disabled | Fix en `generate_ai_response_with_trace()` |
| Error 400 de WhatsApp al enviar respuesta de búsqueda | Markdown `**bold**` y `---` no soportados + mensaje muy largo | Formato corregido y límite 3800 chars |

---

## [3.0.0] — Febrero 2026 — Plataforma Multi-Tenant

- ✅ Tabla `tenant_channels` en MySQL — credenciales por cliente
- ✅ Routing automático de webhooks WhatsApp por `phone_number_id`
- ✅ Ruta dedicada Telegram `/webhook/telegram/<tenant_id>`
- ✅ RAG aislado por tenant en ChromaDB (`tenant_<id>_chunks`)
- ✅ `DELETE /api/rag/tenant` — reset completo del RAG de un cliente
- ✅ JWT Authentication — login, refresh, roles admin/viewer
- ✅ Fix ChromaDB where filter (causaba 0 resultados)
- ✅ Fix umbral RAG — `rag_global_min_similarity=0.3` para canales

## [2.1.0] — Febrero 2026

- ✅ `ResponseGenerationUseCase` extraído a capa application
- ✅ DI centralizado para `MessageHandler` y `UnifiedChannelService`
- ✅ Manejo global de errores con `APIException`
- ✅ Rutas homogeneizadas con semántica HTTP consistente

## [2.0.0] — Febrero 2026

- ✅ Soporte multi-proveedor: OpenAI, Gemini, Ollama
- ✅ RAG mejorado con embeddings específicos por proveedor
- ✅ Arquitectura SOLID completamente refactorizada
- ✅ Fast-path para preguntas simples

## [1.0.0] — Noviembre 2025

- ✅ Chatbot básico con OpenAI
- ✅ WhatsApp y Telegram integrados
- ✅ Procesamiento de documentos (PDF, Word, texto)
- ✅ Sistema de limpieza de contexto
