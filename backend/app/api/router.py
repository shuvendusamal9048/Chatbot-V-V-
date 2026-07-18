from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.stt import router as stt_router
from app.api.routes.upload import router as upload_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(stt_router, tags=["stt"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(chat_router, tags=["chat"])
