import asyncio
import base64
import json
import aiohttp
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.rag import retrieve
import importlib
try:
    _lang_module = importlib.import_module("backend.services.language")
except ModuleNotFoundError:
    _lang_module = importlib.import_module("services.language")
detect_language = _lang_module.detect_language

router = APIRouter()
PUNCTUATION = {".", "?", "!", "\n", "।", "॥", ";"}
ABBREVIATIONS = (
    "pvt.", "ltd.", "mr.", "mrs.", "dr.", "inc.", "co.", "corp.", "approx.", "vs.",
    "pvt", "ltd", "mr", "mrs", "dr", "inc", "co"
)
STT_WS_URL = "wss://api.sarvam.ai/speech-to-text/ws?model=saaras:v3"
TTS_WS_URL = "wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v3&send_completion_event=true"


def get_chat_model():
    if settings.LLM_PROVIDER == "gemini":
        print(f"[CHAT] using Gemini provider with model={settings.GEMINI_MODEL}")
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0
        )
    print(f"[CHAT] using Ollama provider with model={settings.OLLAMA_MODEL}")
    return ChatOllama(model=settings.OLLAMA_MODEL, temperature=0)


def sarvam_headers():
    return {"api-subscription-key": settings.SARVAM_API_KEY}


async def translate_text(session: aiohttp.ClientSession, text: str, target_lang: str) -> str:
    """Translate English text to target Indian language using Sarvam Translate API."""
    if not text or not text.strip():
        return text
    
    # Normalize target language code if needed (Translate API expects od-IN for Odia)
    normalized_target = "od-IN" if target_lang in {"or-IN", "od-IN"} else target_lang
    
    # If target is English, no translation needed
    if normalized_target == "en-IN":
        return text

    sarvam_key = settings.SARVAM_API_KEY
    if not sarvam_key:
        return text

    url = "https://api.sarvam.ai/translate"
    headers = {
        "api-subscription-key": sarvam_key,
        "Content-Type": "application/json",
    }
    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": normalized_target,
        "model": "sarvam-translate:v1",
    }

    try:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                translated_text = data.get("translated_text")
                if translated_text:
                    print(f"[TRANSLATE] Translated '{text[:30]}' to '{translated_text[:30]}'")
                    return translated_text
            else:
                err = await response.text()
                print(f"[TRANSLATE] Failed with status {response.status}: {err}")
    except Exception as e:
        print(f"[TRANSLATE] Exception: {e}")
        
    return text


async def translate_query_to_english(session: aiohttp.ClientSession, text: str, source_lang: str) -> str:
    """Translate Indian language query to English using Sarvam Translate API."""
    if not text or not text.strip():
        return text

    # Normalize source language code if needed (Translate API expects od-IN for Odia)
    normalized_source = "od-IN" if source_lang in {"or-IN", "od-IN"} else source_lang
    sarvam_key = settings.SARVAM_API_KEY
    if not sarvam_key:
        return text

    url = "https://api.sarvam.ai/translate"
    headers = {
        "api-subscription-key": sarvam_key,
        "Content-Type": "application/json",
    }
    payload = {
        "input": text,
        "source_language_code": normalized_source,
        "target_language_code": "en-IN",
        "model": "sarvam-translate:v1",
    }

    try:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                translated_text = data.get("translated_text")
                if translated_text:
                    print(f"[TRANSLATE QUERY] Translated '{text[:30]}' to '{translated_text[:30]}'")
                    return translated_text
    except Exception as e:
        print(f"[TRANSLATE QUERY] Exception: {e}")
        
    return text


async def stt_ws_receive_loop(stt_ws: aiohttp.ClientWebSocketResponse, client_ws: WebSocket, transcripts: list) -> None:
    """Read transcript messages from Sarvam STT WebSocket in real time, 
    and stream them as partial transcripts to the client UI."""
    try:
        async for msg in stt_ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                
                print(f"[STT WS received] {payload}")
                if payload.get("type") == "data":
                    transcript = payload.get("data", {}).get("transcript", "")
                    if transcript:
                        transcripts.append(transcript)
                        # Forward partial transcript to UI
                        await client_ws.send_text(json.dumps({
                            "type": "transcript_partial",
                            "transcript": transcript
                        }))
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(f"[CHAT] stt_ws_receive_loop error: {exc}")


async def receive_user_input(client_ws: WebSocket, http_session: aiohttp.ClientSession) -> str:
    """Wait for client input. If user streams binary PCM frames, dynamically open 
    Sarvam's STT WebSocket, forward frames, and return final transcript when speech ends."""
    stt_ws = None
    stt_receive_task = None
    transcripts = []
    is_first_chunk = True

    def create_wav_header(sample_rate: int = 16000, num_channels: int = 1, bits_per_sample: int = 16) -> bytes:
        header = bytearray(44)
        header[0:4] = b'RIFF'
        header[4:8] = (0x7FFFFFFF).to_bytes(4, byteorder='little')
        header[8:12] = b'WAVE'
        header[12:16] = b'fmt '
        header[16:20] = (16).to_bytes(4, byteorder='little')
        header[20:22] = (1).to_bytes(2, byteorder='little')
        header[22:24] = (num_channels).to_bytes(2, byteorder='little')
        header[24:28] = (sample_rate).to_bytes(4, byteorder='little')
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        header[28:32] = (byte_rate).to_bytes(4, byteorder='little')
        block_align = num_channels * (bits_per_sample // 8)
        header[32:34] = (block_align).to_bytes(2, byteorder='little')
        header[34:36] = (bits_per_sample).to_bytes(2, byteorder='little')
        header[36:40] = b'data'
        header[40:44] = (0x7FFFFFFF).to_bytes(4, byteorder='little')
        return bytes(header)

    try:
        while True:
            message = await client_ws.receive()
            
            if message["type"] == "websocket.disconnect":
                print("[CHAT] client disconnected while waiting for input")
                raise WebSocketDisconnect()

            # Binary audio PCM frame
            if message.get("bytes"):
                audio_bytes = message["bytes"]
                
                if stt_ws is None:
                    print("[CHAT] Connecting to Sarvam STT WebSocket...")
                    stt_url = "wss://api.sarvam.ai/speech-to-text/ws?model=saaras:v3&language-code=unknown"
                    try:
                        stt_ws = await http_session.ws_connect(stt_url, headers=sarvam_headers())
                        transcripts = []
                        stt_receive_task = asyncio.create_task(
                            stt_ws_receive_loop(stt_ws, client_ws, transcripts)
                        )
                        is_first_chunk = True
                    except Exception as e:
                        print(f"[CHAT] Failed to connect to Sarvam STT WS: {e}")
                        await client_ws.send_text(json.dumps({"type": "debug", "message": f"[DEBUG] STT WS connection failed: {e}"}))
                        continue

                if stt_ws and not stt_ws.closed:
                    if is_first_chunk:
                        payload_bytes = create_wav_header() + audio_bytes
                        is_first_chunk = False
                    else:
                        payload_bytes = audio_bytes
                        
                    audio_b64 = base64.b64encode(payload_bytes).decode("utf-8")
                    payload = {
                        "audio": {
                            "data": audio_b64,
                            "sample_rate": "16000",
                            "encoding": "audio/wav"
                        }
                    }
                    try:
                        await stt_ws.send_json(payload)
                    except Exception as e:
                        print(f"[CHAT] Failed to send audio payload to Sarvam STT WS: {e}")
                continue

            # Text frame
            if message.get("text") is not None:
                text = message["text"].strip()
                if not text:
                    continue

                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    return text

                event_type = payload.get("type")
                
                # Speech end triggered by button or client VAD
                if event_type in {"speech_end", "audio_end"}:
                    print("[CHAT] Speech end event received. Completing transcription...")
                    await client_ws.send_text(json.dumps({"type": "debug", "message": "[DEBUG] Speech ended, finalizing transcript..."}))
                    
                    # Brief wait for trailing transcription frames
                    await asyncio.sleep(0.5)
                    
                    # Gracefully close STT WS
                    if stt_ws:
                        await stt_ws.close()
                    if stt_receive_task:
                        stt_receive_task.cancel()
                        await asyncio.gather(stt_receive_task, return_exceptions=True)

                    final_transcript = transcripts[-1] if transcripts else ""
                    print(f"[CHAT] Completed streaming transcription: '{final_transcript}'")
                    return final_transcript

                if event_type == "text":
                    return payload.get("text", "")

    finally:
        if stt_ws:
            await stt_ws.close()
        if stt_receive_task:
            stt_receive_task.cancel()


async def tts_receive_loop(tts_ws_container: list, client_ws: WebSocket, progress: dict) -> None:
    """Read generated audio chunks from Sarvam TTS WebSocket in real time, 
    accumulate them per sentence, and stream the compiled binary MP3 payload 
    to the client when the 'final' event arrives."""
    accumulated_audio = bytearray()
    try:
        while True:
            tts_ws = tts_ws_container[0]
            if tts_ws is None or tts_ws.closed:
                await asyncio.sleep(0.05)
                continue

            try:
                msg = await tts_ws.receive(timeout=0.1)
            except asyncio.TimeoutError:
                continue

            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                msg_type = payload.get("type")
                if msg_type == "audio":
                    data = payload.get("data") or {}
                    audio_b64 = data.get("audio")
                    if audio_b64:
                        try:
                            accumulated_audio.extend(base64.b64decode(audio_b64))
                        except Exception:
                            pass
                elif msg_type == "event":
                    data = payload.get("data") or {}
                    ev = data.get("event_type") or data.get("event") or payload.get("event")
                    if ev in {"completion", "final"}:
                        if accumulated_audio:
                            await safe_send_bytes(client_ws, bytes(accumulated_audio))
                            accumulated_audio.clear()
                        progress["completed"] += 1
                        if progress["all_sent"] and progress["completed"] >= progress["sent"]:
                            progress["turn_event"].set()
                elif msg_type == "error":
                    err_msg = payload.get("data", {}).get("message") or payload.get("message")
                    print(f"[CHAT] TTS WebSocket returned error: {err_msg}")
                    if "closed" in str(err_msg).lower():
                        tts_ws_container[0] = None
            elif msg.type == aiohttp.WSMsgType.BINARY:
                accumulated_audio.extend(msg.data)
            elif msg.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                print(f"[CHAT] TTS WebSocket closed/error. Attempting to reconnect...")
                tts_ws_container[0] = None
                try:
                    headers = {"api-subscription-key": settings.SARVAM_API_KEY}
                    tts_ws_container[0] = await tts_ws.session.ws_connect(TTS_WS_URL, headers=headers)
                    print("[CHAT] TTS WebSocket reconnected successfully.")
                except Exception as rec_err:
                    print(f"[CHAT] TTS Reconnection failed: {rec_err}")
                    await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(f"[CHAT] tts_receive_loop failed: {exc}")
    finally:
        if accumulated_audio:
            try:
                await safe_send_bytes(client_ws, bytes(accumulated_audio))
            except Exception:
                pass


async def synthesize_one_sentence_audio(session: aiohttp.ClientSession, client_ws: WebSocket, text: str, lang_code: str) -> None:
    """Helper to synthesize a single sentence (like a fallback answer) using a short-lived WS connection."""
    try:
        normalized_lang = "od-IN" if lang_code in {"or-IN", "od-IN"} else lang_code
        async with session.ws_connect(TTS_WS_URL, headers=sarvam_headers()) as tts_ws:
            config_payload = {
                "type": "config",
                "data": {
                    "target_language_code": normalized_lang,
                    "speaker": "ritu",
                    "output_audio_codec": "mp3"
                }
            }
            await tts_ws.send_json(config_payload)
            await tts_ws.send_json({"type": "text", "data": {"text": text}})
            await tts_ws.send_json({"type": "flush"})
            
            accumulated_audio = bytearray()
            async for msg in tts_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    msg_type = payload.get("type")
                    if msg_type == "audio":
                        data = payload.get("data") or {}
                        audio_b64 = data.get("audio")
                        if audio_b64:
                            accumulated_audio.extend(base64.b64decode(audio_b64))
                    elif msg_type == "event":
                        data = payload.get("data") or {}
                        ev = data.get("event_type") or data.get("event") or payload.get("event")
                        if ev in {"completion", "final"}:
                            break
                    elif msg_type == "error":
                        break
            if accumulated_audio:
                await safe_send_bytes(client_ws, bytes(accumulated_audio))
    except Exception as exc:
        print(f"[CHAT] synthesize_one_sentence_audio failed: {exc}")


async def translator_worker(
    translation_queue: asyncio.Queue,
    tts_queue: asyncio.Queue,
    http_session: aiohttp.ClientSession,
    client_ws: WebSocket,
    lang_code: str
) -> None:
    """Read English sentences, translate them sequentially, send the text chunk to the client, 
    and push the speakable translated text to the TTS queue."""
    try:
        while True:
            sentence = await translation_queue.get()
            if sentence is None:
                await tts_queue.put(None)
                translation_queue.task_done()
                break

            try:
                if settings.LLM_PROVIDER == "gemini":
                    # Bypass translation since Gemini outputs natively in the target script
                    await send_text_chunk(client_ws, sentence + " ")
                    if any(c.isalnum() for c in sentence):
                        await tts_queue.put(sentence)
                else:
                    await client_ws.send_text(json.dumps({"type": "debug", "message": f"[DEBUG] Translating sentence: {sentence[:30]}..."}))
                    translated = await translate_text(http_session, sentence, lang_code)
                    await send_text_chunk(client_ws, translated + " ")
                    if any(c.isalnum() for c in translated):
                        await tts_queue.put(translated)
            except Exception as e:
                print(f"[CHAT] translator_worker error for sentence: {e}")
            finally:
                translation_queue.task_done()
    except Exception as exc:
        print(f"[CHAT] translator_worker failed: {exc}")


async def tts_synthesizer_worker(
    tts_queue: asyncio.Queue,
    tts_ws_container: list,
    progress: dict
) -> None:
    """Read translated sentences sequentially and stream text and flush commands 
    over the single persistent TTS WebSocket connection."""
    try:
        while True:
            translated = await tts_queue.get()
            if translated is None:
                tts_queue.task_done()
                break

            try:
                tts_ws = tts_ws_container[0]
                if tts_ws is None or tts_ws.closed:
                    print("[CHAT] tts_synthesizer_worker waiting for warm TTS WS...")
                    while tts_ws is None or tts_ws.closed:
                        await asyncio.sleep(0.05)
                        tts_ws = tts_ws_container[0]
                await tts_ws.send_json({"type": "text", "data": {"text": translated}})
                await tts_ws.send_json({"type": "flush"})
                progress["sent"] += 1
            except Exception as e:
                print(f"[CHAT] tts_synthesizer_worker error for sentence: {e}")
            finally:
                tts_queue.task_done()
        progress["all_sent"] = True
    except Exception as exc:
        print(f"[CHAT] tts_synthesizer_worker failed: {exc}")


async def cancel_tasks(*tasks):
    for task in tasks:
        if task and not task.done():
            task.cancel()
    await asyncio.gather(*(task for task in tasks if task), return_exceptions=True)


async def safe_send_text(ws: WebSocket, payload: dict) -> bool:
    try:
        await ws.send_text(json.dumps(payload))
        return True
    except Exception as exc:
        print(f"[CHAT] failed to send_text {payload.get('type')} - {type(exc).__name__}: {exc}")
        return False


async def safe_send_bytes(ws: WebSocket, data: bytes) -> bool:
    try:
        await ws.send_bytes(data)
        return True
    except Exception as exc:
        print(f"[CHAT] failed to send_bytes - {type(exc).__name__}: {exc}")
        return False


async def send_text_chunk(ws: WebSocket, content: str) -> bool:
    return await safe_send_text(ws, {"type": "chunk", "content": content})


@router.websocket("/chat")
async def chat(ws: WebSocket):
    await ws.accept()
    print("[CHAT] websocket connection accepted")
    await ws.send_text(json.dumps({"type": "debug", "message": "WebSocket connected, waiting for input."}))

    if not settings.SARVAM_API_KEY:
        print("[CHAT] missing SARVAM_API_KEY")
        await ws.close(code=1008)
        return

    async with aiohttp.ClientSession() as http_session:
        tts_ws_container = [None]
        
        async def pre_warm_tts():
            try:
                print("[CHAT] Warming global TTS WebSocket connection...")
                tts_ws = await http_session.ws_connect(TTS_WS_URL, headers=sarvam_headers())
                tts_ws_container[0] = tts_ws
                print("[CHAT] Global TTS WebSocket warmed successfully.")
            except Exception as e:
                print(f"[CHAT] Failed to pre-warm global TTS WebSocket: {e}")

        asyncio.create_task(pre_warm_tts())
        
        # Shared progress tracker to coordinate TTS sending and receiving
        progress = {"sent": 0, "completed": 0, "all_sent": False, "turn_event": asyncio.Event()}
        
        # Start background audio reader for the persistent WS connection lifecycle
        tts_reader = asyncio.create_task(tts_receive_loop(tts_ws_container, ws, progress))

        try:
            while True:
                try:
                    user_query = await receive_user_input(ws, http_session)
                except WebSocketDisconnect:
                    print("[CHAT] websocket disconnected while waiting for input")
                    break

                if not user_query:
                    print("[CHAT] no user query received, closing websocket")
                    await ws.close(code=1000)
                    break

                print(f"[CHAT] received user query: {user_query}")
                # Notify frontend of transcribed query to render user text bubble
                await ws.send_text(json.dumps({"type": "user_query", "text": user_query}))
                await ws.send_text(json.dumps({"type": "debug", "message": "Received user input, generating response..."}))
                
                lang_code = detect_language(user_query)
                await ws.send_text(json.dumps({"type": "debug", "message": f"[DEBUG] Detected query language: {lang_code}"}))

                # Translate non-English query to English for better RAG retrieval
                english_query = user_query
                if lang_code != "en-IN":
                    await ws.send_text(json.dumps({"type": "debug", "message": "[DEBUG] Translating query to English..."}))
                    english_query = await translate_query_to_english(http_session, user_query, lang_code)
                    await ws.send_text(json.dumps({"type": "debug", "message": f"[DEBUG] Translated query: {english_query}"}))

                context, sources = retrieve(english_query)
                await ws.send_text(json.dumps({"type": "start"}))

                if context is None:
                    context = "No document context available."

                # Prompt the LLM
                if settings.LLM_PROVIDER == "gemini":
                    if lang_code == "hi-IN":
                        target_lang_name = "Hindi (using Devanagari script)"
                    elif lang_code in {"or-IN", "od-IN"}:
                        target_lang_name = "Odia (using Odia script)"
                    else:
                        target_lang_name = "English"

                    sys_instruction = (
                        f"You are a helpful human assistant. Answer the user's query using the context below. "
                        f"If the answer is present in the context, prioritize using it. If the context does not contain the answer, "
                        f"use your own general knowledge to provide a helpful, correct response. "
                        f"Reason and analyze the query in English step-by-step internally, "
                        f"but output ONLY the final answer, writing it directly in {target_lang_name}."
                        f"Respond in a warm, natural, human-like voice. Keep your answers complete, direct, and very concise (aim for 2-3 short sentences max) so that they are suitable for speech synthesis."
                    )
                else:
                    sys_instruction = (
                        "You are a helpful human assistant. Answer the user's query using the context below. "
                        "If the answer is present in the context, prioritize using it. If the context does not contain the answer, "
                        "use your own general knowledge to provide a helpful, correct response. "
                        "Respond in a warm, natural, human-like voice. Keep your answers complete, direct, and very concise (aim for 2-3 short sentences max) so that they are suitable for speech synthesis. "
                        "You MUST respond in English."
                    )

                prompt = (
                    f"{sys_instruction}\n\n"
                    f"Context:\n{context}\n\n"
                    f"User Query: {english_query}\n"
                    "Answer:"
                )

                # Persistent TTS WebSocket execution turn
                try:
                    # Reset turn statistics
                    progress["turn_event"].clear()
                    progress["sent"] = 0
                    progress["completed"] = 0
                    progress["all_sent"] = False

                    tts_ws = tts_ws_container[0]
                    if tts_ws is None or tts_ws.closed:
                        print("[CHAT] Warm TTS WS not ready, connecting inline...")
                        tts_ws = await http_session.ws_connect(TTS_WS_URL, headers=sarvam_headers())
                        tts_ws_container[0] = tts_ws

                    # Send configuration payload once
                    normalized_lang = "od-IN" if lang_code in {"or-IN", "od-IN"} else lang_code
                    config_payload = {
                        "type": "config",
                        "data": {
                            "target_language_code": normalized_lang,
                            "speaker": "ritu",
                            "output_audio_codec": "mp3"
                        }
                    }
                    await tts_ws.send_json(config_payload)
                    await ws.send_text(json.dumps({"type": "debug", "message": "[DEBUG] Warm TTS WS config sent."}))

                    translation_queue = asyncio.Queue()
                    tts_queue = asyncio.Queue()

                    # Start the background translator and synthesizer workers
                    translator_task = asyncio.create_task(
                        translator_worker(translation_queue, tts_queue, http_session, ws, lang_code)
                    )
                    tts_task = asyncio.create_task(
                        tts_synthesizer_worker(tts_queue, tts_ws_container, progress)
                    )

                    buffer = ""
                    llm = get_chat_model()

                    # Stream response from LLM, split to sentences/clauses, and push to translation queue
                    PUNCTUATION_AND_CLAUSE = {".", "?", "!", "\n", "।", "॥", ";", ",", "—"}
                    async for chunk in llm.astream(prompt):
                        content = getattr(chunk, "content", None)
                        if not content:
                            continue
                        buffer += content

                        while True:
                            # 1. Find earliest punctuation or clause marker
                            earliest_idx = -1
                            for marker in PUNCTUATION_AND_CLAUSE:
                                idx = buffer.find(marker)
                                if idx != -1:
                                    if earliest_idx == -1 or idx < earliest_idx:
                                        earliest_idx = idx

                            if earliest_idx != -1:
                                sentence = buffer[: earliest_idx + 1].strip()
                                # Check if it's a common abbreviation to prevent split
                                if sentence.lower().endswith(ABBREVIATIONS):
                                    break  # Don't split here, wait for more text
                                
                                buffer = buffer[earliest_idx + 1 :]
                                if sentence:
                                    await translation_queue.put(sentence)
                                continue

                            # 2. If no punctuation, split at 5 words threshold
                            words = buffer.split()
                            if len(words) >= 5:
                                prefix_words = words[:5]
                                pos = 0
                                for word in prefix_words:
                                    pos = buffer.find(word, pos) + len(word)
                                sentence = buffer[:pos].strip()
                                buffer = buffer[pos:]
                                if sentence:
                                    await translation_queue.put(sentence)
                                continue
                            break

                    # Send any remaining buffer
                    final_text = buffer.strip()
                    if final_text:
                        await translation_queue.put(final_text)

                    # Signal the end of translation queue
                    await translation_queue.put(None)

                    # Wait for the background workers to complete their pipelined execution
                    await asyncio.gather(translator_task, tts_task, return_exceptions=True)

                    # Wait for the reader to naturally finish receiving all pending audio
                    try:
                        if progress["sent"] > 0 and progress["completed"] < progress["sent"]:
                            await asyncio.wait_for(progress["turn_event"].wait(), timeout=10.0)
                    except asyncio.TimeoutError:
                        print("[CHAT] turn timeout waiting for audio completion")

                except Exception as tts_exc:
                    print(f"[CHAT] TTS WebSocket failure: {tts_exc}")
                    await ws.send_text(json.dumps({"type": "debug", "message": f"[DEBUG] TTS WebSocket failed: {tts_exc}"}))

                await ws.send_text(json.dumps({"type": "sources", "sources": sources, "language": lang_code}))
                await ws.send_text(json.dumps({"type": "end"}))
        finally:
            tts_reader.cancel()
            await asyncio.gather(tts_reader, return_exceptions=True)
            if tts_ws_container[0] and not tts_ws_container[0].closed:
                await tts_ws_container[0].close()
