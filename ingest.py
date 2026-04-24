"""
agent/ingest.py
---------------
PDF ingestion pipeline: extract then chunk then embed then store.
No external RAG libraries — pure pdfplumber + tiktoken + Mistral + SQLite.
"""

import os
import sqlite3
import time
import json
import pdfplumber
import tiktoken
import numpy as np
import logging
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ══ Constants ══════════════════════════════════════════════════════════════════

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY)
DB_PATH         = "data/prior_auth_rag.db"
CHUNK_SIZE      = 512   # tokens — ~1-2 clinical paragraphs, enough context
CHUNK_OVERLAP   = 50    # token overlap to avoid splitting mid-concept
EMBED_MODEL     = "mistral-embed"


# ══ Database ═══════════════════════════════════════════════════════════════════

def init_db() -> None:
    """Create chunks table if it does not exist.

    Stores embeddings as raw bytes (numpy .tobytes()) — no external vector DB.
    """
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source    TEXT NOT NULL,
            page      INTEGER,
            chunk_idx INTEGER,
            text      TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def source_already_ingested(source: str) -> bool:
    """Check if a PDF filename already exists in the database.

    Args:
        source: basename of the PDF file.

    Returns:
        True if rows exist for this source, False otherwise.
    """
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE source = ?", (source,)
    ).fetchone()
    conn.close()
    return row[0] > 0


# ══ Extraction ═════════════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text page-by-page using pdfplumber.

    pdfplumber preserves clinical PDF layout (tables, headers) better
    than PyPDF2. Empty pages are skipped.

    Args:
        pdf_path: absolute or relative path to the PDF file.

    Returns:
        List of dicts with keys 'page' (int) and 'text' (str).
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page": i + 1, "text": text.strip()})
    return pages


# ══ Chunking ═══════════════════════════════════════════════════════════════════

def chunk_text(text: str, source: str, page: int) -> list[dict]:
    """Split page text into token-aware sliding window chunks.

    Fixed-size chunks with overlap preserve clinical context across
    section boundaries better than sentence splitting alone.
    512 tokens ≈ 1-2 clinical paragraphs.

    Args:
        text:   raw page text.
        source: PDF basename, stored with each chunk for citation.
        page:   page number, stored for citation display.

    Returns:
        List of chunk dicts with keys: source, page, chunk_idx, text.
    """
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens    = tokenizer.encode(text)
    chunks    = []
    idx       = 0
    chunk_num = 0

    while idx < len(tokens):
        end        = min(idx + CHUNK_SIZE, len(tokens))
        chunk_toks = tokens[idx:end]
        chunks.append({
            "source":    source,
            "page":      page,
            "chunk_idx": chunk_num,
            "text":      tokenizer.decode(chunk_toks),
        })
        idx       += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_num += 1

    return chunks


# ══ Embedding ══════════════════════════════════════════════════════════════════

def embed_chunks(texts: list[str]) -> list[np.ndarray]:
    """
    Batch embed text chunks using Mistral's mistral-embed model.
    Returns list of numpy float32 vectors.
    Batches in groups of 32 to respect API limits.
    Retries with exponential backoff on rate limit errors.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of numpy float32 embedding vectors.
    """
    vectors  = []
    batch_sz = 16  # reduced from 32 to stay under rate limits
    for i in range(0, len(texts), batch_sz):
        batch       = texts[i : i + batch_sz]
         #exponential backoff — retry up to 5 times on 429
        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=EMBED_MODEL,
                    inputs=batch
                )
                for item in response.data:
                    vectors.append(np.array(item.embedding, dtype=np.float32))
                 #delay between batches to stay under rate limit
                time.sleep(1.5)
                break  # success — exit retry loop

            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = (2 ** attempt) + 1
                    logger.warning(
                        "Rate limit hit, waiting %ss (attempt %d/%d)",
                        wait, attempt + 1, max_retries
                    )
                    time.sleep(wait)
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise   #non-rate-limit error — raise immediately

    return vectors


# ══ Storage ════════════════════════════════════════════════════════════════════

def store_chunks(chunks: list[dict], vectors: list[np.ndarray]) -> None:
    """Persist chunks and their embeddings to SQLite.

    Embeddings stored as raw bytes — avoids any external vector DB dependency.

    Args:
        chunks:  list of chunk dicts from chunk_text().
        vectors: list of numpy float32 arrays from embed_chunks().
    """
    conn = sqlite3.connect(DB_PATH)
    for chunk, vec in zip(chunks, vectors):
        conn.execute(
            """INSERT INTO chunks (source, page, chunk_idx, text, embedding)
               VALUES (?, ?, ?, ?, ?)""",
            (chunk["source"], chunk["page"], chunk["chunk_idx"],
             chunk["text"], vec.tobytes()),
        )
    conn.commit()
    conn.close()


# ══ Public API ═════════════════════════════════════════════════════════════════

def ingest_pdf(pdf_path: str, source_name: str = None) -> dict:
    """Run the full ingestion pipeline for one PDF file.

    Skips the file if it has already been ingested (idempotent).

    Args:
        pdf_path: path to the PDF file to ingest.

    Returns:
        Dict with keys: source, status, pages, chunks.
    """
    init_db()
    source = source_name if source_name else os.path.basename(pdf_path)

    if source_already_ingested(source):
        return {"source": source, "status": "already_ingested", "chunks": 0}

    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        return {"source": source, "status": "no_text_extracted", "chunks": 0}

    all_chunks = []
    for page_data in pages:
        all_chunks.extend(chunk_text(page_data["text"], source, page_data["page"]))

    vectors = embed_chunks([c["text"] for c in all_chunks])
    store_chunks(all_chunks, vectors)

    return {
        "source": source,
        "status": "success",
        "pages":  len(pages),
        "chunks": len(all_chunks),
    }
# ══ Entry Point ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    PDF_DIR = "data/pdfs"
    pdf_files = [
        f for f in os.listdir(PDF_DIR)
        if f.endswith(".pdf")
    ]

    if not pdf_files:
        print("No PDFs found in data/pdfs/")
    else:
        print(f"Found {len(pdf_files)} PDFs to ingest:")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file}")

        print("\nStarting ingestion...")
        for pdf_file in pdf_files:
            pdf_path = os.path.join(PDF_DIR, pdf_file)
            print(f"\nIngesting: {pdf_file}")
            result = ingest_pdf(pdf_path)
            print(f"  Status: {result['status']}")
            if result.get('chunks'):
                print(f"  Pages:  {result.get('pages', 0)}")
                print(f"  Chunks: {result['chunks']}")

        print("\nIngestion complete.")
        print(f"Database saved to: {DB_PATH}")

    


