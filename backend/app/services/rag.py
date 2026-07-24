import os
import gc

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
    Create/update vector database with EXTREME batching and garbage collection.
    Processes chunks in batches of 10 to prevent OOM on Render Free Plan (512 MB).
    Each batch cycle: embed 10 chunks (~2-5MB) -> add to DB -> release memory -> repeat.
    """
    global vector_db

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)

    print(f"\n[RAG] Total Chunks to Index: {len(chunks)}")

    # Clear the original text from memory immediately after splitting
    del text
    gc.collect()
    
    emb = get_embeddings()  # Lazy load embeddings
    
    # EXTREME: Batch size of 10 chunks (very conservative for 512MB Render limit)
    BATCH_SIZE = 10
    
    if not os.path.exists(VECTOR_PATH):
        print("[RAG] Creating New FAISS DB (extreme-batch mode, 10 chunks/batch)...")
        vector_db = None
        
        # Process first batch to initialize FAISS
        first_batch = chunks[:BATCH_SIZE]
        first_batch_meta = [{"source": source} for _ in first_batch]
        vector_db = FAISS.from_texts(first_batch, emb, metadatas=first_batch_meta)
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[RAG] Batch 1/{total_batches}: Created FAISS with {len(first_batch)} chunks")
        
        # Explicit garbage collection
        del first_batch, first_batch_meta
        gc.collect()
        
        # Process remaining batches
        for i in range(BATCH_SIZE, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_meta = [{"source": source} for _ in batch]
            vector_db.add_texts(batch, metadatas=batch_meta)
            batch_num = (i // BATCH_SIZE) + 1
            print(f"[RAG] Batch {batch_num}/{total_batches}: Added {len(batch)} chunks (~{len(batch)}KB text)")
            
            # Explicit garbage collection after each batch
            del batch, batch_meta
            gc.collect()
    else:
        print("[RAG] Loading Existing FAISS (extreme-batch mode, 10 chunks/batch)...")
        vector_db = FAISS.load_local(VECTOR_PATH, emb, allow_dangerous_deserialization=True)
        print(f"[RAG] Loaded existing FAISS, now adding {len(chunks)} new chunks in batches...")
        
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Add chunks in batches to existing FAISS
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_meta = [{"source": source} for _ in batch]
            vector_db.add_texts(batch, metadatas=batch_meta)
            batch_num = (i // BATCH_SIZE) + 1
            print(f"[RAG] Batch {batch_num}/{total_batches}: Added {len(batch)} chunks (~{len(batch)}KB text) to existing DB")
            
            # Explicit garbage collection after each batch
            del batch, batch_meta
            gc.collect()

    vector_db.save_local(VECTOR_PATH)
    print("[RAG] Embeddings Saved Successfully")
    
    # Final cleanup
    del chunks
    gc.collect()
    print("[RAG] Memory cleanup complete")


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
