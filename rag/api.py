import argparse
import os

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from rag.vector_store import (
    CLIENT_LOCK,
    close_shared_client,
    get_shared_client,
    retrieve_context,
    search_documents,
    upsert_document
)


app = FastAPI()
SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")


class DocumentIngestRequest(BaseModel):
    source: str
    text: str
    chunk_size: int = 700
    chunk_overlap: int = 120


@app.post("/documents")
def ingest_document(request: DocumentIngestRequest):
    with CLIENT_LOCK:
        client = get_shared_client()
        result = upsert_document(
            source=request.source,
            text=request.text,
            chunk_size=request.chunk_size,
            overlap=request.chunk_overlap,
            client=client
        )

    return {
        "success": True,
        **result
    }


@app.get("/retrieve")
def retrieve(query: str, top_k: int = 3):
    with CLIENT_LOCK:
        client = get_shared_client()
        context = retrieve_context(query, top_k=top_k, client=client)

    return {
        "query": query,
        "context": context
    }


@app.get("/search")
def search(query: str, top_k: int = 3):
    with CLIENT_LOCK:
        client = get_shared_client()
        matches = search_documents(query, top_k=top_k, client=client)

    return {
        "query": query,
        "matches": matches
    }


@app.get("/health")
def health_check():
    return {
        "status": "rag service alive"
    }


@app.on_event("startup")
def startup():
    with CLIENT_LOCK:
        get_shared_client()


@app.on_event("shutdown")
def shutdown():
    close_shared_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7000)
    args = parser.parse_args()

    uvicorn.run(app, host=SERVICE_HOST, port=args.port)
