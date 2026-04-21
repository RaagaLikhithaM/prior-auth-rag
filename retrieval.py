"""
agent/retrieval.py

Implements hybrid search over the ingested chunk database.
Two independent search methods run in parallel and their ranked
results are merged using Reciprocal Rank Fusion.

Semantic search: embeds the query and finds chunks with the highest
cosine similarity to the query vector.

BM25 keyword search: scores chunks based on term frequency and
inverse document frequency, catching exact clinical terms that
semantic search might miss.

Reciprocal Rank Fusion: merges the two ranked lists by giving each
chunk a score based on its position in each list, then sorting by
combined score. This is more stable than averaging raw scores.
"""

import os
import sqlite3
import math
import numpy as np
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY   = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY)
DB_PATH           = "data/prior_auth_rag.db"
EMBED_MODEL       = "mistral-embed"
TOP_K             = 5
SIM_THRESHOLD     = 0.70
RRF_K             = 60


# ══ Helpers ════════════════════════════════════════════════════════════════════

def load_all_chunks() -> list[dict]:
    """Load every chunk and its embedding from SQLite.

    We load all chunks into memory for search because the dataset is
    small enough (a few hundred chunks per PDF). For larger corpora
    an approximate nearest neighbour index would be more appropriate.
 
    Returns:
        List of dicts with keys: id, source, page, chunk_idx, text,
        embedding (as float32 numpy array).

        # In-memory scan is fine for ~1000-2000 chunks.
        # At scale, replace with an ANN index (e.g. HNSW).
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, source, page, chunk_idx, text, embedding FROM chunks"
    ).fetchall()
    conn.close()

    chunks = []
    for row in rows:
        chunks.append({
            "id":        row[0],
            "source":    row[1],
            "page":      row[2],
            "chunk_idx": row[3],
            "text":      row[4],
            "embedding": np.frombuffer(row[5], dtype=np.float32),
        })
    return chunks


def embed_query(query: str) -> np.ndarray:
    """Embed the user query using the same Mistral model used at ingestion.

    Using the same model for query and document embeddings is required
    for cosine similarity to be meaningful.

    Args:
        query: the user question string.

    Returns:
        Float32 numpy array of the query embedding.
    """
    response = client.embeddings.create(model=EMBED_MODEL, inputs=[query])
    return np.array(response.data[0].embedding, dtype=np.float32)


# ══ Semantic search ════════════════════════════════════════════════════════════

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Cosine similarity measures the angle between two vectors regardless
    of their magnitude, which is what we want for comparing embeddings.

    Args:
        vec_a: first embedding vector.
        vec_b: second embedding vector.

    Returns:
        Float between -1 and 1. Higher means more similar.
    """
    dot    = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def semantic_search(query_vec: np.ndarray, chunks: list[dict]) -> list[dict]:
    """Rank all chunks by cosine similarity to the query vector.

    Args:
        query_vec: embedded query from embed_query().
        chunks:    all chunks loaded from the database.

    Returns:
        List of chunks sorted by similarity descending, each with a
        'score' key added.
    """
    scored = []
    for chunk in chunks:
        score = cosine_similarity(query_vec, chunk["embedding"])
        scored.append({**chunk, "score": score})
    return sorted(scored, key=lambda x: x["score"], reverse=True)


# ══ BM25 keyword search ════════════════════════════════════════════════════════

def tokenize(text: str) -> list[str]:
    """Lowercase and split text into tokens for BM25.

    Simple whitespace tokenization is sufficient here because clinical
    terms are mostly single words or hyphenated phrases.

    Args:
        text: raw string to tokenize.

    Returns:
        List of lowercase string tokens.
    """
    return text.lower().split()


def bm25_search(query: str, chunks: list[dict]) -> list[dict]:
    """Score and rank chunks using the BM25 algorithm from scratch.

    BM25 catches exact keyword matches that semantic search misses,
    such as specific drug names, ICD codes, or measurement thresholds.

    BM25 parameters:
        k1 = 1.5  controls term frequency saturation
        b  = 0.75 controls document length normalisation

    Args:
        query:  raw query string.
        chunks: all chunks loaded from the database.

    Returns:
        List of chunks sorted by BM25 score descending, each with a
        'score' key added.
    """
    k1 = 1.5
    b  = 0.75

    query_tokens = tokenize(query)
    corpus       = [tokenize(c["text"]) for c in chunks]
    N            = len(corpus)
    avg_dl       = sum(len(doc) for doc in corpus) / max(N, 1)

    # Document frequency: how many chunks contain each term
    df = {}
    for doc in corpus:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    scored = []
    for idx, (chunk, doc) in enumerate(zip(chunks, corpus)):
        dl    = len(doc)
        score = 0.0
        tf    = {}
        for term in doc:
            tf[term] = tf.get(term, 0) + 1

        for term in query_tokens:
            if term not in df:
                continue
            idf = math.log((N - df[term] + 0.5) / (df[term] + 0.5) + 1)
            tf_score = (tf.get(term, 0) * (k1 + 1)) / (
                tf.get(term, 0) + k1 * (1 - b + b * dl / avg_dl)
            )
            score += idf * tf_score

        scored.append({**chunk, "score": score})

    return sorted(scored, key=lambda x: x["score"], reverse=True)


# ══ Reciprocal Rank Fusion ═════════════════════════════════════════════════════

def reciprocal_rank_fusion(
    semantic_results: list[dict],
    bm25_results: list[dict],
) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion.

    RRF gives each chunk a score of 1 divided by (rank + RRF_K) in
    each list and sums these scores. This is more stable than averaging
    raw scores because it is not sensitive to scale differences between
    cosine similarity and BM25 scores.

    RRF_K = 60 is the standard value from the original RRF paper.

    Args:
        semantic_results: chunks ranked by cosine similarity.
        bm25_results:     chunks ranked by BM25 score.

    Returns:
        List of unique chunks sorted by combined RRF score descending.
    """
    rrf_scores = {}

    for rank, chunk in enumerate(semantic_results):
        cid = chunk["id"]
        rrf_scores[cid] = rrf_scores.get(cid, {"chunk": chunk, "score": 0.0})
        rrf_scores[cid]["score"] += 1.0 / (rank + RRF_K)

    for rank, chunk in enumerate(bm25_results):
        cid = chunk["id"]
        if cid not in rrf_scores:
            rrf_scores[cid] = {"chunk": chunk, "score": 0.0}
        rrf_scores[cid]["score"] += 1.0 / (rank + RRF_K)

    merged = sorted(
        rrf_scores.values(), key=lambda x: x["score"], reverse=True
    )
    return [entry["chunk"] for entry in merged]


# ══ Public API ═════════════════════════════════════════════════════════════════

def hybrid_search(query: str) -> dict:
    """Run hybrid search and return top chunks with a threshold check.

    This is the single function called by the pipeline. It runs semantic
    search and BM25 in parallel over all stored chunks, merges the
    results with RRF, and checks whether the top result meets the
    minimum similarity threshold.

    If the top chunk similarity is below SIM_THRESHOLD the function
    returns a flag so the generator can respond with insufficient
    evidence instead of hallucinating an answer.

    Args:
        query: the user question string.

    Returns:
        Dict with keys:
            chunks:      list of top-k chunk dicts for generation.
            top_score:   cosine similarity of the best chunk.
            sufficient:  True if top_score meets SIM_THRESHOLD.
    """
    chunks = load_all_chunks()
    if not chunks:
        return {"chunks": [], "top_score": 0.0, "sufficient": False}

    query_vec        = embed_query(query)
    semantic_results = semantic_search(query_vec, chunks)
    bm25_results     = bm25_search(query, chunks)
    merged           = reciprocal_rank_fusion(semantic_results, bm25_results)

    top_k     = merged[:TOP_K]
    top_score = cosine_similarity(query_vec, top_k[0]["embedding"]) if top_k else 0.0
    sufficient = top_score >= SIM_THRESHOLD

    return {
        "chunks":     top_k,
        "top_score":  round(top_score, 4),
        "sufficient": sufficient,
    }