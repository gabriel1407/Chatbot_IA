import hashlib
import json
import time
import logging
from typing import Optional, Any, Dict
from threading import Lock
from datetime import datetime, timedelta

class InMemoryCache:
    """
    Sistema de caché en memoria con TTL (Time To Live) y límite de tamaño.
    Optimizado para respuestas de OpenAI y contextos frecuentes.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
        
    def _generate_key(self, data: Any) -> str:
        """Genera una clave hash única para los datos."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()
    
    def _is_expired(self, entry: Dict) -> bool:
        """Verifica si una entrada ha expirado."""
        return time.time() > entry['expires_at']
    
    def _cleanup_expired(self):
        """Limpia entradas expiradas."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if current_time > entry['expires_at']
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_oldest(self):
        """Elimina las entradas más antiguas si se alcanza el límite."""
        if len(self.cache) >= self.max_size:
            # Ordena por tiempo de creación y elimina las más antiguas
            sorted_items = sorted(
                self.cache.items(), 
                key=lambda x: x[1]['created_at']
            )
            # Elimina el 20% más antiguo
            to_remove = max(1, len(sorted_items) // 5)
            for i in range(to_remove):
                key = sorted_items[i][0]
                del self.cache[key]
    
    def get(self, key_data: Any) -> Optional[Any]:
        """Obtiene un valor del caché."""
        with self.lock:
            key = self._generate_key(key_data)
            
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            if self._is_expired(entry):
                del self.cache[key]
                self.misses += 1
                return None
            
            # Actualiza el tiempo de último acceso
            entry['last_accessed'] = time.time()
            self.hits += 1
            
            logging.info(f"[CACHE] HIT para clave: {key[:8]}...")
            return entry['value']
    
    def set(self, key_data: Any, value: Any, ttl: Optional[int] = None) -> None:
        """Almacena un valor en el caché."""
        with self.lock:
            key = self._generate_key(key_data)
            ttl = ttl or self.default_ttl
            
            # Limpia entradas expiradas
            self._cleanup_expired()
            
            # Evita entradas si se alcanza el límite
            self._evict_oldest()
            
            current_time = time.time()
            self.cache[key] = {
                'value': value,
                'created_at': current_time,
                'last_accessed': current_time,
                'expires_at': current_time + ttl
            }
            
            logging.info(f"[CACHE] SET para clave: {key[:8]}... (TTL: {ttl}s)")
    
    def delete(self, key_data: Any) -> bool:
        """Elimina una entrada del caché."""
        with self.lock:
            key = self._generate_key(key_data)
            if key in self.cache:
                del self.cache[key]
                logging.info(f"[CACHE] DELETE para clave: {key[:8]}...")
                return True
            return False
    
    def clear(self) -> None:
        """Limpia todo el caché."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logging.info("[CACHE] Caché completamente limpiado")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests
            }

# Instancia global del caché
cache_instance = InMemoryCache(max_size=1000, default_ttl=3600)

def get_openai_cache_key(messages: list, model: str, temperature: float, max_tokens: int) -> dict:
    """Genera una clave de caché para respuestas de OpenAI."""
    return {
        'type': 'openai_response',
        'messages': messages,
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens
    }

def get_context_cache_key(user_id: str, context_id: str) -> dict:
    """Genera una clave de caché para contextos de usuario."""
    return {
        'type': 'user_context',
        'user_id': str(user_id),
        'context_id': str(context_id)
    }

def get_file_processing_cache_key(file_path: str, file_hash: str) -> dict:
    """Genera una clave de caché para procesamiento de archivos."""
    return {
        'type': 'file_processing',
        'file_path': file_path,
        'file_hash': file_hash
    }

def cache_openai_response(messages: list, model: str, temperature: float, max_tokens: int, response: str, ttl: int = 3600):
    """Cachea una respuesta de OpenAI."""
    key = get_openai_cache_key(messages, model, temperature, max_tokens)
    cache_instance.set(key, response, ttl)

def get_cached_openai_response(messages: list, model: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Obtiene una respuesta cacheada de OpenAI."""
    key = get_openai_cache_key(messages, model, temperature, max_tokens)
    return cache_instance.get(key)

def cache_user_context(user_id: str, context_id: str, context: list, ttl: int = 1800):
    """Cachea el contexto de un usuario."""
    key = get_context_cache_key(user_id, context_id)
    cache_instance.set(key, context, ttl)

def get_cached_user_context(user_id: str, context_id: str) -> Optional[list]:
    """Obtiene el contexto cacheado de un usuario."""
    key = get_context_cache_key(user_id, context_id)
    return cache_instance.get(key)

def invalidate_user_context(user_id: str, context_id: str):
    """Invalida el contexto cacheado de un usuario."""
    key = get_context_cache_key(user_id, context_id)
    cache_instance.delete(key)

def cache_file_processing(file_path: str, file_hash: str, result: Any, ttl: int = 7200):
    """Cachea el resultado del procesamiento de un archivo."""
    key = get_file_processing_cache_key(file_path, file_hash)
    cache_instance.set(key, result, ttl)

def get_cached_file_processing(file_path: str, file_hash: str) -> Optional[Any]:
    """Obtiene el resultado cacheado del procesamiento de un archivo."""
    key = get_file_processing_cache_key(file_path, file_hash)
    return cache_instance.get(key)

def get_cache_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del caché."""
    return cache_instance.get_stats()

def clear_cache():
    """Limpia todo el caché."""
    cache_instance.clear()
