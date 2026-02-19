"""
Configuración centralizada de la aplicación.
Usa Pydantic para validación de configuración.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, AliasChoices

# Load .env file explicitly before creating Settings
from dotenv import load_dotenv

# Try multiple locations for .env file
env_files = [
    Path(__file__).parent.parent.parent.parent / ".env",  # /app/.env
    Path("/app/.env"),  # /app/.env (absolute)
    Path.cwd() / ".env",  # Current working directory
]

for env_file in env_files:
    if env_file.exists():
        print(f"[Settings] Loading .env from {env_file}")
        load_dotenv(env_file)
        break

# Debug: print presence of critical env vars
try:
    print("[Settings][Debug] ENV keys snapshot:")
    for k in [
        "ENVIRONMENT",
        "SECRET_KEY",
        "OPENAI_API_KEY",
        "TELEGRAM_TOKEN",
        "TOKEN_WHATSAPP",
        "CHROMA_HOST",
        "CHROMA_PORT",
    ]:
        v = os.environ.get(k)
        print(f"  - {k}={'<set>' if v else '<missing>'}")
except Exception as e:
    print(f"[Settings][Debug] Failed to print env snapshot: {e}")


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
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")  # Opcional si usas Gemini u Ollama
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 600
    openai_temperature: float = 0.7

    # Multi-provider AI settings
    # Which provider to use by default: 'openai', 'gemini', 'ollama', etc.
    ai_provider: str = Field(default="ollama")

    # Gemini (Google) credentials / endpoint (optional)
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    gemini_api_url: Optional[str] = Field(None, env="GEMINI_API_URL")
    # Gemini model identifier (use model names like 'gemini-pro', 'gemini-1.5-flash')
    gemini_model: Optional[str] = Field(default="gemini-2.5-flash-lite", env="GEMINI_MODEL")
    gemini_embedding_model: Optional[str] = Field(default="gemini-embedding-001", env="GEMINI_EMBEDDING_MODEL")

    # Ollama (local model serving) settings (optional)
    # URL should point to base Ollama server (e.g., http://localhost:11434), not including /api/generate
    ollama_url: Optional[str] = Field(default="http://host.docker.internal:11434", env="OLLAMA_URL")
    ollama_model: Optional[str] = Field(default="gpt-oss:120b-cloud", env="OLLAMA_MODEL")
    ollama_embedding_model: Optional[str] = Field(default="embeddinggemma", env="OLLAMA_EMBEDDING_MODEL")
    ollama_api_key: Optional[str] = Field(None, env="OLLAMA_API_KEY")
    ollama_channel_streaming_enabled: bool = Field(default=False, env="OLLAMA_CHANNEL_STREAMING_ENABLED")
    ollama_channel_thinking_enabled: bool = Field(default=False, env="OLLAMA_CHANNEL_THINKING_ENABLED")
    ollama_max_tokens: int = Field(default=2048, env="OLLAMA_MAX_TOKENS")
    ollama_stream_chunk_size: int = Field(default=120, env="OLLAMA_STREAM_CHUNK_SIZE")
    ollama_stream_max_updates: int = Field(default=20, env="OLLAMA_STREAM_MAX_UPDATES")

    # Tenant por defecto cuando no se especifica X-Tenant-ID en el webhook
    default_tenant_id: str = Field(default="default", env="DEFAULT_TENANT_ID")
    
    # Telegram
    telegram_token: str = Field(..., env="TELEGRAM_TOKEN")
    telegram_api_url: Optional[str] = None
    
    # WhatsApp
    whatsapp_token: str = Field(
        ..., 
        env="TOKEN_WHATSAPP", 
        validation_alias=AliasChoices("TOKEN_WHATSAPP", "WHATSAPP_TOKEN")
    )
    phone_number_id: str = Field(..., env="PHONE_NUMBER_ID")
    whatsapp_api_url: Optional[str] = None
    whatsapp_verify_token: str = Field(
        default="E23431A21A991BE82FF3D79D5F1F8", env="WHATSAPP_VERIFY_TOKEN"
    )
    
    # SerpAPI (búsqueda web)
    serpapi_key: Optional[str] = Field(None, env="SERPAPI_KEY")

    # Admin API Key (legacy, mantenida por compatibilidad)
    admin_api_key: Optional[str] = Field(None, env="ADMIN_API_KEY")

    # JWT Authentication
    # Si JWT_SECRET_KEY no está definida, se usa el SECRET_KEY de Flask como fallback
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_access_token_ttl_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_TTL_MINUTES")
    jwt_refresh_token_ttl_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_TTL_DAYS")
    # Contraseña del admin inicial (si no hay ningún usuario en DB)
    jwt_default_admin_password: str = Field(default="changeme123", env="JWT_DEFAULT_ADMIN_PASSWORD")

    @property
    def effective_jwt_secret(self) -> str:
        """JWT secret efectivo: JWT_SECRET_KEY o fallback a SECRET_KEY."""
        return self.jwt_secret_key or self.secret_key
    
    # Rutas
    upload_folder: str = "local/uploads"
    db_path: str = "local/contextos.db"
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    vector_store_path: str = "local/vector_store"
    chroma_host: str = Field(default="chroma", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    
    # RAG Configuration
    rag_enabled: bool = Field(default=True, env="RAG_ENABLED")
    rag_chunk_size: int = Field(default=500, env="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=50, env="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_min_similarity: float = Field(default=0.7, env="RAG_MIN_SIMILARITY")
    # Valores por defecto para búsquedas globales (chat/webhook)
    rag_global_min_similarity: float = Field(default=0.3, env="RAG_GLOBAL_MIN_SIMILARITY")
    rag_chat_top_k: int = Field(default=5, env="RAG_CHAT_TOP_K")
    
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

    @validator("whatsapp_api_url", always=True)
    def set_whatsapp_api_url(cls, v, values):
        """Genera la URL de WhatsApp API automáticamente usando phone_number_id."""
        if v is None and "phone_number_id" in values:
            return f"https://graph.facebook.com/v18.0/{values['phone_number_id']}/messages"
        return v
    
    # Pydantic v2 Settings configuration
    model_config = SettingsConfigDict(
        env_file=("/app/.env", "../../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Instancia global de configuración
settings = Settings()
