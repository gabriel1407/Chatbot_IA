import logging
import json
import base64
from openai import OpenAI
from decouple import config

from services.context_service import load_context, save_context

# Configura la clave de API de OpenAI
OPENAI_API_KEY = config('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

conversational_contexts = {}

def generate_openai_response(prompt, context, language, initial_instructions=None):
    """
    Genera una respuesta de OpenAI basada en el contexto de la conversación.
    """
    if initial_instructions:
        context = [initial_instructions] + context

    message = context + [{"role": "user", "content": prompt}]

    if language != 'en':
        message.insert(0, {"role": "system", "content": f"Por favor, responde en {language}."})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=message,
            max_tokens=600,
            temperature=0.7,
        )
        
        if response and response.choices:
            return response.choices[0].message.content.strip()
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
            model="gpt-4o",  # Modelo recomendado para vision y texto
            messages=messages,
            max_tokens=800,
        )
        if response and response.choices:
            return response.choices[0].message.content.strip()
        return "No se pudo generar una respuesta."
    except Exception as e:
        logging.error(f"Error en vision con OpenAI: {e}")
        return "Error al analizar la imagen."




def handle_text_message(message, user_id, image_path=None):
    """
    Maneja mensajes de texto o imágenes.
    Si image_path es provisto, usa GPT-4 Vision para analizar la imagen junto con el mensaje del usuario.
    """
    context = load_context(user_id)
    language = 'es'

    initial_instructions = {
        "role": "system",
        "content": "Eres un asistente virtual diseñado para ayudar a los usuarios con una amplia variedad de preguntas y temas."
    }

    if image_path:
        # Aquí es donde llamas a vision
        response = generate_openai_vision_response(message, image_path, language)
    else:
        prompt = message
        response = generate_openai_response(prompt, context, language, initial_instructions)
        context.append({"role": "user", "content": prompt})
        context.append({"role": "assistant", "content": response})
        save_context(user_id, context)
    return response
