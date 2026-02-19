"""
Sistema de logging centralizado para toda la aplicación.
Implementa el patrón Singleton y configuración por módulos.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional


class LoggerFactory:
    """Factory para crear loggers configurados."""
    
    _loggers = {}
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file: Optional[str] = None,
        level: Optional[str] = None
    ) -> logging.Logger:
        """
        Obtiene o crea un logger configurado.
        
        Args:
            name: Nombre del logger
            log_file: Archivo de log (opcional)
            level: Nivel de logging (opcional)
            
        Returns:
            Logger configurado
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        # Usar configuración por defecto en lugar de config externo
        log_level = level or os.getenv('LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Evitar duplicación de handlers
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Formato
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler para archivo
        if log_file:
            file_path = Path(log_file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


# Loggers predefinidos
def get_app_logger() -> logging.Logger:
    """Logger principal de la aplicación."""
    return LoggerFactory.get_logger("chatbot_ia", "logs/app.log")


def get_domain_logger() -> logging.Logger:
    """Logger para capa de dominio."""
    return LoggerFactory.get_logger("domain", "logs/app.log")


def get_application_logger() -> logging.Logger:
    """Logger para capa de aplicación."""
    return LoggerFactory.get_logger("application", "logs/app.log")


def get_infrastructure_logger() -> logging.Logger:
    """Logger para capa de infraestructura."""
    return LoggerFactory.get_logger("infrastructure", "logs/app.log")


def get_telegram_logger() -> logging.Logger:
    """Logger específico para Telegram."""
    return LoggerFactory.get_logger("telegram", "logs/telegram.log")


def get_whatsapp_logger() -> logging.Logger:
    """Logger específico para WhatsApp."""
    return LoggerFactory.get_logger("whatsapp", "logs/whatsapp.log")


def get_rag_logger() -> logging.Logger:
    """Logger específico para RAG."""
    return LoggerFactory.get_logger("rag", os.getenv('LOG_FILE', 'app.log'))
