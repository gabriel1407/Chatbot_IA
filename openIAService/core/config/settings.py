"""
Configuración centralizada de la aplicación.
Usa Pydantic para validación de configuración.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Configuración de la aplicación con validación.
    Las variables se cargan desde .env automáticamente.
    """
    
    # Configuración general
    app_name: str = "Chatbot IA"
    debug: bool = False
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Flask
    secret_key: str = Field(..., env="SECRET_KEY")
    host: str = "0.0.0.0"
    port: int = 8082
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 600
    openai_temperature: float = 0.7
    
    # Telegram
    telegram_token: str = Field(..., env="TELEGRAM_TOKEN")
    telegram_api_url: Optional[str] = None
    
    # WhatsApp
    whatsapp_token: str = Field(..., env="TOKEN_WHATSAPP")
    whatsapp_api_url: str = "https://graph.facebook.com/v18.0/245533201976802/messages"
    whatsapp_verify_token: str = "E23431A21A991BE82FF3D79D5F1F8"
    
    # SerpAPI (búsqueda web)
    serpapi_key: Optional[str] = Field(None, env="SERPAPI_KEY")
    
    # Rutas
    upload_folder: str = "local/uploads"
    db_path: str = "local/contextos.db"
    vector_store_path: str = "local/vector_store"
    
    # RAG Configuration
    rag_enabled: bool = True
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5
    rag_min_similarity: float = 0.7
    
    # Context Window
    max_context_tokens: int = 4000
    context_summary_threshold: int = 3000
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    @validator("telegram_api_url", always=True)
    def set_telegram_api_url(cls, v, values):
        """Genera la URL de Telegram API automáticamente."""
        if v is None and "telegram_token" in values:
            return f"https://api.telegram.org/bot{values['telegram_token']}"
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()
