import logging
import json
from openai import OpenAI
from decouple import config

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

def handle_text_message(message, user_id):
    """
    Maneja los mensajes de texto recibidos.
    """
    prompt = message
    context = conversational_contexts.setdefault(user_id, {"context": []})["context"]
    language = 'es'  # Asumimos español por defecto

    initial_instructions = {
        "role": "system",
        "content": "Eres un asistente virtual diseñado para ayudar a los usuarios con una amplia variedad de preguntas y temas."
    }
    
    response = generate_openai_response(prompt, context, language, initial_instructions)
    context.append({"role": "user", "content": prompt})
    context.append({"role": "assistant", "content": response})
    return response
