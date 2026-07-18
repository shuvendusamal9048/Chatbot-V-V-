import json
import os

from fastapi import APIRouter, HTTPException

from app.services.rag import get_db

router = APIRouter()


@router.get("/documents")
def documents():
    meta_file = "metadata.json"
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@router.get("/debug")
def debug():
    db = get_db()
    if db is None:
        return {"error": "No DB Loaded"}
    docs = db.similarity_search("candidate")
    return {"documents": [d.page_content for d in docs]}
