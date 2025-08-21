import time
import logging
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Any
from functools import wraps

class MetricsCollector:
    """
    Recolector de métricas para monitorear el rendimiento del chatbot.
    """
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.response_times = defaultdict(deque)
        self.error_counts = defaultdict(int)
        self.lock = threading.Lock()
        
        # Configuración de ventanas de tiempo
        self.time_window = 3600  # 1 hora
        self.max_samples = 1000  # Máximo de muestras por métrica
    
    def record_response_time(self, service: str, duration: float):
        """Registra el tiempo de respuesta de un servicio."""
        with self.lock:
            current_time = time.time()
            self.response_times[service].append((current_time, duration))
            
            # Limpia datos antiguos
            cutoff_time = current_time - self.time_window
            while (self.response_times[service] and 
                   self.response_times[service][0][0] < cutoff_time):
                self.response_times[service].popleft()
            
            # Limita el número de muestras
            if len(self.response_times[service]) > self.max_samples:
                self.response_times[service].popleft()
    
    def increment_counter(self, metric: str, value: int = 1):
        """Incrementa un contador."""
        with self.lock:
            self.counters[metric] += value
    
    def record_error(self, service: str, error_type: str = "general"):
        """Registra un error."""
        with self.lock:
            error_key = f"{service}_{error_type}"
            self.error_counts[error_key] += 1
            self.increment_counter(f"errors_{service}")
    
    def get_response_time_stats(self, service: str) -> Dict[str, float]:
        """Obtiene estadísticas de tiempo de respuesta para un servicio."""
        with self.lock:
            if service not in self.response_times or not self.response_times[service]:
                return {"count": 0, "avg": 0, "min": 0, "max": 0, "p95": 0}
            
            times = [duration for _, duration in self.response_times[service]]
            times.sort()
            
            count = len(times)
            avg = sum(times) / count
            min_time = min(times)
            max_time = max(times)
            p95_index = int(0.95 * count)
            p95 = times[p95_index] if p95_index < count else max_time
            
            return {
                "count": count,
                "avg": round(avg, 3),
                "min": round(min_time, 3),
                "max": round(max_time, 3),
                "p95": round(p95, 3)
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Obtiene todas las estadísticas."""
        with self.lock:
            stats = {
                "counters": dict(self.counters),
                "errors": dict(self.error_counts),
                "response_times": {}
            }
            
            for service in self.response_times.keys():
                stats["response_times"][service] = self.get_response_time_stats(service)
            
            return stats
    
    def reset_metrics(self):
        """Reinicia todas las métricas."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.response_times.clear()
            self.error_counts.clear()

# Instancia global del recolector de métricas
metrics_collector = MetricsCollector()

def measure_time(service_name: str):
    """
    Decorador para medir el tiempo de ejecución de funciones.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics_collector.increment_counter(f"success_{service_name}")
                return result
            except Exception as e:
                metrics_collector.record_error(service_name, type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_response_time(service_name, duration)
        return wrapper
    return decorator

def log_user_interaction(user_id: str, platform: str, message_type: str):
    """Registra una interacción de usuario."""
    metrics_collector.increment_counter("total_messages")
    metrics_collector.increment_counter(f"messages_{platform}")
    metrics_collector.increment_counter(f"messages_{message_type}")
    
    logging.info(f"[METRICS] Interacción: usuario={user_id}, plataforma={platform}, tipo={message_type}")

def log_openai_usage(model: str, tokens_used: int, cached: bool = False):
    """Registra el uso de OpenAI."""
    if cached:
        metrics_collector.increment_counter("openai_cache_hits")
    else:
        metrics_collector.increment_counter("openai_api_calls")
        metrics_collector.increment_counter("openai_tokens_used", tokens_used)
        metrics_collector.increment_counter(f"openai_tokens_{model}", tokens_used)

def log_file_processing(file_type: str, file_size: int, processing_time: float):
    """Registra el procesamiento de archivos."""
    metrics_collector.increment_counter("files_processed")
    metrics_collector.increment_counter(f"files_{file_type}")
    metrics_collector.record_response_time("file_processing", processing_time)
    
    # Registra el tamaño del archivo en categorías
    if file_size < 1024 * 1024:  # < 1MB
        size_category = "small"
    elif file_size < 10 * 1024 * 1024:  # < 10MB
        size_category = "medium"
    else:
        size_category = "large"
    
    metrics_collector.increment_counter(f"files_size_{size_category}")

def get_performance_report() -> Dict[str, Any]:
    """Genera un reporte de rendimiento completo."""
    from openIAService.services.cache_service import get_cache_stats
    
    stats = metrics_collector.get_all_stats()
    cache_stats = get_cache_stats()
    
    # Calcula métricas derivadas
    total_messages = stats["counters"].get("total_messages", 0)
    cache_hits = stats["counters"].get("openai_cache_hits", 0)
    api_calls = stats["counters"].get("openai_api_calls", 0)
    total_openai_requests = cache_hits + api_calls
    
    cache_hit_rate = (cache_hits / total_openai_requests * 100) if total_openai_requests > 0 else 0
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_messages": total_messages,
            "openai_cache_hit_rate": round(cache_hit_rate, 2),
            "total_errors": sum(stats["errors"].values()),
            "files_processed": stats["counters"].get("files_processed", 0)
        },
        "detailed_stats": stats,
        "cache_stats": cache_stats,
        "response_times": stats["response_times"]
    }
    
    return report

def log_performance_summary():
    """Registra un resumen de rendimiento en los logs."""
    report = get_performance_report()
    summary = report["summary"]
    
    logging.info(f"[PERFORMANCE] Resumen: "
                f"Mensajes={summary['total_messages']}, "
                f"Cache Hit Rate={summary['openai_cache_hit_rate']}%, "
                f"Errores={summary['total_errors']}, "
                f"Archivos={summary['files_processed']}")

# Función para inicializar métricas periódicas
def start_metrics_logging():
    """Inicia el logging periódico de métricas."""
    import threading
    
    def periodic_logging():
        while True:
            time.sleep(300)  # Cada 5 minutos
            log_performance_summary()
    
    thread = threading.Thread(target=periodic_logging, daemon=True)
    thread.start()
    logging.info("[METRICS] Sistema de métricas iniciado")
