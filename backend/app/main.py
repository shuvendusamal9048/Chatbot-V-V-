from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.router import api_router
from app.core.config import settings

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.CORS_ORIGINS == ["*"] else settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
