"""
Interface LLMService - Define el contrato para servicios de LLM.
Abstracción que permite cambiar de proveedor (OpenAI, Anthropic, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.message import Message


class LLMService(ABC):
    """
    Interface para servicios de Language Model.
    Permite abstraer el proveedor específico (OpenAI, Anthropic, etc.).
    """
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 600
    ) -> str:
        """
        Genera una respuesta basada en los mensajes.
        
        Args:
            messages: Lista de mensajes de contexto
            system_prompt: Prompt del sistema (opcional)
            temperature: Temperatura para generación (0-1)
            max_tokens: Máximo de tokens a generar
            
        Returns:
            Respuesta generada
        """
        pass
    
    @abstractmethod
    def generate_vision_response(
        self,
        prompt: str,
        image_path: str,
        max_tokens: int = 800
    ) -> str:
        """
        Genera una respuesta analizando una imagen.
        
        Args:
            prompt: Pregunta sobre la imagen
            image_path: Ruta de la imagen
            max_tokens: Máximo de tokens a generar
            
        Returns:
            Respuesta generada
        """
        pass
    
    @abstractmethod
    def classify_intent(self, user_message: str) -> str:
        """
        Clasifica la intención del usuario.
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Intención clasificada (ej: "WEB", "MODEL", "DOCUMENT")
        """
        pass
    
    @abstractmethod
    def summarize_conversation(
        self,
        messages: List[Message],
        max_tokens: int = 300
    ) -> str:
        """
        Resume una conversación larga.
        
        Args:
            messages: Lista de mensajes a resumir
            max_tokens: Máximo de tokens para el resumen
            
        Returns:
            Resumen de la conversación
        """
        pass
