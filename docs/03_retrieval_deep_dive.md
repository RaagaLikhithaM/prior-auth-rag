# 03 — Retrieval Deep Dive

## Why retrieval is the hardest part

Generation is solved — any sufficiently capable LLM can produce a
coherent, well-formatted PA verdict if given good context. The hard
problem is retrieval: finding the right 5 chunks out of 1,230 that
directly support the specific PA criteria being evaluated.

A system that retrieves the wrong chunks and generates fluently from
them is more dangerous than one that retrieves nothing. It produces
APPROVED verdicts with confident-sounding citations that do not exist
on the referenced pages.

This system uses three retrieval mechanisms working together.

---

## Semantic search — cosine similarity

### What an embedding is

An embedding is a list of 1024 numbers produced by the `mistral-embed`
model. These numbers represent the meaning of a piece of text as a
point in 1024-dimensional space. Two pieces of text with similar
meaning have embeddings that point in similar directions.

```
embed("pembrolizumab first-line NSCLC PD-L1 >= 50%")
  → [0.021, -0.134, 0.887, ..., 0.042]  (1024 numbers)

embed("Keytruda monotherapy treatment naive lung cancer PD-L1 positive")
  → [0.019, -0.128, 0.891, ..., 0.039]  (similar direction)

embed("osimertinib EGFR exon 19 deletion targeted therapy")
  → [-0.412, 0.033, -0.201, ..., 0.187]  (different direction)
```

The first two are close. The third is far. This is why "pembrolizumab"
and "Keytruda" retrieve the same relevant chunks even though BM25
would score them differently — they are semantically equivalent in
embedding space.

### The cosine similarity formula

```
similarity(A, B) = (A · B) / (|A| × |B|)
```

Where:
- `A · B` = dot product = sum of element-wise multiplications
- `|A|` = magnitude of A = √(sum of A squared)
- `|B|` = magnitude of B

Result is between 0 and 1 for text embeddings. 1.0 = identical meaning.
0.0 = no relationship.

### Why cosine and not Euclidean distance

Euclidean distance measures how far apart two points are in space.
A short clinical criterion and a long guideline paragraph about the
same topic have different magnitudes but similar directions. Cosine
similarity correctly identifies them as related. Euclidean distance
penalises the length difference and ranks them as distant.

### Implementation — 6 lines of numpy

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot    = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
```

No external libraries. Runs in microseconds per chunk on modern hardware.

### Where semantic search fails in clinical text

Semantic search blurs precise clinical values. The embedding for
"PD-L1 TPS >= 50%" and "PD-L1 TPS >= 1%" are similar — both concern
PD-L1 thresholds in NSCLC. But 50% triggers Category 1 pembrolizumab
monotherapy eligibility; 1% triggers a different pembrolizumab
indication (combination with chemotherapy). Acting on the wrong
threshold produces a wrong verdict.

Similarly, "EGFR exon 19 deletion" (contraindication for pembrolizumab)
and "EGFR testing required" (documentation requirement) are semantically
similar but clinically opposite in meaning for PA purposes.

This is why BM25 is essential.

---

## BM25 — keyword search from scratch

### What BM25 is

BM25 (Best Match 25) is a probabilistic keyword scoring algorithm.
It is the foundation of Elasticsearch's relevance scoring and has been
a top-performing retrieval baseline since the 1970s. Despite its age,
it remains one of the strongest retrieval algorithms for domain-specific
text because it preserves exact term matching.

The "25" refers to the 25th iteration of the Okapi BM probabilistic
retrieval framework. It encodes two insights: term frequency saturation
and document length normalisation.

### The formula

```
BM25(query, doc) = Σ IDF(term) × [tf × (k1+1)] / [tf + k1×(1 - b + b×|d|/avgdl)]
```

**IDF(term) = log((N - df + 0.5) / (df + 0.5))**
- N = total number of chunks (1,230 in this system)
- df = number of chunks containing this term
- "KEYNOTE-024" appears in ~20 chunks → high IDF → informative
- "cancer" appears in ~800 chunks → low IDF → uninformative

**tf** = frequency of term in this chunk

**k1 = 1.5** — term frequency saturation
- A chunk containing "pembrolizumab" 20 times is not 20× more relevant
- After the first few occurrences, additional repetitions add little
- k1=1.5 limits this — chosen empirically as the standard clinical
  text value

**b = 0.75** — document length normalisation
- A 512-token chunk with "PD-L1" once is as relevant as a 100-token
  chunk with "PD-L1" once
- b=0.75 normalises for chunk length relative to the corpus average

### Why BM25 is indispensable for PA criteria retrieval

BM25 treats text as exact tokens. "50" and "1" are different. "exon 19"
and "exon 20" are different. "EGFR negative" and "EGFR positive" are
different. "Category 1" and "Category 2B" are different.

For a prior authorization system evaluating precise clinical thresholds,
exact matching is not optional. A semantic search that retrieves chunks
about PD-L1 criteria in general is insufficient — the system needs the
chunk that contains the specific threshold that determines the verdict.

**BM25 catches terms that semantic search blurs:**

| Term pair | Semantic similarity | BM25 distinction |
|---|---|---|
| PD-L1 >= 50% vs PD-L1 >= 1% | High (both PD-L1 thresholds) | Distinct ("50" vs "1") |
| EGFR negative vs EGFR positive | High (both EGFR status) | Distinct ("negative" vs "positive") |
| Category 1 vs Category 2B | High (both NCCN categories) | Distinct ("1" vs "2B") |
| KEYNOTE-024 vs KEYNOTE-042 | High (both KEYNOTE trials) | Distinct ("024" vs "042") |
| C34.12 vs C34.31 | High (both NSCLC ICD codes) | Distinct ("12" vs "31") |

---

## Reciprocal Rank Fusion

### The problem with combining two ranked lists

After semantic search and BM25 each produce results, we have two ranked
lists that cannot simply be combined by averaging scores.

Cosine similarity ranges from 0 to 1. BM25 scores in this corpus range
from ~1 to ~15. Averaging them gives BM25 scores ~8× the weight of
cosine scores purely because of scale — not because BM25 is more
accurate. Any fixed weight combination is arbitrary and
corpus-dependent.

### The RRF solution

Reciprocal Rank Fusion converts ranks to scores using:

```
RRF_score(chunk) = 1 / (rank_semantic + 60) + 1 / (rank_bm25 + 60)
```

**Example with real PA criteria query:**

| Chunk | Semantic rank | BM25 rank | RRF score |
|---|---|---|---|
| NCCN: PD-L1 >= 50% Category 1 pembrolizumab | 1 | 1 | 1/61 + 1/61 = 0.0328 |
| NCCN: First-line pembrolizumab indications | 2 | 3 | 1/62 + 1/63 = 0.0320 |
| NCCN: EGFR ALK exclusions immunotherapy | 3 | 2 | 1/63 + 1/62 = 0.0318 |
| FDA label: NSCLC indication language | 4 | 8 | 1/64 + 1/68 = 0.0303 |
| Cigna policy: pembrolizumab coverage | 1 | 12 | 1/61 + 1/72 = 0.0303 |

The chunk that ranks #1 in both lists wins decisively. The chunk that
ranks #1 semantically but #12 in BM25 ties with a chunk that ranks #4
semantically and #8 in BM25 — consistent performance is rewarded over
single-method dominance.

### Why k=60

k=60 prevents a single top-ranked result from dominating too strongly.
Without k, the #1 result would score 1.0 and #2 would score 0.5 — a
2× advantage for being one rank higher. With k=60, #1 scores 1/61 and
#2 scores 1/62 — still better, but by a clinically appropriate margin.

The value 60 was shown empirically in Cormack, Clarke, and Buettcher
(2009) to outperform other values across a wide range of retrieval tasks.

### Why RRF over weighted combination

A weighted combination requires choosing weights. Which is more
reliable for a clinical PA query — semantic match or keyword match?
The answer is: it depends on the query. For "pembrolizumab first-line
NSCLC" the semantic match is strong. For "PD-L1 TPS >= 50% Dako 22C3"
the BM25 match is stronger. No fixed weight handles both correctly.

RRF is tuning-free. It uses only ranks, not raw scores, so it is
naturally scale-invariant and adapts to the characteristics of each
individual query.

---

## The 0.70 similarity threshold

### What it does

If the top chunk's cosine similarity to the query is below 0.70, the
pipeline returns "INSUFFICIENT EVIDENCE — no relevant guidelines
retrieved" instead of running Layer 2.

### Why 0.70 specifically

0.70 was determined empirically. Below this value, retrieved chunks are
topically adjacent to the query but not directly relevant to the
specific PA criteria being evaluated:

- Query about pembrolizumab in NSCLC retrieving a chunk about
  pembrolizumab in melanoma: similarity ~0.65 (below threshold)
- Query about pembrolizumab in NSCLC retrieving a chunk about
  nivolumab in NSCLC: similarity ~0.68 (below threshold — wrong drug)
- Query about pembrolizumab in NSCLC retrieving the correct NCCN
  first-line therapy section: similarity ~0.80-0.85 (above threshold)

In a clinical decision context, a weakly-retrieved chunk is more
dangerous than no chunk. A system that generates "APPROVED" from a
melanoma chunk when asked about NSCLC has made a category error with
clinical consequences.

### Production consideration

0.70 is hardcoded. In production it should be:
- A configurable environment variable
- Calibrated per knowledge base — a small, highly specific knowledge
  base may need a lower threshold than a large, broad one
- Logged to allow monitoring of threshold hit rates over time

---

## Chunking decisions and their impact on retrieval

### Why chunk size matters for oncology PA

An NCCN criterion for pembrolizumab eligibility is not a single
sentence. A complete criterion in NCCN v5.2026 reads approximately:
"Pembrolizumab (preferred, Category 1) for stage IIIB/IVA/IVB NSCLC
without sensitizing EGFR mutations or ALK/ROS1 rearrangements, PD-L1
TPS >= 50%, ECOG PS 0-1, no prior systemic therapy for metastatic
disease." This is approximately 50-60 tokens.

However, this criterion appears in context within an algorithm that
also specifies contraindications, footnotes about specific molecular
subtypes, and cross-references to other algorithm sections. A chunk
that is too small loses this context. A chunk that is too large
introduces unrelated algorithm branches that dilute the embedding.

### Why 512 tokens with 50-token overlap

512 tokens ≈ 1-2 clinical paragraphs. This captures:
- The core recommendation statement
- Its qualifying conditions (PD-L1 threshold, EGFR/ALK exclusion,
  performance status requirement)
- The evidence category and trial reference
- Immediately adjacent context that qualifies the recommendation

The 50-token overlap ensures that recommendations at chunk boundaries —
where a criterion statement ends one chunk and its qualifying condition
begins the next — appear complete in at least one chunk and are
retrievable against a specific PA criterion query.

### Why tiktoken over character splitting

We tokenise using `cl100k_base` — the same encoding used by the Mistral
API internally. Character-based chunking creates chunks of unpredictable
token length. A 2,000-character chunk of dense clinical abbreviations
might be 650 tokens (exceeds model context for some operations).
A 2,000-character chunk of prose might be 400 tokens. Token-based
chunking guarantees every chunk is within the embedding model's context
window and processing costs are predictable.

### Why pdfplumber over PyPDF2

NCCN NSCLC v5.2026 contains:
- Multi-column algorithm layouts (recommendation on left, evidence on right)
- Evidence tables with graded recommendations
- Footnotes with key qualifying conditions
- Headers that identify the patient population and treatment line

PyPDF2 reads the PDF byte stream in document order — it concatenates
multi-column content in the order it appears in the file's internal
structure, not in reading order. For NCCN's two-column algorithm pages,
this interleaves the recommendation column and evidence column,
producing garbled chunks where criteria text and evidence ratings are
mixed.

pdfplumber uses spatial analysis to reconstruct reading order by text
block position. It identifies text blocks, sorts them by page position,
and reads them in the order a human would. For NCCN guidelines, this
preserves the relationship between the recommendation statement and its
evidence grade.

### Idempotent ingestion

`source_already_ingested()` queries the database for existing rows with
the same filename before processing any PDF. Re-running `ingest.py`
after adding one new PDF does not re-process the two already-ingested
PDFs. This matters for production — a knowledge base update should
process only the new document, not rebuild the entire index.
