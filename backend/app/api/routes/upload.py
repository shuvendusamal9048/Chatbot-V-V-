import json
import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.loaders import extract_text
from app.services.rag import create_vector_db

router = APIRouter()


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    allowed = [".pdf", ".txt", ".docx"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, "Unsupported File Type")

    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(file_path)
    create_vector_db(text, file.filename)

    meta_file = "metadata.json"
    docs = []
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            docs = json.load(f)

    if file.filename not in docs:
        docs.append(file.filename)

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(docs, f)

    return {"message": "Uploaded Successfully"}
