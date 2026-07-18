import json

from fastapi import APIRouter, WebSocket
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.services.tts_service import get_sarvam_tts
from app.services.rag import retrieve
from services.language import detect_language

router = APIRouter()

model = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0)


def extract_sentences(buffer: str):
    sentences = []
    current = ""
    i = 0
    while i < len(buffer):
        char = buffer[i]
        current += char
        if char in [".", "?", "!", "\u0964", "\n"]:
            if char == "." and i + 1 < len(buffer) and buffer[i + 1].isdigit():
                i += 1
                continue
            stripped = current.strip()
            if stripped:
                sentences.append(stripped)
            current = ""
        i += 1

    if len(current) > 200:
        last_space = current.rfind(" ")
        if last_space > 100:
            stripped = current[:last_space].strip()
            if stripped:
                sentences.append(stripped)
            current = current[last_space:].strip()

    return sentences, current


@router.websocket("/chat")
async def chat(ws: WebSocket):
    await ws.accept()
    print("WS Connected")

    while True:
        question = await ws.receive_text()
        lang = detect_language(question)

        context, sources = retrieve(question)

        if context is None:
            no_answer = "I don't know."
            await ws.send_text(json.dumps({"type": "chunk", "content": no_answer}))
            audio_b64 = await get_sarvam_tts(no_answer, lang)
            if audio_b64:
                await ws.send_text(json.dumps({"type": "audio", "audio": audio_b64}))
            await ws.send_text(json.dumps({"type": "sources", "sources": [], "language": lang}))
            await ws.send_text(json.dumps({"type": "end"}))
            continue

        prompt = f"""
You are a RAG assistant.
Answer ONLY from context.
If answer is not present,
reply exactly:

I don't know.

Context:
{context}

Question:
{question}
"""

        text_buffer = ""
        for chunk in model.stream(prompt):
            if chunk.content:
                await ws.send_text(json.dumps({"type": "chunk", "content": chunk.content}))
                text_buffer += chunk.content
                sentences, text_buffer = extract_sentences(text_buffer)
                for sentence in sentences:
                    audio_b64 = await get_sarvam_tts(sentence, lang)
                    if audio_b64:
                        await ws.send_text(json.dumps({"type": "audio", "audio": audio_b64}))

        if text_buffer.strip():
            audio_b64 = await get_sarvam_tts(text_buffer.strip(), lang)
            if audio_b64:
                await ws.send_text(json.dumps({"type": "audio", "audio": audio_b64}))

        await ws.send_text(json.dumps({"type": "sources", "sources": sources, "language": lang}))
        await ws.send_text(json.dumps({"type": "end"}))
