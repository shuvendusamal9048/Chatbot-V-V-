import os
from typing import List


class Settings:
    APP_NAME = "Bihar Chatbot"
    APP_ENV = os.getenv("APP_ENV", "development")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "faiss_db")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() in ("true", "1", "t")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


settings = Settings()
