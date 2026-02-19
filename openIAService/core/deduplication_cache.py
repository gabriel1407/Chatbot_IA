"""
Cache de deduplicación compartido entre workers usando SQLite.
Previene procesamiento duplicado de mensajes en entorno multi-worker.
"""
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path


class DuplicationCache:
    """
    Cache compartido para deduplicación de mensajes entre workers de Gunicorn.
    Usa SQLite con file-locking para sincronización entre procesos.
    """
    
    def __init__(self, db_path: str = "local/deduplication.db", expiry_hours: int = 24):
        """
        Inicializa cache de deduplicación.
        
        Args:
            db_path: Ruta al archivo SQLite
            expiry_hours: Horas de expiración de mensajes en cache
        """
        self.db_path = db_path
        self.expiry_hours = expiry_hours
        self._local = threading.local()  # Thread-local para conexiones
        self._ensure_db_directory()
        self._init_db()
    
    def _ensure_db_directory(self):
        """Crea el directorio para la base de datos si no existe."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión thread-local con timeout para evitar locks."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                timeout=5.0,  # 5 segundos de timeout para locks
                check_same_thread=False
            )
            # Habilitar Write-Ahead Logging para mejor concurrencia
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn
    
    def _init_db(self):
        """Inicializa la tabla de deduplicación."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    processed_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            # Índice para limpieza eficiente de mensajes expirados
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON processed_messages(expires_at)
            """)
            conn.commit()
        except sqlite3.Error as e:
            # Log pero no fallar la inicialización
            print(f"Warning: Error inicializando tabla de deduplicación: {e}")
    
    def is_processed(self, message_id: str, channel: str) -> bool:
        """
        Verifica si un mensaje ya fue procesado.
        
        Args:
            message_id: ID único del mensaje
            channel: Canal de origen (whatsapp, telegram, etc.)
            
        Returns:
            True si el mensaje ya fue procesado
        """
        if not message_id:
            return False
        
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT 1 FROM processed_messages 
                WHERE message_id = ? AND channel = ? AND expires_at > ?
            """, (message_id, channel, datetime.now()))
            
            result = cursor.fetchone() is not None
            return result
            
        except sqlite3.Error as e:
            # En caso de error de DB, permitir procesamiento (fail-safe)
            print(f"Warning: Error verificando mensaje duplicado: {e}")
            return False
    
    def mark_processed(self, message_id: str, channel: str) -> bool:
        """
        Marca un mensaje como procesado.
        
        Args:
            message_id: ID único del mensaje
            channel: Canal de origen
            
        Returns:
            True si se marcó exitosamente
        """
        if not message_id:
            return False
        
        conn = self._get_connection()
        try:
            now = datetime.now()
            expires_at = now + timedelta(hours=self.expiry_hours)
            
            conn.execute("""
                INSERT OR REPLACE INTO processed_messages 
                (message_id, channel, processed_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (message_id, channel, now, expires_at))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Warning: Error marcando mensaje como procesado: {e}")
            conn.rollback()
            return False
    
    def cleanup_expired(self) -> int:
        """
        Limpia mensajes expirados del cache.
        
        Returns:
            Número de registros eliminados
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                DELETE FROM processed_messages 
                WHERE expires_at <= ?
            """, (datetime.now(),))
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
            
        except sqlite3.Error as e:
            print(f"Warning: Error limpiando cache: {e}")
            conn.rollback()
            return 0
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas del cache."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN expires_at > ? THEN 1 END) as active,
                    MIN(processed_at) as oldest,
                    MAX(processed_at) as newest
                FROM processed_messages
            """, (datetime.now(),))
            
            row = cursor.fetchone()
            return {
                "total_records": row[0],
                "active_records": row[1],
                "oldest_record": row[2],
                "newest_record": row[3]
            }
            
        except sqlite3.Error as e:
            print(f"Warning: Error obteniendo stats: {e}")
            return {}
    
    def close(self):
        """Cierra conexión thread-local."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Instancia singleton compartida
_cache_instance: Optional[DuplicationCache] = None


def get_deduplication_cache() -> DuplicationCache:
    """Factory function para obtener instancia singleton del cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DuplicationCache()
    return _cache_instance
