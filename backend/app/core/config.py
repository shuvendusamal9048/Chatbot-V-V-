import os
from typing import List


class Settings:
    APP_NAME = "Bihar Chatbot"
    APP_ENV = os.getenv("APP_ENV", "development")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "faiss_db")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")


settings = Settings()
