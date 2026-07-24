import json
import os
import shutil
import gc

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

    # Limit file size to 20 MB to prevent OOM on Render (512 MB plan)
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"

    # Read file and check size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            413, 
            f"File too large. Maximum size is 20 MB. Your file is {len(file_content) / (1024*1024):.1f} MB"
        )
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    print(f"[UPLOAD] Extracting text from {file.filename} ({len(file_content) / 1024:.1f} KB)...")
    text = extract_text(file_path)
    print(f"[UPLOAD] Extracted {len(text)} characters, creating vector DB...")
    
    create_vector_db(text, file.filename)
    
    # Force garbage collection to free up memory after vector creation
    del text, file_content
    gc.collect()
    print(f"[UPLOAD] Completed indexing {file.filename}")

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
