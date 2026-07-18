from fastapi import APIRouter, File, UploadFile

from app.services.stt_service import transcribe_audio

router = APIRouter()


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    return await transcribe_audio(file)
