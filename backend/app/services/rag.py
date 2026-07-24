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
    global vector_db

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)

    print(f"\nTotal Chunks : {len(chunks)}")

    metadatas = [{"source": source} for _ in chunks]

    emb = get_embeddings()  # Lazy load embeddings
    if not os.path.exists(VECTOR_PATH):
        print("Creating New FAISS DB...")
        vector_db = FAISS.from_texts(chunks, emb, metadatas=metadatas)
    else:
        print("Loading Existing FAISS...")
        vector_db = FAISS.load_local(VECTOR_PATH, emb, allow_dangerous_deserialization=True)
        vector_db.add_texts(chunks, metadatas=metadatas)

    vector_db.save_local(VECTOR_PATH)
    print("Embeddings Saved Successfully")


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
