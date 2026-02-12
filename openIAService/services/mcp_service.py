import re
from bs4 import BeautifulSoup
import requests
from decouple import config
from core.ai.factory import get_ai_provider
from core.logging.logger import get_app_logger

# Usar el nuevo sistema de logging centralizado
logger = get_app_logger()

SERPAPI_KEY = config('SERPAPI_KEY')  # Agrega esto a tu .env
# Proveedor configurable (OpenAI, Gemini, Ollama, ...)
provider = get_ai_provider()

def extract_text_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Elimina scripts, styles y noscripts
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = ' '.join(soup.stripped_strings)
        return text[:4000]  # Limita a 4000 caracteres para GPT
    except Exception as e:
        logger.error(f"[MCP][LinkReader] Error extrayendo texto de {url}: {e}")
        return f"No pude leer la página: {e}"
    
def extract_url_from_message(message):
    # Busca el primer link http(s)
    match = re.search(r'(https?://\S+)', message)
    if match:
        return match.group(1)
    return None

def link_reader_agent(url, question=None):
    logger.info(f"[MCP][LinkReader] Leyendo y resumiendo link: {url}")
    page_text = extract_text_from_url(url)
    context = [
        {"role": "system", "content": "Eres un asistente que responde leyendo el contenido de una página web proporcionada por el usuario. Responde de forma clara y concisa."},
        {"role": "user", "content": f"Página leída: {url}\nContenido:\n{page_text}\n\nPregunta específica: {question or 'Resume el contenido.'}"}
    ]
    try:
        resp_text = provider.generate_text(prompt="", messages=context, max_tokens=700, temperature=0.7)
        return resp_text.strip()
    except Exception as e:
        logger.error(f"[MCP][LinkReader] Error al generar respuesta con OpenAI: {e}")
        return "No se pudo generar un resumen de la página."

def web_search_agent(query):
    logger.info("========== [MCP][WebSearch][ENTRADA] ==========")
    logger.info(f"[MCP][WebSearch] Consulta recibida: '{query}'")

    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "hl": "es"  # o "en" para inglés
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = resp.json()
        results = data.get("organic_results", [])
        if results:
            # Extrae los primeros resultados (título y snippet)
            snippets = []
            for res in results[:3]:
                title = res.get("title", "")
                snippet = res.get("snippet", "")
                link = res.get("link", "")
                if title or snippet:
                    snippets.append(f"Título: {title}\nFragmento: {snippet}\nEnlace: {link}\n")
            logger.info(f"[MCP][WebSearch] {len(snippets)} resultados de Google encontrados.")
            logger.info("========== [MCP][WebSearch][SALIDA] ==========")
            return "\n".join(snippets)
        else:
            logger.warning("[MCP][WebSearch] No se encontraron resultados en Google.")
            logger.info("========== [MCP][WebSearch][SALIDA] ==========")
            return "No se encontraron resultados relevantes en Google."
    except Exception as e:
        logger.error(f"[MCP][WebSearch] Error en búsqueda Google: {e}")
        logger.info("========== [MCP][WebSearch][SALIDA] ==========")
        return f"Error en búsqueda web: {e}"


# --- Agente ChatGPT (resumidor/filtro) ---
def chatgpt_agent(query, web_results):
    logger.info("========== [MCP][ChatGPT][ENTRADA] ==========")
    logger.info(f"[MCP][ChatGPT] Resumiendo resultados para: '{query}'")

    context = [
        {"role": "system", "content": "Eres un asistente que responde usando información de la web. Resume y filtra la información relevante para el usuario."},
        {"role": "user", "content": f"Consulta: {query}\n\nResultados web:\n{web_results}\n\nPor favor, responde de forma clara y concisa usando la mejor información disponible."}
    ]
    try:
        resp_text = provider.generate_text(prompt="", messages=context, max_tokens=600, temperature=0.7)
        if resp_text:
            logger.info("[MCP][ChatGPT] Respuesta generada correctamente.")
            logger.info("========== [MCP][ChatGPT][SALIDA] ==========")
            return resp_text.strip()
        logger.warning("[MCP][ChatGPT] No se pudo generar una respuesta.")
        logger.info("========== [MCP][ChatGPT][SALIDA] ==========")
        return "No se pudo generar una respuesta."
    except Exception as e:
        logger.error(f"[MCP][ChatGPT] Error en ChatGPT: {e}")
        logger.info("========== [MCP][ChatGPT][SALIDA] ==========")
        return f"Error en ChatGPT: {e}"

# --- MCP: Orquestador multi-agente ---
def mcp_pipeline(query):
    logger.info("--------------------------------------------------------")
    logger.info(f"[MCP][PIPELINE] Iniciando pipeline MCP para: '{query}'")
    web_results = web_search_agent(query)
    final_response = chatgpt_agent(query, web_results)
    logger.info(f"[MCP][PIPELINE] Pipeline MCP finalizado para: '{query}'")
    logger.info("--------------------------------------------------------")
    return final_response
