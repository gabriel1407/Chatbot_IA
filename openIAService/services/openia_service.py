import logging
import json
import base64
import re
from openai import OpenAI
from decouple import config

from openIAService.services.context_service import load_context, save_context
from openIAService.services.mcp_service import extract_url_from_message, link_reader_agent, mcp_pipeline
from openIAService.services.cache_service import (
    cache_openai_response, 
    get_cached_openai_response,
    get_cache_stats
)
from openIAService.services.metrics_service import measure_time, log_openai_usage

# Configura la clave de API de OpenAI (sanitiza comillas y espacios)
raw_key = config('OPENAI_API_KEY', default='')
OPENAI_API_KEY = raw_key.strip().strip('"').strip("'")
client = OpenAI(api_key=OPENAI_API_KEY)


def should_use_web_search_with_llm(user_question):
    prompt = (
        "Actúa como un clasificador de intención. "
        "Responde SOLO con 'WEB' si la pregunta requiere buscar información factual, de actualidad, o reciente en internet. "
        "Responde SOLO con 'MODEL' si puedes contestar usando solo tu conocimiento general. "
        "No expliques nada ni agregues otra cosa, solo responde WEB o MODEL.\n\n"
        f"Pregunta: {user_question}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # Cambia a "gpt-3.5-turbo" si quieres ahorrar más tokens
            messages=[
                {"role": "system", "content": "Eres un detector de intención para un asistente conversacional."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=5,
            temperature=0
        )
        decision = response.choices[0].message.content.strip().upper()
        logging.info(f"[LLM-INTENT] Clasificador para pregunta '{user_question}': {decision}")
        return decision == "WEB"
    except Exception as e:
        logging.error(f"[LLM-INTENT] Error al clasificar la pregunta: {e}")
        # Si hay error, responde de forma conservadora (usa modelo, no web)
        return False


@measure_time("openai_generate")
def generate_openai_response(prompt, context, language, initial_instructions=None):
    """
    Genera una respuesta de OpenAI basada en el contexto de la conversación.
    Utiliza caché para respuestas similares.
    """
    if initial_instructions:
        context = [initial_instructions] + context

    messages = context + [{"role": "user", "content": prompt}]

    if language != 'en':
        messages.insert(0, {"role": "system", "content": f"Por favor, responde en {language}."})
    
    # Parámetros de la llamada
    model = "gpt-4o-mini"
    max_tokens = 600
    temperature = 0.7
    
    # Verifica si hay una respuesta en caché
    cached_response = get_cached_openai_response(messages, model, temperature, max_tokens)
    if cached_response:
        logging.info("[OPENAI] Respuesta obtenida desde caché")
        try:
            log_openai_usage(model, tokens_used=0, cached=True)
        except Exception:
            pass
        return cached_response
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response and response.choices:
            result = response.choices[0].message.content.strip()
            # Cachea la respuesta para futuras consultas similares
            cache_openai_response(messages, model, temperature, max_tokens, result, ttl=3600)
            logging.info("[OPENAI] Respuesta generada y cacheada")
            # Métricas de uso de OpenAI
            try:
                usage = getattr(response, 'usage', None)
                tokens = 0
                if usage:
                    # En el cliente OpenAI v1, usage puede tener total_tokens
                    tokens = getattr(usage, 'total_tokens', 0) or usage.get('total_tokens', 0)
                log_openai_usage(model, tokens_used=int(tokens) if tokens else 0, cached=False)
            except Exception:
                pass
            return result
        return "No se pudo generar una respuesta."
    except Exception as e:
        logging.error(f"Error al generar respuesta con OpenAI: {e}")
        return "Error al generar la respuesta."

def generate_openai_vision_response(prompt, image_path, language='es'):
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    
    messages = [
        {"role": "system", "content": "Eres un asistente visual experto en analizar y describir imágenes para humanos."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or "Describe el contenido de la imagen."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Modelo recomendado para visión y texto
            messages=messages,
            max_tokens=800,
        )
        if response and response.choices:
            return response.choices[0].message.content.strip()
        return "No se pudo generar una respuesta."
    except Exception as e:
        logging.error(f"Error en vision con OpenAI: {e}")
        return "Error al analizar la imagen."

def handle_text_message(message, user_id, image_path=None, context_id="default"):
    context = load_context(user_id, context_id)
    language = 'es'

    initial_instructions = {
        "role": "system",
        "content": "Eres un asistente virtual diseñado para ayudar a los usuarios con una amplia variedad de preguntas y temas."
    }

    # --- Nuevo: ¿El mensaje tiene URL? ---
    url = extract_url_from_message(message)
    if url:
        logging.info(f"[MCP][Entrada][LinkReader] Activando agente de lectura de links para usuario {user_id} y url: {url}")
        question = re.sub(r'https?://\S+', '', message).strip()  # Quita la URL para usar como pregunta específica
        response = link_reader_agent(url, question)
        context.append({"role": "user", "content": message})
        context.append({"role": "assistant", "content": response})
        save_context(user_id, context, context_id)
        return response

    # --- Si no hay link, sigue con la lógica avanzada de intención ---
    if should_use_web_search_with_llm(message):
        logging.info(f"[MCP][Entrada][LLM] Activando flujo MCP (web) para usuario {user_id} con mensaje: {message}")
        response = mcp_pipeline(message)
        context.append({"role": "user", "content": message})
        context.append({"role": "assistant", "content": response})
        save_context(user_id, context, context_id)
        return response

    # --- Lógica estándar o visión ---
    if image_path:
        logging.info(f"[VISION][Entrada] Procesando imagen para usuario {user_id}")
        response = generate_openai_vision_response(message, image_path, language)
        logging.info(f"[VISION][Salida] Respuesta vision generada para usuario {user_id}: {response}")
        context.append({"role": "user", "content": message})
        context.append({"role": "assistant", "content": response})
        save_context(user_id, context, context_id)
    else:
        prompt = message
        logging.info(f"[OPENAI][Entrada] Flujo estándar para usuario {user_id} con mensaje: {prompt}")
        response = generate_openai_response(prompt, context, language, initial_instructions)
        logging.info(f"[OPENAI][Salida] Respuesta estándar generada para usuario {user_id}: {response}")
        context.append({"role": "user", "content": prompt})
        context.append({"role": "assistant", "content": response})
        save_context(user_id, context, context_id)
    return response