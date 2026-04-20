"""
agent/__init__.py

Exposes the public functions for the agent package so the server
and frontend can import them from one clean place.
"""

from .ingest import ingest_pdf
from .retrieval import hybrid_search
from .generate import generate_answer
from .pipeline import run_query

__all__ = ["ingest_pdf", "hybrid_search", "generate_answer", "run_query"]
