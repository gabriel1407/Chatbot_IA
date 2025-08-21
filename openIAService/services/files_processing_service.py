import os
import hashlib
import time
import fitz  # PyMuPDF
import docx
import pytesseract
import speech_recognition as sr
from pydub import AudioSegment
import logging
from openIAService.services.cache_service import (
    cache_file_processing,
    get_cached_file_processing,
)
from openIAService.services.metrics_service import log_file_processing, measure_time

UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def _hash_file(file_path: str) -> str:
    """Calcula un hash MD5 del archivo para usarlo como clave de caché."""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()

@measure_time("process_pdf")
def process_pdf(file_path):
    """Extrae el texto de un archivo PDF con caché y métricas."""
    start = time.time()
    try:
        file_hash = _hash_file(file_path)
        cached = get_cached_file_processing(file_path, file_hash)
        if cached is not None:
            logging.info(f"[FILES] PDF cache hit: {file_path}")
            log_file_processing("pdf", os.path.getsize(file_path), time.time() - start)
            return cached

        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        cache_file_processing(file_path, file_hash, text)
        logging.info(f"PDF procesado correctamente: {file_path}")
        return text
    except Exception as e:
        logging.error(f"Error al procesar PDF: {e}")
        return ""
    finally:
        try:
            log_file_processing("pdf", os.path.getsize(file_path), time.time() - start)
        except Exception:
            pass

@measure_time("process_docx")
def process_docx(file_path):
    """Extrae el texto de un archivo DOCX con caché y métricas."""
    start = time.time()
    try:
        file_hash = _hash_file(file_path)
        cached = get_cached_file_processing(file_path, file_hash)
        if cached is not None:
            logging.info(f"[FILES] DOCX cache hit: {file_path}")
            log_file_processing("docx", os.path.getsize(file_path), time.time() - start)
            return cached

        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        cache_file_processing(file_path, file_hash, text)
        logging.info(f"DOCX procesado correctamente: {file_path}")
        return text
    except Exception as e:
        logging.error(f"Error al procesar DOCX: {e}")
        return "Error al procesar el documento."
    finally:
        try:
            log_file_processing("docx", os.path.getsize(file_path), time.time() - start)
        except Exception:
            pass

@measure_time("process_image")
def process_image(file_path):
    """Extrae el texto de una imagen usando OCR con caché y métricas."""
    start = time.time()
    try:
        if not os.path.exists(file_path):
            logging.error(f"El archivo de imagen no existe: {file_path}")
            return "Error: el archivo de imagen no existe."
        file_hash = _hash_file(file_path)
        cached = get_cached_file_processing(file_path, file_hash)
        if cached is not None:
            logging.info(f"[FILES] IMAGE cache hit: {file_path}")
            log_file_processing("image", os.path.getsize(file_path), time.time() - start)
            return cached

        logging.info(f"Procesando imagen con pytesseract: {file_path}")
        text = pytesseract.image_to_string(file_path)
        text = text if text.strip() else "No se pudo extraer texto de la imagen."
        cache_file_processing(file_path, file_hash, text)
        logging.info(f"Imagen procesada correctamente: {file_path}")
        return text
    except Exception as e:
        logging.error(f"Error al procesar imagen: {e}", exc_info=True)
        return "Error al analizar la imagen."
    finally:
        try:
            log_file_processing("image", os.path.getsize(file_path), time.time() - start)
        except Exception:
            pass

@measure_time("process_audio")
def process_audio(file_path, language='es'):
    """Convierte un archivo de audio a texto usando reconocimiento de voz con caché y métricas."""
    start = time.time()
    recognizer = sr.Recognizer()
    try:
        file_hash = _hash_file(file_path)
        cached = get_cached_file_processing(file_path, file_hash)
        if cached is not None:
            logging.info(f"[FILES] AUDIO cache hit: {file_path}")
            log_file_processing("audio", os.path.getsize(file_path), time.time() - start)
            return cached

        audio = AudioSegment.from_file(file_path)
        wav_path = file_path.replace(file_path.split('.')[-1], 'wav')
        audio.export(wav_path, format="wav")
        
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=language)
            cache_file_processing(file_path, file_hash, text)
            return text
    except sr.UnknownValueError:
        return "No se pudo reconocer el audio."
    except sr.RequestError:
        return "Error en el servicio de reconocimiento de voz."
    except Exception as e:
        logging.error(f"Error al procesar audio: {e}")
        return "Error al procesar el audio."
    finally:
        try:
            log_file_processing("audio", os.path.getsize(file_path), time.time() - start)
        except Exception:
            pass

def process_document(file_path, file_type):
    """Procesa documentos según su tipo (PDF o DOCX) y extrae el texto."""
    start = time.time()
    try:
        file_hash = _hash_file(file_path)
        cached = get_cached_file_processing(file_path, file_hash)
        if cached is not None:
            logging.info(f"[FILES] DOCUMENT cache hit: {file_path}")
            log_file_processing("document", os.path.getsize(file_path), time.time() - start)
            return cached

        if file_type == "pdf":
            return process_pdf(file_path)
        elif file_type == "docx":
            return process_docx(file_path)
        else:
            return "Formato de documento no soportado."
    except Exception as e:
        logging.error(f"Error al procesar documento: {e}")
        return ""
    finally:
        try:
            log_file_processing("document", os.path.getsize(file_path), time.time() - start)
        except Exception:
            pass