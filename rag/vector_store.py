import hashlib
import math
import os
import re
import uuid

from qdrant_client import QdrantClient, models


VECTOR_SIZE = int(os.getenv("RAG_VECTOR_SIZE", "384"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "distributed_llm_docs")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_data")
QDRANT_URL = os.getenv("QDRANT_URL")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "700"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
MIN_KEYWORD_OVERLAP = int(os.getenv("RAG_MIN_KEYWORD_OVERLAP", "1"))

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "that",
    "the", "their", "there", "this", "to", "using", "what", "when", "where",
    "why", "with", "your"
}


def get_client():
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL)

    return QdrantClient(path=QDRANT_PATH)


def ensure_collection(client):
    if client.collection_exists(COLLECTION_NAME):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )


def tokenize(text):
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def keyword_set(text):
    return {
        token
        for token in tokenize(text)
        if len(token) > 2 and token not in STOPWORDS
    }


def keyword_overlap(query, text):
    query_keywords = keyword_set(query)
    text_keywords = keyword_set(text)

    return len(query_keywords.intersection(text_keywords))


def embed_text(text):
    vector = [0.0] * VECTOR_SIZE

    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))

    if norm == 0:
        return vector

    return [value / norm for value in vector]


def chunk_text(text, chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_CHUNK_OVERLAP):
    clean_text = " ".join(text.split())

    if not clean_text:
        return []

    chunks = []
    start = 0

    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunks.append(clean_text[start:end])

        if end == len(clean_text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def upsert_document(source, text, chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_CHUNK_OVERLAP):
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    if not chunks:
        return {
            "source": source,
            "chunks_inserted": 0
        }

    client = get_client()

    try:
        ensure_collection(client)
        points = []

        for chunk_index, chunk in enumerate(chunks):
            points.append(
                models.PointStruct(
                    id=uuid.uuid4().int >> 65,
                    vector=embed_text(chunk),
                    payload={
                        "source": source,
                        "chunk_index": chunk_index,
                        "text": chunk
                    }
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        return {
            "source": source,
            "chunks_inserted": len(points)
        }
    finally:
        client.close()


def search_documents(query, top_k=DEFAULT_TOP_K):
    client = get_client()

    try:
        ensure_collection(client)
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=embed_text(query),
            limit=top_k
        )

        matches = []

        for point in response.points:
            text = point.payload.get("text", "")
            overlap = keyword_overlap(query, text)

            if overlap < MIN_KEYWORD_OVERLAP:
                continue

            matches.append({
                "score": point.score,
                "keyword_overlap": overlap,
                "source": point.payload.get("source", "unknown"),
                "chunk_index": point.payload.get("chunk_index", 0),
                "text": text
            })

        return matches
    finally:
        client.close()


def retrieve_context(query, top_k=DEFAULT_TOP_K):
    matches = search_documents(query, top_k=top_k)

    if not matches:
        return f"No relevant VectorDB context found for query: {query}"

    context_parts = []

    for match in matches:
        context_parts.append(
            f"[source={match['source']} score={match['score']:.3f} "
            f"keyword_overlap={match['keyword_overlap']}] "
            f"{match['text']}"
        )

    return "\n".join(context_parts)
