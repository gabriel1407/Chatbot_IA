import os
import fitz  # PyMuPDF
import docx
import pytesseract
import speech_recognition as sr
from pydub import AudioSegment
from core.logging.logger import get_app_logger

# Usar el nuevo sistema de logging centralizado
logger = get_app_logger()

UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def process_pdf(file_path):
    """Extrae el texto de un archivo PDF."""
    text = ""
    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        logger.info(f"PDF procesado correctamente: {file_path}")
    except Exception as e:
        logger.error(f"Error al procesar PDF: {e}")
    return text

def process_docx(file_path):
    """Extrae el texto de un archivo DOCX."""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        logger.info(f"DOCX procesado correctamente: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error al procesar DOCX: {e}")
        return "Error al procesar el documento."

def process_image(file_path):
    """Extrae el texto de una imagen usando OCR."""
    try:
        if not os.path.exists(file_path):
            logger.error(f"El archivo de imagen no existe: {file_path}")
            return "Error: el archivo de imagen no existe."
        logger.info(f"Procesando imagen con pytesseract: {file_path}")
        text = pytesseract.image_to_string(file_path)
        logger.info(f"Imagen procesada correctamente: {file_path}")
        return text if text.strip() else "No se pudo extraer texto de la imagen."
    except Exception as e:
        logger.error(f"Error al procesar imagen: {e}", exc_info=True)
        return "Error al analizar la imagen."

def process_audio(file_path, language='es'):
    """Convierte un archivo de audio a texto usando reconocimiento de voz."""
    recognizer = sr.Recognizer()
    try:
        audio = AudioSegment.from_file(file_path)
        wav_path = file_path.replace(file_path.split('.')[-1], 'wav')
        audio.export(wav_path, format="wav")
        
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language=language)
    except sr.UnknownValueError:
        return "No se pudo reconocer el audio."
    except sr.RequestError:
        return "Error en el servicio de reconocimiento de voz."
    except Exception as e:
        logger.error(f"Error al procesar audio: {e}")
        return "Error al procesar el audio."

def process_document(file_path, file_type):
    """Procesa documentos según su tipo (PDF o DOCX) y extrae el texto."""
    if file_type == "pdf":
        return process_pdf(file_path)
    elif file_type == "docx":
        return process_docx(file_path)
    else:
        return "Formato de documento no soportado."