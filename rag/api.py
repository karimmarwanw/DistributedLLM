import argparse

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from rag.vector_store import retrieve_context, search_documents, upsert_document


app = FastAPI()


class DocumentIngestRequest(BaseModel):
    source: str
    text: str
    chunk_size: int = 700
    chunk_overlap: int = 120


@app.post("/documents")
def ingest_document(request: DocumentIngestRequest):
    result = upsert_document(
        source=request.source,
        text=request.text,
        chunk_size=request.chunk_size,
        overlap=request.chunk_overlap
    )

    return {
        "success": True,
        **result
    }


@app.get("/retrieve")
def retrieve(query: str, top_k: int = 3):
    return {
        "query": query,
        "context": retrieve_context(query, top_k=top_k)
    }


@app.get("/search")
def search(query: str, top_k: int = 3):
    return {
        "query": query,
        "matches": search_documents(query, top_k=top_k)
    }


@app.get("/health")
def health_check():
    return {
        "status": "rag service alive"
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7000)
    args = parser.parse_args()

    uvicorn.run(app, host="127.0.0.1", port=args.port)
