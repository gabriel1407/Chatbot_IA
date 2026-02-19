"""
Servicio para detectar cambios de tema en conversaciones.
Implementa Single Responsibility Principle.
"""
from typing import List
from core.logging.logger import get_infrastructure_logger


class TopicDetectionService:
    """
    Servicio para detectar cambios de tema en conversaciones.
    """

    def __init__(self):
        self.logger = get_infrastructure_logger()
        self._topic_keywords = [
            # Español
            "nuevo tema", "hablemos de", "cambia de tema", "cambiar de tema",
            "nueva conversación", "otro asunto", "otra pregunta", "hablemos sobre",
            "hablar de", "nuevo tópico", "hablar ahora de", "quisiera preguntar sobre",
            "otra cosa", "cambiar el tema", "tema diferente", "empezar otro tema",
            "quiero hablar de", "tengo otra duda", "podemos cambiar de tema",
            "ahora quiero preguntar", "otra consulta", "consultar otra cosa",
            "otra pregunta", "cambiando de tema",
            # Inglés
            "start new topic", "change topic", "new conversation", "different subject",
            "let's talk about", "can we talk about", "new subject", "another topic",
            "move on to",
        ]

    def detect_new_topic(self, user_input: str) -> bool:
        """
        Detecta si el usuario quiere empezar un nuevo tema.

        Args:
            user_input: Entrada del usuario

        Returns:
            True si se detecta cambio de tema
        """
        if not user_input or not user_input.strip():
            return False

        lower_input = user_input.lower().strip()
        topic_detected = any(phrase in lower_input for phrase in self._topic_keywords)

        if topic_detected:
            self.logger.info(f"Nuevo tema detectado en: '{user_input[:50]}...'")

        return topic_detected

    def add_keyword(self, keyword: str) -> None:
        """Agrega una nueva palabra clave para detección de temas."""
        if keyword and keyword.lower() not in self._topic_keywords:
            self._topic_keywords.append(keyword.lower())
            self.logger.info(f"Nueva palabra clave agregada: '{keyword}'")

    def get_keywords(self) -> List[str]:
        """Obtiene todas las palabras clave configuradas."""
        return self._topic_keywords.copy()
