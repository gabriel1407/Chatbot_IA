"""
Context Cleanup Service - Limpieza automática de contextos cada 24 horas.
Implementa principios SOLID y Clean Code.
"""
import os
import sqlite3
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Protocol
from abc import ABC, abstractmethod


class ContextCleanupStrategy(ABC):
    """Strategy pattern para diferentes estrategias de limpieza."""
    
    @abstractmethod
    def should_cleanup(self, last_updated: datetime, threshold_hours: int = 24) -> bool:
        """Determina si un contexto debe ser limpiado."""
        pass
    
    @abstractmethod
    def get_cleanup_description(self) -> str:
        """Descripción de la estrategia de limpieza."""
        pass


class TimeBasedCleanupStrategy(ContextCleanupStrategy):
    """Estrategia de limpieza basada en tiempo."""
    
    def should_cleanup(self, last_updated: datetime, threshold_hours: int = 24) -> bool:
        """Limpia contextos más viejos que threshold_hours."""
        threshold = datetime.now() - timedelta(hours=threshold_hours)
        return last_updated < threshold
    
    def get_cleanup_description(self) -> str:
        return "Limpieza basada en tiempo (24 horas)"


class InactivityBasedCleanupStrategy(ContextCleanupStrategy):
    """Estrategia de limpieza basada en inactividad."""
    
    def should_cleanup(self, last_updated: datetime, threshold_hours: int = 48) -> bool:
        """Limpia contextos inactivos por más de threshold_hours."""
        threshold = datetime.now() - timedelta(hours=threshold_hours)
        return last_updated < threshold
    
    def get_cleanup_description(self) -> str:
        return "Limpieza basada en inactividad (48 horas)"


class ContextCleanupRepository:
    """Repositorio para operaciones de limpieza de contextos."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión a la base de datos."""
        return sqlite3.connect(self.db_path)
    
    def get_old_contexts(self, threshold_hours: int = 24) -> list[tuple]:
        """
        Obtiene contextos candidatos para limpieza.
        
        Args:
            threshold_hours: Horas de antigüedad para considerar limpieza
            
        Returns:
            Lista de tuplas (user_id, context_id, last_updated)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                threshold_date = datetime.now() - timedelta(hours=threshold_hours)
                
                cursor.execute("""
                    SELECT user_id, context_id, last_updated
                    FROM user_context 
                    WHERE last_updated < ?
                    ORDER BY last_updated ASC
                """, (threshold_date,))
                
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error obteniendo contextos antiguos: {e}")
            return []
    
    def delete_context(self, user_id: str, context_id: str) -> bool:
        """
        Elimina un contexto específico.
        
        Args:
            user_id: ID del usuario
            context_id: ID del contexto
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM user_context 
                    WHERE user_id = ? AND context_id = ?
                """, (user_id, context_id))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"Contexto eliminado: user={user_id}, context={context_id}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Error eliminando contexto {user_id}/{context_id}: {e}")
            return False
    
    def get_context_stats(self) -> dict:
        """Obtiene estadísticas de contextos almacenados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total de contextos
                cursor.execute("SELECT COUNT(*) FROM user_context")
                total_contexts = cursor.fetchone()[0]
                
                # Contextos únicos por usuario
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_context")
                unique_users = cursor.fetchone()[0]
                
                # Contexto más antiguo
                cursor.execute("SELECT MIN(last_updated) FROM user_context")
                oldest_context = cursor.fetchone()[0]
                
                return {
                    "total_contexts": total_contexts,
                    "unique_users": unique_users,
                    "oldest_context": oldest_context
                }
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}


class ContextCleanupService:
    """
    Servicio principal de limpieza de contextos.
    Implementa Single Responsibility Principle.
    """
    
    def __init__(
        self,
        repository: ContextCleanupRepository,
        cleanup_strategy: ContextCleanupStrategy,
        cleanup_interval_hours: int = 24,
        threshold_hours: int = 24
    ):
        self.repository = repository
        self.cleanup_strategy = cleanup_strategy
        self.cleanup_interval_hours = cleanup_interval_hours
        self.threshold_hours = threshold_hours
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._last_cleanup: Optional[datetime] = None
    
    def cleanup_old_contexts(self) -> dict:
        """
        Ejecuta la limpieza de contextos antiguos.
        
        Returns:
            Diccionario con estadísticas de la limpieza
        """
        start_time = datetime.now()
        cleaned_count = 0
        errors_count = 0
        
        self.logger.info("Iniciando limpieza de contextos...")
        self.logger.info(f"Estrategia: {self.cleanup_strategy.get_cleanup_description()}")
        
        try:
            # Obtener contextos candidatos
            old_contexts = self.repository.get_old_contexts(self.threshold_hours)
            
            if not old_contexts:
                self.logger.info("No hay contextos para limpiar")
                return {
                    "cleaned_count": 0,
                    "errors_count": 0,
                    "duration_seconds": 0,
                    "strategy": self.cleanup_strategy.get_cleanup_description()
                }
            
            self.logger.info(f"Encontrados {len(old_contexts)} contextos candidatos para limpieza")
            
            # Procesar cada contexto
            for user_id, context_id, last_updated_str in old_contexts:
                try:
                    # Convertir string a datetime
                    if isinstance(last_updated_str, str):
                        last_updated = datetime.fromisoformat(last_updated_str)
                    else:
                        last_updated = last_updated_str
                    
                    # Verificar si debe ser limpiado según la estrategia
                    if self.cleanup_strategy.should_cleanup(last_updated, self.threshold_hours):
                        if self.repository.delete_context(user_id, context_id):
                            cleaned_count += 1
                        else:
                            errors_count += 1
                            
                except Exception as e:
                    self.logger.error(f"Error procesando contexto {user_id}/{context_id}: {e}")
                    errors_count += 1
            
            duration = (datetime.now() - start_time).total_seconds()
            self._last_cleanup = datetime.now()
            
            self.logger.info(f"Limpieza completada: {cleaned_count} eliminados, {errors_count} errores, {duration:.2f}s")
            
            return {
                "cleaned_count": cleaned_count,
                "errors_count": errors_count,
                "duration_seconds": round(duration, 2),
                "strategy": self.cleanup_strategy.get_cleanup_description(),
                "timestamp": self._last_cleanup.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error en limpieza de contextos: {e}")
            return {
                "cleaned_count": 0,
                "errors_count": 1,
                "error": str(e),
                "strategy": self.cleanup_strategy.get_cleanup_description()
            }
    
    def start_automatic_cleanup(self) -> None:
        """Inicia la limpieza automática en background."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self.logger.warning("La limpieza automática ya está en ejecución")
            return
        
        self.logger.info(f"Iniciando limpieza automática cada {self.cleanup_interval_hours} horas")
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop_automatic_cleanup(self) -> None:
        """Detiene la limpieza automática."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self.logger.info("Deteniendo limpieza automática...")
            self._stop_event.set()
            self._cleanup_thread.join(timeout=10)
            if self._cleanup_thread.is_alive():
                self.logger.warning("No se pudo detener la limpieza automática limpiamente")
        else:
            self.logger.info("La limpieza automática no estaba en ejecución")
    
    def _cleanup_loop(self) -> None:
        """Loop principal de limpieza automática."""
        while not self._stop_event.is_set():
            try:
                # Ejecutar limpieza
                stats = self.cleanup_old_contexts()
                
                # Esperar hasta la próxima ejecución
                sleep_seconds = self.cleanup_interval_hours * 3600  # horas a segundos
                
                # Dormir en pequeños intervalos para poder responder al stop_event
                elapsed = 0
                while elapsed < sleep_seconds and not self._stop_event.is_set():
                    time.sleep(60)  # Dormir 1 minuto
                    elapsed += 60
                    
            except Exception as e:
                self.logger.error(f"Error en loop de limpieza automática: {e}")
                time.sleep(300)  # Esperar 5 minutos antes de reintentar
    
    def get_status(self) -> dict:
        """Obtiene el estado actual del servicio de limpieza."""
        return {
            "is_running": self._cleanup_thread is not None and self._cleanup_thread.is_alive(),
            "last_cleanup": self._last_cleanup.isoformat() if self._last_cleanup else None,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "threshold_hours": self.threshold_hours,
            "strategy": self.cleanup_strategy.get_cleanup_description(),
            "repository_stats": self.repository.get_context_stats()
        }


# Factory para crear el servicio con configuración por defecto
def create_context_cleanup_service(
    db_path: str = "local/contextos.db",
    cleanup_strategy: str = "time_based"
) -> ContextCleanupService:
    """
    Factory function para crear el servicio de limpieza.
    
    Args:
        db_path: Ruta a la base de datos SQLite
        cleanup_strategy: Estrategia de limpieza ("time_based" o "inactivity_based")
        
    Returns:
        Instancia configurada del servicio
    """
    repository = ContextCleanupRepository(db_path)
    
    if cleanup_strategy == "inactivity_based":
        strategy = InactivityBasedCleanupStrategy()
    else:
        strategy = TimeBasedCleanupStrategy()
    
    return ContextCleanupService(
        repository=repository,
        cleanup_strategy=strategy,
        cleanup_interval_hours=24,  # Ejecutar cada 24 horas
        threshold_hours=24  # Limpiar contextos mayores a 24 horas
    )