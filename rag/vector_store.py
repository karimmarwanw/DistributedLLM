import hashlib
import math
import os
import re
import threading
import uuid

from qdrant_client import QdrantClient, models


VECTOR_SIZE = int(os.getenv("RAG_VECTOR_SIZE", "384"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "distributed_llm_docs")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_data")
QDRANT_URL = os.getenv("QDRANT_URL")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "700"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
MIN_KEYWORD_OVERLAP = int(os.getenv("RAG_MIN_KEYWORD_OVERLAP", "2"))
VECTOR_CANDIDATE_LIMIT = int(os.getenv("RAG_VECTOR_CANDIDATE_LIMIT", "25"))
LEXICAL_SCROLL_LIMIT = int(os.getenv("RAG_LEXICAL_SCROLL_LIMIT", "256"))
CLIENT_LOCK = threading.RLock()
_SHARED_CLIENT = None

STOPWORDS = {
    "a", "about", "an", "and", "answer", "are", "as", "ask", "at", "be",
    "briefly", "but", "by", "can", "complete", "does", "explain", "for",
    "from", "give", "hard", "how", "i", "in", "is", "it", "me", "of", "on",
    "or", "paragraph", "question", "that", "the", "their", "there", "this",
    "to", "topic", "using", "very", "what", "when", "where", "why", "with",
    "word", "words", "write", "your"
}


def create_client():
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL)

    return QdrantClient(path=QDRANT_PATH, force_disable_check_same_thread=True)


def get_client():
    return create_client()


def get_shared_client():
    global _SHARED_CLIENT

    with CLIENT_LOCK:
        if _SHARED_CLIENT is None:
            _SHARED_CLIENT = create_client()

        return _SHARED_CLIENT


def close_shared_client():
    global _SHARED_CLIENT

    with CLIENT_LOCK:
        if _SHARED_CLIENT is not None:
            _SHARED_CLIENT.close()
            _SHARED_CLIENT = None


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


def normalize_keyword(token):
    if len(token) > 5 and token.endswith("sses"):
        return token[:-2]

    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"

    if len(token) > 4 and token.endswith("es"):
        return token[:-2]

    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]

    return token


def keyword_set(text):
    keywords = set()

    for token in tokenize(text):
        keyword = normalize_keyword(token)

        if len(keyword) > 2 and token not in STOPWORDS and keyword not in STOPWORDS:
            keywords.add(keyword)

    return keywords



def matched_keywords(query, text):
    query_keywords = keyword_set(query)
    text_keywords = keyword_set(text)

    return query_keywords.intersection(text_keywords)


def required_keyword_overlap(query):
    query_keyword_count = len(keyword_set(query))

    if query_keyword_count == 0:
        return MIN_KEYWORD_OVERLAP

    return min(MIN_KEYWORD_OVERLAP, query_keyword_count)


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


def upsert_document(
    source,
    text,
    chunk_size=DEFAULT_CHUNK_SIZE,
    overlap=DEFAULT_CHUNK_OVERLAP,
    client=None
):
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    if not chunks:
        return {
            "source": source,
            "chunks_inserted": 0
        }

    owns_client = client is None
    client = client or get_client()

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
        if owns_client:
            client.close()


def search_documents(query, top_k=DEFAULT_TOP_K, client=None):
    owns_client = client is None
    client = client or get_client()

    try:
        ensure_collection(client)
        candidate_limit = max(top_k, VECTOR_CANDIDATE_LIMIT)
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=embed_text(query),
            limit=candidate_limit
        )

        matches = []
        minimum_overlap = required_keyword_overlap(query)
        seen_ids = set()

        for point in response.points:
            text = point.payload.get("text", "")
            overlap_keywords = matched_keywords(query, text)
            overlap = len(overlap_keywords)

            if overlap < minimum_overlap:
                continue

            matches.append({
                "id": point.id,
                "score": point.score,
                "retrieval": "vector",
                "keyword_overlap": overlap,
                "matched_keywords": sorted(overlap_keywords),
                "source": point.payload.get("source", "unknown"),
                "chunk_index": point.payload.get("chunk_index", 0),
                "text": text
            })
            seen_ids.add(point.id)

            if len(matches) == top_k:
                break

        if len(matches) < top_k:
            matches.extend(
                lexical_search_documents(
                    client=client,
                    query=query,
                    top_k=top_k - len(matches),
                    exclude_ids=seen_ids
                )
            )

        return matches
    finally:
        if owns_client:
            client.close()


def lexical_search_documents(client, query, top_k, exclude_ids=None):
    exclude_ids = exclude_ids or set()
    minimum_overlap = required_keyword_overlap(query)
    candidates = []
    offset = None

    while True:
        records, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=LEXICAL_SCROLL_LIMIT,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        for record in records:
            if record.id in exclude_ids:
                continue

            text = record.payload.get("text", "")
            overlap_keywords = matched_keywords(query, text)
            overlap = len(overlap_keywords)

            if overlap < minimum_overlap:
                continue

            candidates.append({
                "id": record.id,
                "score": float(overlap),
                "retrieval": "keyword",
                "keyword_overlap": overlap,
                "matched_keywords": sorted(overlap_keywords),
                "source": record.payload.get("source", "unknown"),
                "chunk_index": record.payload.get("chunk_index", 0),
                "text": text
            })

        if offset is None:
            break

    candidates.sort(
        key=lambda match: (
            match["keyword_overlap"],
            len(match["matched_keywords"]),
            -match["chunk_index"]
        ),
        reverse=True
    )

    return candidates[:top_k]


def retrieve_context(query, top_k=DEFAULT_TOP_K, client=None):
    matches = search_documents(query, top_k=top_k, client=client)

    if not matches:
        return f"No relevant VectorDB context found for query: {query}"

    context_parts = []

    for match in matches:
        context_parts.append(
            f"[source={match['source']} score={match['score']:.3f} "
            f"retrieval={match['retrieval']} "
            f"keyword_overlap={match['keyword_overlap']} "
            f"matched_keywords={','.join(match['matched_keywords'])}] "
            f"{match['text']}"
        )

    return "\n".join(context_parts)
