import os
import aiohttp
import traceback


async def get_sarvam_tts(text: str, lang_code: str):
    """Return base64 WAV audio from Sarvam AI using a valid speaker list."""
    if not text or not text.strip():
        return None

    sarvam_key = os.getenv("SARVAM_API_KEY", "")
    if not sarvam_key:
        print("SARVAM_API_KEY not set, skipping TTS")
        return None

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": sarvam_key,
        "Content-Type": "application/json",
    }

    speakers = ["manisha", "vidya", "arya", "karun", "hitesh", "abhilash", "anushka"]

    for speaker in speakers:
        payload = {
            "text": text,
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": "bulbul:v2",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        audios = data.get("audios", [])
                        if audios:
                            print(f"[TTS] Got audio for: {text[:40]}... with speaker {speaker}")
                            return audios[0]
                    else:
                        err = await response.text()
                        print(f"[TTS] Failed {response.status} with speaker {speaker}: {err}")
        except Exception:
            print("[TTS] Exception:")
            traceback.print_exc()

    return None
