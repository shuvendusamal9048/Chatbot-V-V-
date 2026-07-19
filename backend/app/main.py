from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
print(f"[STARTUP] LLM_PROVIDER={settings.LLM_PROVIDER}, GEMINI_MODEL={settings.GEMINI_MODEL}, SARVAM_API_KEY_PRESENT={bool(settings.SARVAM_API_KEY)}")
