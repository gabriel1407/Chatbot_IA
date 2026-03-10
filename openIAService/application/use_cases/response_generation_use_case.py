"""
Response Generation Use Case.
Orquesta la generación de respuestas (RAG/LLM/fallback legacy) en capa application.
"""
import base64
import re
from typing import Optional, List, Any, Protocol

from core.logging.logger import get_application_logger
from core.ai.providers import AIProvider


class ContextPort(Protocol):
    def load_context(self, user_id: str, context_id: str) -> List[dict]: ...
    def save_context(self, user_id: str, context: List[dict], context_id: str) -> None: ...


class WebAssistPort(Protocol):
    def extract_url(self, message: str) -> Optional[str]: ...
    def summarize_link(self, url: str, question: Optional[str] = None) -> str: ...
    def run_web_pipeline(self, query: str) -> str: ...


class AIProviderFactoryPort(Protocol):
    def get_provider(self, provider_name: Optional[str] = None) -> AIProvider: ...


class RAGSearchPort(Protocol):
    def search(self, query: str, tenant_id: str = "default", top_k: Optional[int] = None) -> Optional[List[dict]]: ...


class ResponseGenerationUseCase:
    """Caso de uso para generar respuestas del asistente."""

    IDENTITY_POLICY = (
        "Regla de identidad obligatoria: eres un asistente virtual de IA. "
        "Nunca afirmes ser una persona real, desarrollador, empleado o usuario específico. "
        "Si te preguntan quién eres, responde que eres un asistente virtual."
    )

    def __init__(
        self,
        context_port: ContextPort,
        web_assist_port: WebAssistPort,
        ai_provider_factory: AIProviderFactoryPort,
        rag_search_port: RAGSearchPort,
        tenant_config_service=None,   # TenantConfigService (opcional, inyectado)
    ):
        self.logger = get_application_logger()
        self.context_port = context_port
        self.web_assist_port = web_assist_port
        self.ai_provider_factory = ai_provider_factory
        self.rag_search_port = rag_search_port
        self._tenant_config_service = tenant_config_service

    # ------------------------------------------------------------------ #
    # Helpers de configuración desde DB                                     #
    # ------------------------------------------------------------------ #

    def _get_system_prompt(self, tenant_id: str = "default") -> str:
        """Carga el system prompt del tenant desde la DB (con caché)."""
        if self._tenant_config_service is None:
            return (
                "Eres un asistente útil. Responde de forma clara y concisa. "
                f"{self.IDENTITY_POLICY}"
            )
        try:
            config = self._tenant_config_service.get(tenant_id)
            return config.get_full_system_prompt()
        except Exception as e:
            self.logger.warning(f"[ResponseGeneration] Error cargando config de tenant '{tenant_id}': {e}")
            return f"Eres un asistente útil. {self.IDENTITY_POLICY}"

    def _get_rag_system_prompt(self, tenant_id: str = "default") -> str:
        """System prompt para respuestas con contexto RAG."""
        if self._tenant_config_service is None:
            return (
                "Eres un asistente útil que responde basándote en la información proporcionada. "
                "Si la pregunta no se puede responder con esa información, indícalo. "
                f"{self.IDENTITY_POLICY}"
            )
        try:
            config = self._tenant_config_service.get(tenant_id)
            return (
                f"{config.get_full_system_prompt()}\n\n"
                "Responde SOLO usando la información proporcionada como contexto. "
                "Si la respuesta no se encuentra en el contexto, indícalo claramente."
            )
        except Exception as e:
            self.logger.warning(f"[ResponseGeneration] Error cargando config RAG de tenant '{tenant_id}': {e}")
            return f"Eres un asistente útil. {self.IDENTITY_POLICY}"

    def _get_ai_model(self, tenant_id: str = "default") -> Optional[str]:
        """Obtiene el modelo de IA específico seleccionado por el tenant."""
        if self._tenant_config_service is None:
            return None
        try:
            config = self._tenant_config_service.get(tenant_id)
            model = getattr(config, "ai_model", None)
            if model:
                self.logger.info(f"[ResponseGeneration] Usando modelo específico del tenant '{tenant_id}': {model}")
            return model
        except Exception as e:
            self.logger.warning(f"[ResponseGeneration] Error cargando model de tenant '{tenant_id}': {e}")
            return None

    def _get_ai_provider_name(self, tenant_id: str = "default") -> Optional[str]:
        """Obtiene el proveedor de IA (openai/gemini/ollama) del tenant."""
        if self._tenant_config_service is None:
            return None
        try:
            config = self._tenant_config_service.get(tenant_id)
            provider = getattr(config, "ai_provider", None)
            if provider:
                self.logger.info(f"[ResponseGeneration] Usando proveedor específico del tenant '{tenant_id}': {provider}")
            return provider
        except Exception as e:
            self.logger.warning(f"[ResponseGeneration] Error cargando provider de tenant '{tenant_id}': {e}")
            return None

    def search_rag_context(
        self,
        user_id: str,
        query: str,
        tenant_id: str = "default",
        top_k: Optional[int] = None,
    ) -> Optional[List[dict]]:
        """
        Busca contexto en RAG del tenant especificado.

        Args:
            user_id: ID del usuario (para logging)
            query: Texto de la consulta
            tenant_id: ID del tenant para aislamiento
            top_k: Número máximo de resultados

        Returns:
            Lista de chunks con contexto relevante, o None si no hay resultados
        """
        try:
            results = self.rag_search_port.search(query=query, tenant_id=tenant_id, top_k=top_k)
            if results:
                self.logger.info(f"RAG: {len(results)} chunks encontrados para usuario {user_id} en tenant {tenant_id}")
                return results
            return None
        except Exception as e:
            self.logger.warning(f"Error buscando en RAG para tenant {tenant_id}: {e}")
            return None

    def generate_ai_response(
        self,
        user_id: str,
        context_id: str,
        processed_msg: Any,
        rag_context: Optional[List[dict]] = None,
        rag_enabled: bool = True,
        tenant_id: str = "default",
    ) -> str:
        """Genera respuesta del asistente según configuración y contexto."""
        try:
            if not rag_enabled:
                return self.generate_legacy_response(user_id, processed_msg, context_id=context_id, tenant_id=tenant_id)

            if rag_context:
                return self._generate_rag_response(processed_msg, rag_context, tenant_id=tenant_id)

            return self._generate_plain_ai_response(processed_msg, tenant_id=tenant_id)

        except Exception as e:
            self.logger.error(f"Error generando respuesta con IA: {e}")
            return "Disculpa, hubo un error generando la respuesta. Por favor intenta de nuevo."

    def generate_ai_response_with_trace(
        self,
        user_id: str,
        context_id: str,
        processed_msg: Any,
        rag_context: Optional[List[dict]] = None,
        rag_enabled: bool = True,
        include_thinking: bool = False,
        tenant_id: str = "default",
    ) -> dict:
        """Genera respuesta y, opcionalmente, retorna traza de thinking si el proveedor la soporta."""
        try:
            if not rag_enabled:
                return self.generate_legacy_response_with_trace(
                    user_id=user_id,
                    processed_msg=processed_msg,
                    context_id=context_id,
                    include_thinking=include_thinking,
                    tenant_id=tenant_id,
                )

            if rag_context:
                return self._generate_rag_response_with_trace(
                    processed_msg=processed_msg,
                    rag_context=rag_context,
                    include_thinking=include_thinking,
                    tenant_id=tenant_id,
                )

            # RAG habilitado pero sin documentos relevantes:
            # verificar si el mensaje requiere búsqueda web antes de responder con LLM.
            prompt = processed_msg.processed_content
            url = self.web_assist_port.extract_url(prompt)
            if url:
                self.logger.info(f"[WebAssist] URL detectada en mensaje → usando read_webpage")
                import re
                question = re.sub(r'https?://\S+', '', prompt).strip()
                web_result = self.web_assist_port.summarize_link(url, question or None)
                return {"content": web_result, "thinking": ""}

            if self._should_use_web_search_with_llm(prompt, tenant_id=tenant_id):
                self.logger.info(f"[WebAssist] Intención WEB detectada → ejecutando web_search via MCP")
                web_result = self.web_assist_port.run_web_pipeline(prompt)
                return {"content": web_result, "thinking": ""}

            return self._generate_plain_ai_response_with_trace(
                processed_msg=processed_msg,
                include_thinking=include_thinking,
                tenant_id=tenant_id,
            )
        except Exception as e:
            self.logger.error(f"Error generando respuesta con traza: {e}")
            return {
                "content": "Disculpa, hubo un error generando la respuesta. Por favor intenta de nuevo.",
                "thinking": "",
            }


    def generate_legacy_response(
        self,
        user_id: str,
        processed_msg: Any,
        context_id: Optional[str] = None,
        tenant_id: str = "default",
    ) -> str:
        """Fallback legacy cuando RAG está deshabilitado."""
        try:
            current_context_id = context_id or "default"
            context = self.context_port.load_context(user_id, current_context_id)

            import re
            prompt = processed_msg.original_content if processed_msg.message_type.value == "image" else processed_msg.processed_content

            url = self.web_assist_port.extract_url(prompt)
            if url:
                question = re.sub(r'https?://\S+', '', prompt).strip()
                response = self.web_assist_port.summarize_link(url, question)
                context.append({"role": "user", "content": prompt})
                context.append({"role": "assistant", "content": response})
                self.context_port.save_context(user_id, context, current_context_id)
                return response

            if self._should_use_web_search_with_llm(prompt, tenant_id=tenant_id):
                response = self.web_assist_port.run_web_pipeline(prompt)
                context.append({"role": "user", "content": prompt})
                context.append({"role": "assistant", "content": response})
                self.context_port.save_context(user_id, context, current_context_id)
                return response

            if processed_msg.message_type.value == "image":
                image_path = processed_msg.metadata.get("file_path") if processed_msg.metadata else None
                response = self._generate_legacy_vision_response(
                    prompt=prompt or "Describe la imagen",
                    image_path=image_path,
                    language="es",
                    tenant_id=tenant_id,
                )
                context.append({"role": "user", "content": prompt})
                context.append({"role": "assistant", "content": response})
                self.context_port.save_context(user_id, context, current_context_id)
                return response

            response = self._generate_legacy_text_response(prompt=prompt, context=context, language="es", tenant_id=tenant_id)
            context.append({"role": "user", "content": prompt})
            context.append({"role": "assistant", "content": response})
            self.context_port.save_context(user_id, context, current_context_id)
            return response

        except Exception as e:
            self.logger.error(f"Error en fallback legacy sin RAG: {e}")
            return self._generate_plain_ai_response(processed_msg, tenant_id=tenant_id)

    def generate_legacy_response_with_trace(
        self,
        user_id: str,
        processed_msg: Any,
        context_id: Optional[str] = None,
        include_thinking: bool = False,
        tenant_id: str = "default",
    ) -> dict:
        """Fallback legacy con salida enriquecida para UI/canales."""
        response = self.generate_legacy_response(
            user_id=user_id,
            processed_msg=processed_msg,
            context_id=context_id,
            tenant_id=tenant_id,
        )
        if not include_thinking:
            return {"content": response, "thinking": ""}

        # Para mantener compatibilidad del flujo legacy, no se expone thinking detallado.
        return {
            "content": response,
            "thinking": "",
        }

    def _should_use_web_search_with_llm(self, user_question: str, tenant_id: str = "default") -> bool:
        question_lower = (user_question or "").lower().strip()
        import re

        # ── 1. Fast-path: patrones que NUNCA necesitan internet ───────────────
        no_web_patterns = [
            r'^hola\b', r'^hello\b', r'^hi\b', r'^hey\b',
            r'\bquien\s+eres\b', r'\bwho\s+are\s+you\b',
            r'\bcomo\s+estas\b', r'\bhow\s+are\s+you\b',
            r'\bque\s+eres\b', r'\bwhat\s+are\s+you\b',
            r'^gracias\b', r'^thanks\b', r'^thank\s+you\b',
            r'^adios\b', r'^bye\b', r'^goodbye\b',
            r'\btu\s+nombre\b', r'\byour\s+name\b',
        ]
        for pattern in no_web_patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                return False

        # ── 2. Fast-path: keywords que SÍ requieren internet → evita el LLM ──
        #    Si el mensaje contiene alguna de estas expresiones, WEB inmediato.
        web_keywords = [
            # búsqueda explícita
            r'\bbusca\s+en\s+internet\b', r'\bbusca\s+en\s+la\s+web\b',
            r'\bbusca\s+en\s+google\b',   r'\bsearch\s+(the\s+)?(web|internet|google)\b',
            r'\bconsulta\s+en\s+internet\b',
            # actualidad / tiempo real
            r'\bhoy\b',           r'\btoday\b',
            r'\bahora\b',         r'\bright\s+now\b',
            r'\bactual(mente)?\b',r'\bcurrent(ly)?\b',
            r'\b\d{4}\b',         # año (ej: "2025", "2026")
            r'\besta\s+semana\b', r'\bthis\s+week\b',
            r'\breciente(mente)?\b', r'\blatest\b', r'\brecent\b',
            # deportes / eventos
            r'\bjuega\b', r'\bjuegan\b', r'\bpartido\b', r'\bmatch\b',
            r'\bclasificaci[oó]n\b', r'\bliga\b', r'\btorneo\b',
            # precios / mercados
            r'\bprecio\s+de\b',   r'\bprice\s+of\b',
            r'\bcotizaci[oó]n\b', r'\bbolsa\b', r'\bbtc\b', r'\bcrypto\b',
            # noticias
            r'\bnoticias\b',      r'\bnews\b',
            r'\blo\s+[uú]ltimo\b',r'\blatest\s+news\b',
            # clima
            r'\bclima\b', r'\btiempo\s+en\b', r'\bweather\b',
        ]
        for pattern in web_keywords:
            if re.search(pattern, question_lower, re.IGNORECASE):
                self.logger.info(f"[WebAssist] Fast-path WEB por keyword: '{pattern}'")
                return True

        # ── 3. Slow-path: LLM classifier solo para casos ambiguos ─────────────
        prompt = (
            "Actúa como un clasificador de intención. "
            "Responde SOLO con 'WEB' si la pregunta requiere buscar información factual, de actualidad, o reciente en internet. "
            "Responde SOLO con 'MODEL' si puedes contestar usando solo tu conocimiento general. "
            "No expliques nada ni agregues otra cosa, solo responde WEB o MODEL.\n\n"
            f"Pregunta: {user_question}"
        )

        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)
            
            messages = [
                {"role": "system", "content": "Eres un detector de intención para un asistente conversacional."},
                {"role": "user", "content": prompt},
            ]
            
            kwargs = {"max_tokens": 5, "temperature": 0}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            resp_text = provider.generate_text(prompt=prompt, messages=messages, **kwargs)
            decision = (resp_text or "").strip().upper()
            return decision == "WEB"
        except Exception as e:
            self.logger.error(f"Error al clasificar intención web/model: {e}")
            return False

    def _generate_plain_ai_response(self, processed_msg: Any, tenant_id: str = "default") -> str:
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)
            system_prompt = self._get_system_prompt(tenant_id)
            
            kwargs = {"temperature": 0.7, "max_tokens": 2048}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            resp_text = provider.generate_text(
                prompt=processed_msg.processed_content,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": processed_msg.processed_content}
                ],
                **kwargs
            )
            return resp_text
        except Exception as e:
            self.logger.error(f"Error en generación LLM plana: {e}")
            return self._generate_default_response(processed_msg)

    def _generate_plain_ai_response_with_trace(self, processed_msg: Any, include_thinking: bool = False, tenant_id: str = "default") -> dict:
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)
            system_prompt = self._get_system_prompt(tenant_id)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": processed_msg.processed_content},
            ]

            kwargs = {"temperature": 0.7, "max_tokens": 2048}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            if include_thinking and getattr(provider, "supports_thinking", lambda: False)():
                traced = provider.generate_text_with_thinking(
                    prompt=processed_msg.processed_content,
                    messages=messages,
                    **kwargs
                )
                return {
                    "content": traced.get("content", ""),
                    "thinking": traced.get("thinking", "") or "",
                }

            text = provider.generate_text(
                prompt=processed_msg.processed_content,
                messages=messages,
                **kwargs
            )
            return {"content": text, "thinking": ""}
        except Exception as e:
            self.logger.error(f"Error en generación LLM plana con traza: {e}")
            return {"content": self._generate_default_response(processed_msg), "thinking": ""}

    def _generate_legacy_text_response(self, prompt: str, context: List[dict], language: str = "es", tenant_id: str = "default") -> str:
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)
            initial_instructions = {
                "role": "system",
                "content": self._get_system_prompt(tenant_id),
            }

            messages = [initial_instructions] + context + [{"role": "user", "content": prompt}]
            if language != 'en':
                messages.insert(0, {"role": "system", "content": f"Por favor, responde en {language}."})
            
            kwargs = {"temperature": 0.7, "max_tokens": 600}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            resp_text = provider.generate_text(prompt=prompt, messages=messages, **kwargs)
            if resp_text:
                return resp_text.strip()
            return "No se pudo generar una respuesta."
        except Exception as e:
            self.logger.error(f"Error en generación legacy texto: {e}")
            return "Error al generar la respuesta."

    def _generate_legacy_vision_response(self, prompt: str, image_path: Optional[str], language: str = "es", tenant_id: str = "default") -> str:
        if not image_path:
            return "No se proporcionó imagen para analizar."

        import base64
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            messages = [
                {
                    "role": "system",
                    "content": (
                        self._get_system_prompt(tenant_id) +
                        " Además eres un asistente visual experto en analizar y describir imágenes."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or "Describe el contenido de la imagen."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]

            if language != 'en':
                messages.insert(0, {"role": "system", "content": f"Por favor, responde en {language}."})

            kwargs = {"max_tokens": 800}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            resp_text = provider.generate_text(prompt=prompt, messages=messages, **kwargs)
            if resp_text:
                return resp_text.strip()
            return "No se pudo generar una respuesta."
        except Exception as e:
            self.logger.error(f"Error en generación legacy visión: {e}")
            return "Error al analizar la imagen."

    def _generate_rag_response(self, processed_msg: Any, rag_context: List[dict], tenant_id: str = "default") -> str:
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)

            context_str = "Información relevante:\n"
            for i, chunk in enumerate(rag_context, 1):
                content = chunk.get("content", "")
                sim = chunk.get("similarity", 0)
                context_str += f"[{i}] (Relevancia: {sim:.0%}) {content[:200]}...\n\n"

            system_prompt = self._get_rag_system_prompt(tenant_id)
            user_prompt = f"""{context_str}

Pregunta: {processed_msg.processed_content}

Responde de forma concisa y relevante."""

            kwargs = {"temperature": 0.7, "max_tokens": 2048}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            resp_text = provider.generate_text(
                prompt=processed_msg.processed_content,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                **kwargs
            )

            return resp_text
        except Exception as e:
            self.logger.error(f"Error en generación RAG+OpenAI: {e}")
            return self._generate_default_response(processed_msg)

    def _generate_rag_response_with_trace(
        self,
        processed_msg: Any,
        rag_context: List[dict],
        include_thinking: bool = False,
        tenant_id: str = "default",
    ) -> dict:
        try:
            p_name = self._get_ai_provider_name(tenant_id)
            provider = self.ai_provider_factory.get_provider(p_name)

            context_str = "Información relevante:\n"
            for i, chunk in enumerate(rag_context, 1):
                content = chunk.get("content", "")
                sim = chunk.get("similarity", 0)
                context_str += f"[{i}] (Relevancia: {sim:.0%}) {content[:200]}...\n\n"

            system_prompt = self._get_rag_system_prompt(tenant_id)
            user_prompt = f"""{context_str}

Pregunta: {processed_msg.processed_content}

Responde de forma concisa y relevante."""

            kwargs = {"temperature": 0.7, "max_tokens": 2048}
            ai_model = self._get_ai_model(tenant_id)
            if ai_model:
                kwargs["model"] = ai_model

            if include_thinking and getattr(provider, "supports_thinking", lambda: False)():
                traced = provider.generate_text_with_thinking(
                    prompt=processed_msg.processed_content,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    **kwargs
                )
                return {
                    "content": traced.get("content", ""),
                    "thinking": traced.get("thinking", "") or "",
                }

            resp_text = provider.generate_text(
                prompt=processed_msg.processed_content,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs
            )

            return {"content": resp_text, "thinking": ""}
        except Exception as e:
            self.logger.error(f"Error en generación RAG+LLM con traza: {e}")
            return {"content": self._generate_default_response(processed_msg), "thinking": ""}

    @staticmethod
    def _generate_default_response(processed_msg: Any) -> str:
        if processed_msg.message_type.value == "text":
            return f"Entiendo tu mensaje: '{processed_msg.processed_content[:100]}...' ¿En qué más puedo ayudarte?"
        if processed_msg.message_type.value == "image":
            return "He analizado tu imagen. ¿Hay algo específico que te gustaría saber sobre ella?"
        if processed_msg.message_type.value == "audio":
            return f"He recibido tu audio. Texto detectado: '{processed_msg.processed_content[:120]}'. ¿Deseas que te ayude con algo específico sobre esto?"
        if processed_msg.message_type.value == "document":
            return "He procesado tu documento. ¿Tienes alguna pregunta específica sobre su contenido?"
        return "He recibido tu mensaje. ¿Cómo puedo ayudarte?"
