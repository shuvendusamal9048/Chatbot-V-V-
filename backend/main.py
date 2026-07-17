from fastapi import (
    FastAPI,
    UploadFile,
    File,
    WebSocket,
    HTTPException
)

from pydantic import BaseModel

from loaders import extract_text

from rag import (
    create_vector_db,
    retrieve,
    get_db
)

from langchain_ollama import (
    ChatOllama
)

import os
import shutil

app = FastAPI()

print("Connecting to Ollama...")

model = ChatOllama(
    model="llama3.2:latest",
    temperature=0
)

print("Ollama Connected")


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
async def startup():

    print("\n========== STARTUP ==========")

    if os.path.exists("faiss_db"):

        print("FAISS DATABASE FOUND")

    else:

        print("NO FAISS DATABASE")

    print("=============================\n")


@app.post("/upload")
async def upload(
        file: UploadFile = File(...)
):

    print("\nUploading File...")

    allowed = [
        ".txt",
        ".pdf",
        ".docx"
    ]

    ext = os.path.splitext(
        file.filename
    )[1].lower()

    if ext not in allowed:

        raise HTTPException(
            400,
            "Unsupported File"
        )

    os.makedirs(
        "uploads",
        exist_ok=True
    )

    file_path = (
        f"uploads/{file.filename}"
    )

    with open(
            file_path,
            "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    print("File Saved")

    text = extract_text(
        file_path
    )

    print("\n========== EXTRACTED TEXT ==========\n")

    print(text[:1000])

    print("\n====================================")

    print(
        "Text Length:",
        len(text)
    )

    create_vector_db(text)

    return {
        "message":
        "Uploaded Successfully"
    }


@app.get("/debug")
def debug():

    db = get_db()

    docs = db.similarity_search(
        "candidate"
    )

    return {
        "documents":
        [
            d.page_content
            for d in docs
        ]
    }


@app.post("/ask")
def ask(data: ChatRequest):

    print("\n================================")
    print("QUESTION :", data.question)
    print("================================")

    context = retrieve(
        data.question
    )

    if context is None:

        return {
            "answer":
            "I don't know"
        }

    prompt = f"""
You are a RAG assistant.

Answer ONLY from context.

If answer is not present,
reply exactly:

I don't know.

Context:
{context}

Question:
{data.question}
"""

    print("\n=========== PROMPT ===========\n")

    print(prompt[:2000])

    print("\n==============================")

    response = model.invoke(
        prompt
    )

    print("\n=========== LLM RESPONSE ==========\n")

    print(response.content)

    print("\n===================================\n")

    return {
        "answer":
        response.content
    }


@app.websocket("/chat")
async def chat(ws: WebSocket):

    await ws.accept()

    while True:

        question = await ws.receive_text()

        context = retrieve(question)

        if context is None:

            await ws.send_text(
                "I don't know"
            )

            await ws.send_text(
                "[END]"
            )

            continue

        prompt = f"""
Context:
{context}

Question:
{question}

Answer only from context.
"""

        for chunk in model.stream(
                prompt
        ):

            if chunk.content:

                await ws.send_text(
                    chunk.content
                )

        await ws.send_text(
            "[END]"
        )

@app.get("/health")
def health():

    return {
        "backend": "running",
        "ollama": "connected",
        "vector_db":
            os.path.exists(
                "faiss_db"
            )
    }

@app.websocket("/chat")
async def chat(ws: WebSocket):

    await ws.accept()

    while True:

        question = await ws.receive_text()

        context = retrieve(question)

        if context is None:

            await ws.send_text(
                "I don't know"
            )

            await ws.send_text(
                "[END]"
            )

            continue

        prompt = f"""
Answer only from context.

Context:
{context}

Question:
{question}
"""

        for chunk in model.stream(
                prompt
        ):

            if chunk.content:

                await ws.send_text(
                    chunk.content
                )

        await ws.send_text(
            "[END]"
        )