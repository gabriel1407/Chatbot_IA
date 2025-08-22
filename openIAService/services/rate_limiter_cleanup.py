import time
import threading
from collections import defaultdict, deque
from typing import Dict

class CleanupRateLimiter:
    """Rate limiter con limpieza automática para evitar memory leaks."""
    
    def __init__(self, cleanup_interval: int = 300):  # 5 minutos
        self._lock = threading.Lock()
        self._events: Dict[str, deque] = defaultdict(deque)
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Limpia entradas antiguas para evitar memory leaks."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
            
        with self._lock:
            # Elimina claves que no han tenido actividad en 1 hora
            cutoff = now - 3600
            keys_to_remove = []
            
            for key, dq in self._events.items():
                # Limpia eventos antiguos de esta clave
                while dq and dq[0] < cutoff:
                    dq.popleft()
                # Si no quedan eventos, marca para eliminación
                if not dq:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._events[key]
            
            self._last_cleanup = now
    
    def is_allowed(self, key: str, limit: int = 20, window_seconds: int = 60) -> bool:
        """Verifica si la acción está permitida bajo el límite."""
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - window_seconds
        
        with self._lock:
            dq = self._events[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            
            if len(dq) < limit:
                dq.append(now)
                return True
            return False
    
    def remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """Retorna el número de requests restantes."""
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - window_seconds
        
        with self._lock:
            dq = self._events[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            return max(0, limit - len(dq))

# Instancia global con limpieza automática
rate_limiter = CleanupRateLimiter()

def is_allowed(key: str, limit: int = 20, window_seconds: int = 60) -> bool:
    return rate_limiter.is_allowed(key, limit, window_seconds)

def remaining(key: str, limit: int, window_seconds: int) -> int:
    return rate_limiter.remaining(key, limit, window_seconds)
