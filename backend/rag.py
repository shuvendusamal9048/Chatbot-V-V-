import os

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from langchain_community.vectorstores import (
    FAISS
)

from langchain_community.embeddings import (
    HuggingFaceEmbeddings
)

VECTOR_PATH = "backend/faiss_db"

print("Loading Embedding Model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("Embedding Model Loaded Successfully")


def create_vector_db(text):

    print("\n========== EMBEDDING START ==========")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(text)

    print(f"Total Chunks Generated : {len(chunks)}")

    for i, chunk in enumerate(chunks):

        print(f"\n----- Chunk {i+1} -----")
        print(chunk[:500])

    if os.path.exists(VECTOR_PATH):

        print("Existing FAISS DB Found")

        db = FAISS.load_local(
            VECTOR_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        db.add_texts(chunks)

    else:

        print("Creating New FAISS DB")

        db = FAISS.from_texts(
            chunks,
            embeddings
        )

    db.save_local(VECTOR_PATH)

    print("FAISS Saved Successfully")
    print("========== EMBEDDING END ==========\n")


def get_db():

    print("\nLoading FAISS Database...")

    if not os.path.exists(VECTOR_PATH):

        print("FAISS DB NOT FOUND")

        return None

    print("FAISS DB Loaded")

    return FAISS.load_local(
        VECTOR_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )


def retrieve(question):

    print("\n===================================")
    print("Question:")
    print(question)
    print("===================================")

    db = get_db()

    if db is None:
        return None

    docs = db.similarity_search_with_score(
        question,
        k=3
    )

    print("\nRetrieved Documents:\n")

    for i, (doc, score) in enumerate(docs):

        print(f"\nDocument {i+1}")

        print("Similarity Score :", score)

        print(doc.page_content[:500])

    if len(docs) == 0:

        print("NO DOCUMENTS FOUND")

        return None

    context = "\n".join(
        [
            doc.page_content
            for doc, score in docs
        ]
    )

    print("\n=========== CONTEXT ===========")

    print(context[:1000])

    print("================================\n")

    return context