import aiohttp
import os
import traceback
from fastapi import HTTPException, UploadFile


async def transcribe_audio(file: UploadFile):
    sarvam_key = os.getenv("SARVAM_API_KEY", "")
    if not sarvam_key:
        raise HTTPException(500, detail="SARVAM_API_KEY not configured")

    audio_bytes = await file.read()
    raw_mime = (file.content_type or "audio/webm").split(";")[0].strip()

    form_data = aiohttp.FormData()
    form_data.add_field("file", audio_bytes, filename="recording.webm", content_type=raw_mime)
    form_data.add_field("model", "saaras:v3")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.sarvam.ai/speech-to-text",
                data=form_data,
                headers={"api-subscription-key": sarvam_key},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    res_data = await response.json()
                    transcript = res_data.get("transcript", "")
                    return {"transcript": transcript}
                err = await response.text()
                raise HTTPException(500, detail=f"Sarvam STT failed: {err}")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))
