"""
Utilidades generales para la aplicación.
"""
import uuid
from typing import List
from domain.entities.message import Message


def generate_uuid() -> str:
    """
    Genera un UUID único.
    
    Returns:
        UUID como string
    """
    return str(uuid.uuid4())


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Trunca un texto a una longitud máxima.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        
    Returns:
        Texto truncado
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def estimate_tokens(text: str) -> int:
    """
    Estima el número de tokens en un texto.
    Aproximación simple: ~4 caracteres por token.
    
    Args:
        text: Texto a analizar
        
    Returns:
        Número estimado de tokens
    """
    return len(text) // 4


def count_tokens_in_messages(messages: List[Message]) -> int:
    """
    Cuenta los tokens totales en una lista de mensajes.
    
    Args:
        messages: Lista de mensajes
        
    Returns:
        Número total de tokens estimados
    """
    return sum(estimate_tokens(msg.content) for msg in messages)


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo removiendo caracteres peligrosos.
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo sanitizado
    """
    import re
    # Remueve caracteres no alfanuméricos excepto . - _
    sanitized = re.sub(r'[^\w\s\-\.]', '', filename)
    # Reemplaza espacios con guiones bajos
    sanitized = sanitized.replace(' ', '_')
    return sanitized


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[str]:
    """
    Divide un texto en chunks con overlap.
    
    Args:
        text: Texto a dividir
        chunk_size: Tamaño de cada chunk
        chunk_overlap: Overlap entre chunks
        
    Returns:
        Lista de chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
    
    return chunks
