"""
agent/pipeline.py

Orchestrates the full query flow by connecting intent detection,
query rewriting, hybrid search, and answer generation in the correct
order. This is the single function the server calls for every user
question.

Keeping orchestration here means the server and frontend stay thin.
Neither of them needs to know about retrieval or generation details.
"""

from .generate import detect_intent, rewrite_query, generate_answer
from .retrieval import hybrid_search


# ══ Public API ═════════════════════════════════════════════════════════════════

def run_query(query: str) -> dict:
    """Run the full RAG pipeline for one user question.

    Steps in order:
    1. PII check — refuse queries containing personal health information.
    2. Intent detection — CHAT queries return immediately.
    3. Query rewrite — improve retrieval quality.
    4. Hybrid search — semantic + BM25 + RRF + threshold check.
    5. Answer generation — cited, shaped by query type, hallucination checked.

    Args:
        query: the raw user question string.

    Returns:
        Dict with keys: answer, sources, intent, top_score.
    """
    from .generate import (
        detect_intent, rewrite_query, generate_answer,
        contains_pii, PII_REFUSAL
    )
    from .retrieval import hybrid_search

    # Step 1: PII refusal
    if contains_pii(query):
        return {
            "answer":    PII_REFUSAL,
            "sources":   [],
            "intent":    "REFUSED",
            "top_score": 0.0,
        }

    # Step 2: intent detection
    intent = detect_intent(query)

    if intent == "CHAT":
        return {
            "answer":    "Hello! I am a clinical protocol assistant. "
                         "Ask me a question about treatment guidelines.",
            "sources":   [],
            "intent":    "CHAT",
            "top_score": 0.0,
        }

    # Step 3: rewrite the query for better retrieval
    rewritten = rewrite_query(query)

    # Step 4: hybrid search
    search_result = hybrid_search(rewritten)

    # Step 5: threshold check
    if not search_result["sufficient"]:
        return {
            "answer":    "Insufficient evidence — the knowledge base does "
                         "not contain reliable information to answer this "
                         "question. Please upload relevant clinical guidelines.",
            "sources":   [],
            "intent":    "SEARCH",
            "top_score": search_result["top_score"],
        }

    # Step 6: generate answer
# Step 6: generate answer
    result = generate_answer(query, search_result["chunks"])
    if result is None:
        return {
            "answer":   "Rate limit reached. Please wait 60 seconds and try again.",
            "sources":  [],
            "intent":   "SEARCH",
            "top_score": search_result["top_score"],
        }
    return {
        "answer":    result["answer"],
        "sources":   result["sources"],
        "intent":    "SEARCH",
        "top_score": search_result["top_score"],
    }