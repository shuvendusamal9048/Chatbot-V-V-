import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

VECTOR_PATH = "faiss_db"

# Lazy-loaded at first use, not at import time
embeddings = None
vector_db = None


def get_embeddings():
    """Lazy load embeddings model on first access to reduce startup memory."""
    global embeddings
    if embeddings is None:
        print("[RAG] Loading Embedding Model...")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        print("[RAG] Embedding Model Loaded")
    return embeddings


def create_vector_db(text, source="Unknown"):
    """
    Create/update vector database with batched embedding to avoid memory spikes during upload.
    Processes chunks in batches of 50 to prevent OOM errors on Render Free Plan (512 MB).
    """
    global vector_db

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)

    print(f"\n[RAG] Total Chunks to Index: {len(chunks)}")

    emb = get_embeddings()  # Lazy load embeddings
    
    # Batch size: process 50 chunks at a time to avoid memory spike
    BATCH_SIZE = 50
    
    if not os.path.exists(VECTOR_PATH):
        print("[RAG] Creating New FAISS DB (batch mode)...")
        vector_db = None
        
        # Process first batch to initialize FAISS
        first_batch = chunks[:BATCH_SIZE]
        first_batch_meta = [{"source": source} for _ in first_batch]
        vector_db = FAISS.from_texts(first_batch, emb, metadatas=first_batch_meta)
        print(f"[RAG] Batch 1/{(len(chunks)-1)//BATCH_SIZE + 1}: Created FAISS with {len(first_batch)} chunks")
        
        # Process remaining batches
        for i in range(BATCH_SIZE, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_meta = [{"source": source} for _ in batch]
            vector_db.add_texts(batch, metadatas=batch_meta)
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(chunks)-1) // BATCH_SIZE + 1
            print(f"[RAG] Batch {batch_num}/{total_batches}: Added {len(batch)} chunks")
    else:
        print("[RAG] Loading Existing FAISS (batch mode)...")
        vector_db = FAISS.load_local(VECTOR_PATH, emb, allow_dangerous_deserialization=True)
        print(f"[RAG] Loaded existing FAISS, now adding {len(chunks)} new chunks in batches...")
        
        # Add chunks in batches to existing FAISS
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_meta = [{"source": source} for _ in batch]
            vector_db.add_texts(batch, metadatas=batch_meta)
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(chunks)-1) // BATCH_SIZE + 1
            print(f"[RAG] Batch {batch_num}/{total_batches}: Added {len(batch)} chunks to existing DB")

    vector_db.save_local(VECTOR_PATH)
    print("[RAG] Embeddings Saved Successfully")


def load_vector_db():
    global vector_db

    if os.path.exists(VECTOR_PATH):
        print("\n[RAG] Loading Existing Embeddings...")
        emb = get_embeddings()  # Lazy load embeddings
        vector_db = FAISS.load_local(VECTOR_PATH, emb, allow_dangerous_deserialization=True)
        print("[RAG] Embeddings Loaded Successfully")
    else:
        print("[RAG] No Existing Embeddings")


def get_db():
    global vector_db
    if vector_db is None:
        load_vector_db()
    return vector_db


def retrieve(question):
    global vector_db

    if vector_db is None:
        load_vector_db()  # Lazy load on first use

    if vector_db is None:
        print("[RAG] No DB Loaded")
        return None, []

    docs = vector_db.similarity_search_with_score(question, k=4)
    context_list = []
    sources = []

    print("\nRetrieved Docs:\n")

    for i, (doc, score) in enumerate(docs):
        print("=" * 70)
        print("Doc:", i + 1)
        print("Score:", score)
        print("Metadata:", doc.metadata)
        print(doc.page_content[:400])
        print("=" * 70)

        context_list.append(doc.page_content)
        src = doc.metadata.get("source", "Unknown")
        if src not in sources:
            sources.append(src)

    if len(context_list) == 0:
        print("No Relevant Documents Found")
        return None, []

    context = "\n".join(context_list)
    return context, sources
