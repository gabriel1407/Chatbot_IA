import os
import fitz  # PyMuPDF
import docx
import pytesseract
import speech_recognition as sr
from flask import Flask, request, jsonify
from openai import OpenAI
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import requests
import json
import logging
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from langdetect import detect
from decouple import config

app = Flask(__name__)

# Configura la clave de API de OpenAI
OPENAI_API_KEY = config('OPENAI_API_KEY')  # Reemplaza con tu clave API
client = OpenAI(api_key=OPENAI_API_KEY)

conversational_contexts = {}

# Configura la ruta para guardar los archivos subidos
UPLOAD_FOLDER = os.path.join('local', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configuración de logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# Ruta para subir el archivo PDF
@app.route('/upload-pdf/', methods=['POST'])
def upload_pdf():
    global galanet_knowledge
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extraer contenido del PDF
        galanet_knowledge = process_pdf(file_path)
        return jsonify({"message": "PDF uploaded and content processed successfully"}), 200
    else:
        return jsonify({"error": "Only PDF files are allowed"}), 400

def process_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        logging.info(f"PDF processed successfully: {file_path}")
    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
    return text

def process_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def process_image(file_path):
    text = pytesseract.image_to_string(file_path)
    return text

def process_audio(file_path, language):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(file_path)
    audio.export(file_path, format="wav")
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language=language)
    return text
def handle_message_with_ai(message, user_id="default_user", message_type="text", media_file=None):
    try:
        # Crear un contexto de conversación por usuario
        if user_id not in conversational_contexts:
            conversational_contexts[user_id] = {"context": [], "galanet_mode": False}

        # Detectar si el mensaje contiene la palabra clave "Galanet" para activar el modo
        if "galanet" in message.lower():
            conversational_contexts[user_id]["galanet_mode"] = True
            response = "Modo de soporte Galanet activado. Ahora, solo puedo responder a preguntas relacionadas con los servicios de internet de Galanet."
            conversational_contexts[user_id]["context"].append({"role": "assistant", "content": response})
            return response

        # Detectar si el mensaje contiene las palabras clave para salir del modo Galanet
        if any(word in message.lower() for word in ["salir", "adios"]):
            if conversational_contexts[user_id]["galanet_mode"]:
                conversational_contexts[user_id]["galanet_mode"] = False
                response = "Modo de soporte Galanet desactivado. Ahora puedes hacerme cualquier pregunta."
                conversational_contexts[user_id]["context"].append({"role": "assistant", "content": response})
                return response
            else:
                response = "No estás en modo Galanet. Puedes hacerme cualquier pregunta."
                conversational_contexts[user_id]["context"].append({"role": "assistant", "content": response})
                return response

        
        # Detectar si el mensaje contiene código
        if "```" in message or "import " in message or "const " in message:
            logging.info("Mensaje contiene código de programación.")
            # Aquí podrías formatear el mensaje como código y pasar instrucciones específicas a la IA
            initial_instructions = {
                "role": "system",
                "content": "Eres un asistente técnico que puede ayudar con preguntas sobre programación y código. Puedes recibir y analizar fragmentos de código en diferentes lenguajes de programación, como Python, JavaScript, Java, etc. Proporciona soluciones claras y específicas a problemas de programación."
            }
            response = generate_openai_response(f"Este es un código que necesito ayuda para ajustar: {message}", conversational_contexts[user_id]["context"], 'es', initial_instructions=initial_instructions)
            return response
        
        # Comprobar si está en modo Galanet
        if conversational_contexts[user_id]["galanet_mode"]:
            # Procesar mensaje según su tipo
            if message_type == "text":
                return handle_text_message(message, user_id)
            elif message_type == "image" and media_file:
                return handle_image_message(media_file, user_id)
            elif message_type == "audio" and media_file:
                return handle_audio_message(media_file, user_id)
            else:
                return "Lo siento, no puedo procesar este tipo de mensaje en modo Galanet."

        else:
            # Si no está en modo Galanet, responder normalmente a cualquier pregunta
            return handle_text_message(message, user_id)

    except Exception as e:
        logging.error(f"Error al manejar el mensaje con IA: {e}")
        return "Hubo un error al procesar tu mensaje."

def handle_text_message(message, user_id):
    prompt = message
    context = conversational_contexts[user_id]["context"]
    language = 'es'  # Asumimos español por defecto

    initial_instructions = {
        "role": "system",
        "content": "Eres un asistente de soporte técnico especializado en ayudar a los clientes de Galanet con problemas de internet. Proporciona respuestas claras, útiles y orientadas a solucionar problemas de conexión, configuración de red, y asistencia técnica general para los servicios de Galanet. Si te hacen preguntas fuera de estos temas, responde con 'Lo siento, no puedo darte esa respuesta, ya que mi conocimiento es para prestar servicio a Galanet'."
    }

    response = generate_openai_response(prompt, context, language, initial_instructions)
    conversational_contexts[user_id]["context"].append({"role": "user", "content": prompt})
    conversational_contexts[user_id]["context"].append({"role": "assistant", "content": response})
    return response

def handle_image_message(media_file, user_id):
    # Procesar la imagen usando OCR para obtener el texto
    extracted_text = process_image(media_file)
    # Comprobar si el texto extraído está relacionado con problemas de internet
    return handle_text_message(extracted_text, user_id)

def handle_audio_message(media_file, user_id):
    # Procesar el audio para obtener el texto
    extracted_text = process_audio(media_file, 'es')
    # Comprobar si el texto extraído está relacionado con problemas de internet
    return handle_text_message(extracted_text, user_id)

def generate_openai_response(prompt, context, language, initial_instructions=None):
    # Si hay instrucciones iniciales, agrégalas al inicio del contexto
    if initial_instructions:
        context = [initial_instructions] + context

    message = context + [
        {"role": "user", "content": prompt}
    ]

    # Incluir instrucciones de idioma si no es inglés
    if language != 'en':
        message.insert(0, {"role": "system", "content": f"Por favor, responde en {language}."})
    
    # Realiza la llamada a la API de OpenAI para obtener una respuesta
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=message,
        max_tokens=600,
        temperature=0.7,
    )
    
    if response and response.choices:
        completion = response.choices[0].message.content.strip()
        return completion
    return "No se pudo generar una respuesta."

def is_relevant_to_galanet(response_text):
    # Lista de palabras clave relacionadas con soporte de internet, redes, Galanet, etc.
    keywords = ["internet", "conexión", "red", "Galanet", "WiFi", "modem", "router", "soporte técnico", "configuración"]
    
    # Convertir respuesta a minúsculas para una comparación insensible a mayúsculas/minúsculas
    response_text_lower = response_text.lower()
    
    # Verificar si alguna palabra clave está en la respuesta
    for keyword in keywords:
        if keyword in response_text_lower:
            return True
    return False

def generate_media(content, media_type):
    if media_type == "audio":
        tts = gTTS(content, lang='es')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "response.mp3")
        tts.save(file_path)
    elif media_type == "image":
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "response.png")
        font = ImageFont.load_default()
        image = Image.new('RGB', (500, 300), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), content, font=font, fill=(255, 255, 255))
        image.save(file_path)
    return file_path

@app.route('/saludar', methods=['GET'])
def Saludar():
    return "Hola mundo desde flask"

@app.route('/whatsapp', methods=['GET'])
def verifyToken():
    try:
        access_token = "E23431A21A991BE82FF3D79D5F1F8"
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if token == access_token:
            return challenge
        else:
            return "Error", 400
    except Exception as e:
        logging.error(f"Error en verifyToken: {e}")
        return "Error", 400


# Función para crear mensajes interactivos de botones con parámetros
def create_button_message(body_text, buttons):
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": buttons
            }
        }
    }


def create_list_message(body_text, options):
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Opciones Disponibles"
            },
            "body": {
                "text": body_text  # Texto del cuerpo con información general
            },
            "footer": {
                "text": "Selecciona una opción de la lista para más detalles."
            },
            "action": {
                "button": "Seleccionar",
                "sections": [
                    {
                        "title": "Opciones",
                        "rows": options
                    }
                ]
            }
        }
    }

def truncate_text(text, max_length):
    """
    Truncate the text to the specified max_length.
    If the text is longer than max_length, truncate and add '...'
    """
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text

def split_message(text, max_length):
    """
    Divide un texto largo en partes más pequeñas.
    """
    parts = []
    while len(text) > max_length:
        split_index = text.rfind('\n', 0, max_length)
        if split_index == -1:
            split_index = max_length
        parts.append(text[:split_index])
        text = text[split_index:]
    parts.append(text)
    return parts

# Set para almacenar los IDs de mensajes ya procesados
processed_messages = set()

@app.route('/whatsapp', methods=['POST'])
def Received_message():
    try:
        body = request.get_json()
        if not body:
            logging.error("No se recibió ningún cuerpo JSON.")
            return "EVENT_RECEIVED"

        logging.info(f"JSON recibido: {json.dumps(body)}")  # Registrar el JSON completo para depuración

        if "entry" in body and len(body["entry"]) > 0:
            entry = body["entry"][0]
            if "changes" in entry and len(entry["changes"]) > 0:
                changes = entry["changes"][0]
                if "value" in changes:
                    value = changes["value"]
                    if "messages" in value:
                        messages = value["messages"]
                        for message in messages:
                            # Verificar si ya se procesó el mensaje
                            message_id = message.get("id")
                            if message_id and message_id not in processed_messages:
                                processed_messages.add(message_id)
                                process_individual_message(message)  # Lógica de procesamiento de mensajes
                            else:
                                logging.info(f"Mensaje {message_id} ya procesado o no tiene ID.")
                    else:
                        logging.info("Evento no es un mensaje directo, puede ser un estado de mensaje u otro evento.")
                else:
                    logging.error("La clave 'value' no está presente en 'changes'.")
            else:
                logging.error("La clave 'changes' no está presente en 'entry'.")
        else:
            logging.error("La clave 'entry' no está presente en el cuerpo recibido.")
        return "EVENT_RECEIVED"
    except Exception as e:
        logging.error(f"Error en Received_message: {e}")
        return "EVENT_RECEIVED"

def process_individual_message(message):
    try:
        if "text" in message:
            text = message["text"]
            body = text["body"]
        elif "document" in message:
            document = message["document"]
            document_id = document["id"]
            document_mime_type = document["mime_type"]
            file_path = download_media(document_id, document_mime_type)
            body = process_docx(file_path) if document_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" else process_pdf(file_path)
        elif "image" in message:
            image = message["image"]
            image_id = image["id"]
            file_path = download_media(image_id, "image/jpeg")
            body = process_image(file_path)
        elif "audio" in message:
            audio = message["audio"]
            audio_id = audio["id"]
            file_path = download_media(audio_id, "audio/ogg")
            language = detect_audio_language(file_path)
            body = process_audio(file_path, language)
        else:
            body = "No se pudo procesar el mensaje."

        number = message["from"]
        logging.info(f"Mensaje recibido: {body}")

        language = detect(body)
        
        if number not in conversational_contexts:
            conversational_contexts[number] = []

        openai_response = generate_openai_response(body, conversational_contexts[number], language)

        conversational_contexts[number].append({"role": "user", "content": body})
        conversational_contexts[number].append({"role": "assistant", "content": openai_response})

        # Comentado: Análisis de respuesta de la IA para crear lista de opciones
        # lines = openai_response.split('\n')
        # options = []
        # detailed_text = ""

        # for line in lines:
        #     if line.strip() and line.strip()[0].isdigit() and line.strip()[1] == '.':
        #         parts = line.split(". ", 1)
        #         if len(parts) == 2:
        #             id = f"option{parts[0].strip()}"
        #             description = truncate_text(parts[1].split(':')[0], max_length=60)
        #             options.append({
        #                 "id": id,
        #                 "title": 'Opciones disponibles',
        #                 "description": description
        #             })
        #             detailed_text += f"{line}\n\n"

        # if len(options) >= 2:
        #     answer_body = create_list_message(detailed_text.strip(), options)
        #     answer_body["to"] = f"{number}"
        # else:
        logging.error("No se pudieron crear opciones de lista de la respuesta de OpenAI.")
        answer_body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{number}",
            "type": "text",
            "text": {"body": openai_response}
        }

        logging.info(f"Respuesta de OpenAI: {openai_response}")

        send_message_whatsapp = WhatsappService(answer_body)
        if send_message_whatsapp:
            logging.info("Mensaje enviado correctamente")
        else:
            logging.error("Error al enviar el mensaje")
    except Exception as e:
        logging.error(f"Error al procesar el mensaje individual: {e}")
        
        
def download_media(media_id, media_type):
    try:
        token = "EAANIN5buPuIBO8qy3ZBm3RzI8E9YJ42DA25nOo1sPyVBYeJ9V7WQbKUL9WJwLIlB1TEGXKw65ku7IXz0AtAS64Yd3Y9Yp4UYr9JqpqCxzUp96TbzZCFN4wW2bSFZCMugSuS85hHVm29HIJuGfbThdQzWV3eifpFCz4GZBWm549ZAQggAXVhBnBRfIiktM6Tre"
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(url, headers=headers)
        media_url = response.json().get('url')
        media_response = requests.get(media_url, headers=headers)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{media_id}.{media_type.split('/')[1]}")
        with open(file_path, 'wb') as f:
            f.write(media_response.content)
        logging.info(f"Archivo descargado: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Error en download_media: {e}")
        return None

def detect_audio_language(file_path):
    return 'es'

def upload_media_to_whatsapp(file_path, media_type):
    try:
        token = config('TOKEN_WHATSAPP')
        url = "https://graph.facebook.com/v18.0/245533201976802/media"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        files = {
            'file': (file_path, open(file_path, 'rb'), media_type)
        }
        data = {
            'messaging_product': 'whatsapp'
        }
        response = requests.post(url, headers=headers, files=files, data=data)
        media_id = response.json().get('id')
        logging.info(f"Archivo subido a WhatsApp: {media_id}")
        return media_id
    except Exception as e:
        logging.error(f"Error en upload_media_to_whatsapp: {e}")
        return None

def WhatsappService(body):
    try:
        token = config('TOKEN_WHATSAPP')
        api_url = "https://graph.facebook.com/v18.0/245533201976802/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        response = requests.post(api_url, data=json.dumps(body), headers=headers)
        logging.info(f"Respuesta de WhatsApp API: {response.status_code} - {response.text}")
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error en WhatsappService: {e}")
        return False

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8082, debug=True)