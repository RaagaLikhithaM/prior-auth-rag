# 08 — Cost and Infrastructure

## Cost per PA request — detailed breakdown

Every `/authorize` request triggers up to five Mistral API calls.
Here is the exact breakdown based on Mistral's pricing at time of
writing. Verify current pricing at docs.mistral.ai/pricing.

### Cost model assumptions

- PII check input: ~400 tokens (note text + prompt)
- Layer 1 input: ~900 tokens (note + prompt); output: ~150 tokens
- Intent detection input: ~150 tokens; output: ~5 tokens
- Query transformation input: ~200 tokens; output: ~100 tokens
- Embedding: ~250 tokens (expanded query)
- Layer 2 input: ~3,800 tokens (5 chunks × 512 + patient JSON + prompt);
  output: ~700 tokens

### Mistral pricing (approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| mistral-medium-latest | $2.70 | $8.10 |
| mistral-small-latest | $0.10 | $0.30 |
| mistral-embed | $0.10 | N/A |

### Cost per PA request — current implementation (all mistral-medium)

| Call | Input tokens | Output tokens | Cost |
|---|---|---|---|
| PII check | 400 | 80 | $0.0018 |
| Layer 1 quality gate | 900 | 150 | $0.0036 |
| Intent detection | 150 | 5 | $0.0004 |
| Query transformation | 200 | 100 | $0.0013 |
| Embedding | 250 | — | $0.000025 |
| Layer 2 NCCN evaluation | 3,800 | 700 | $0.0159 |
| **Total** | **5,700** | **1,035** | **~$0.023** |

### Cost per PA request — optimised implementation

Using mistral-small for PII check and intent detection (classification
tasks that do not require full reasoning capability):

| Call | Model | Cost |
|---|---|---|
| PII check | mistral-small | $0.00004 |
| Layer 1 quality gate | mistral-medium | $0.0036 |
| Intent detection | mistral-small | $0.00001 |
| Query transformation | mistral-small | $0.00003 |
| Embedding | mistral-embed | $0.000025 |
| Layer 2 NCCN evaluation | mistral-medium | $0.0159 |
| **Total** | | **~$0.020** |

The savings from switching classification tasks to mistral-small are
minimal in absolute terms because Layer 2 generation dominates the cost.
The real optimisation lever is caching: if a PA coordinator submits the
same drug/indication combination multiple times in a shift, Layer 2
results can be cached by query hash with a short TTL.

### Cost at scale

| Usage | Requests/day | Cost/day | Cost/month |
|---|---|---|---|
| Demo | 10 | $0.23 | $6.90 |
| Small oncology practice (3-5 PA staff) | 50 | $1.15 | $34.50 |
| Cancer center (20 PA staff) | 300 | $6.90 | $207 |
| Health system (5 cancer centers) | 1,500 | $34.50 | $1,035 |

At health system scale the LLM API cost is modest relative to the
value recovered from avoided PA denials. A single overturned denial
for pembrolizumab (one cycle: $11,000-$13,000) covers the entire
monthly LLM API cost for a large health system deployment.

### Cost optimisation levers

**1. Cache Layer 2 results for identical queries**

The patient demographics change per request, but the Layer 2 retrieval
context is identical for every pembrolizumab first-line NSCLC request.
Cache the retrieved chunks by query hash. Only regenerate the verdict
if the patient data changes:

```python
import hashlib
import json

def get_query_cache_key(query: str) -> str:
    return f"query:{hashlib.md5(query.encode()).hexdigest()}"

def get_context_with_cache(query: str) -> dict:
    key = get_query_cache_key(query)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    result = hybrid_search(query)
    redis_client.setex(key, 3600, json.dumps(result))  # 1 hour TTL
    return result
```

Estimated savings: 30-40% of Layer 2 embedding cost for repeated
indications.

**2. Skip Layer 2 when Layer 1 fails**

Already implemented. If Layer 1 returns incomplete, no API calls run
for Layer 2. For a workflow where 30-40% of submissions have incomplete
notes (realistic for first-attempt PA submissions), this saves 30-40%
of total Layer 2 costs.

**3. Use mistral-small for Layer 1**

Layer 1 is a structured information extraction task — check five
elements, return JSON. This does not require full reasoning capability.
Switching Layer 1 to mistral-small saves ~$0.0033 per complete request.

---

## Infrastructure cost

### Current deployment

| Component | Service | Cost |
|---|---|---|
| FastAPI backend | Local (localhost:8000) | $0 |
| Streamlit frontend | Local (localhost:8501) | $0 |
| Database | SQLite (local file) | $0 |
| Mistral API | Developer tier | Pay-per-use |
| **Total infrastructure** | | **$0/month** |

**Limitation:** Local deployment is not accessible to other users.
No persistent hosting. SQLite database is ephemeral if the machine
is reimaged.

### Cloud deployment — Railway + Streamlit Cloud

| Component | Service | Cost |
|---|---|---|
| FastAPI backend | Railway Starter ($5/month credit) | ~$5/month |
| Streamlit frontend | Streamlit Community Cloud | $0 |
| Database | SQLite on Railway filesystem | $0 (ephemeral) |
| **Total infrastructure** | | **~$5/month** |

**Limitation:** Railway free tier has ephemeral filesystem — the SQLite
database resets on restart or redeploy. PDFs must be re-ingested on
each deployment. Suitable for demo only.

### Production deployment — AWS (HIPAA eligible)

| Component | Service | Cost/month |
|---|---|---|
| FastAPI backend | ECS Fargate (0.5 vCPU, 1GB) | ~$30 |
| Load balancer | ALB | ~$18 |
| Database | RDS PostgreSQL t3.micro + pgvector | ~$20 |
| Cache | ElastiCache Redis t3.micro | ~$15 |
| Storage | S3 for PDF documents | ~$2 |
| API Gateway | AWS API Gateway | ~$3.50/M requests |
| **Total infrastructure** | | **~$90/month** |

**Add:** LLM API cost scales with usage as shown above.

### Production deployment — Azure (HIPAA BAA available)

Azure provides HIPAA BAA coverage for Azure OpenAI Service and
supporting services — the preferred deployment for healthcare
organisations requiring BAA for LLM API usage.

| Component | Service | Cost/month |
|---|---|---|
| FastAPI backend | Azure Container Apps | ~$25 |
| Database | Azure Database for PostgreSQL + pgvector | ~$30 |
| Cache | Azure Cache for Redis | ~$15 |
| Storage | Azure Blob Storage | ~$2 |
| API Management | Azure API Management (Basic) | ~$50 |
| **Total infrastructure** | | **~$125/month** |

Azure is approximately 40% more expensive than AWS equivalent but the
HIPAA BAA coverage and integrated compliance tooling justify the premium
for production healthcare deployment.

---

## API key management

API keys must never appear in source code or version control. This
system's API key was accidentally committed to the initial GitHub push
— it was revoked immediately and rotated. This section documents the
correct pattern going forward.

### Local development

Store the key in `.env` in the project root:

```
MISTRAL_API_KEY=your_key_here
```

`.env` is in `.gitignore`. Load it at startup:

```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
```

**Always verify `.env` is in `.gitignore` before the first commit.**
Run `git ls-files | grep .env` — if this returns anything, the file is
tracked and must be removed with `git rm --cached .env`.

### Cloud deployment (Railway)

Set the key as an environment variable in the Railway dashboard — never
in Procfile or any committed file. The running container reads it from
the environment at startup.

### Production (enterprise)

| Cloud | Secrets service |
|---|---|
| AWS | AWS Secrets Manager |
| Azure | Azure Key Vault |
| GCP | Google Secret Manager |
| Self-hosted | HashiCorp Vault |

**Key rotation policy for production:**
- Rotate every 90 days minimum
- One key per environment (dev/staging/prod)
- Revoke immediately if exposed in any log or commit
- Automated rotation scripts tied to CI/CD pipeline

### What to do if a key is accidentally committed

1. Revoke the key immediately in the Mistral console
2. Generate a new key
3. Run `git filter-branch` or BFG Repo Cleaner to remove from history
   — `git rm --cached` alone is insufficient, the key remains in history
4. Force-push the cleaned history
5. Assume the key was compromised and audit all API usage logs
6. Update all deployment environments with the new key

This happened during this project's development. The key was rotated
across four locations: local `.env`, Railway environment variables,
Streamlit Cloud secrets, and a second project using the same key.
The incident highlighted why `.gitignore` must be set up correctly
before the first commit.


## Current deployment — actual infrastructure

### Hugging Face Spaces (live, free, permanent)

| Component | Service | Cost |
|---|---|---|
| FastAPI backend | HF Spaces Docker container | $0 |
| Streamlit frontend | Same Docker container | $0 |
| Database | Container filesystem (SQLite) | $0 |
| PDF storage | Container filesystem | $0 |
| LLM API | Mistral AI (pay per use) | ~$0.023/request |
| **Total infrastructure** | | **$0/month** |

**URL:** https://huggingface.co/spaces/RaagaLikhitha/prior-auth-rag

HF Spaces CPU Basic tier: 2 vCPU, 16GB RAM, no sleep, no credit card
required, permanent URL. Both FastAPI (port 8000) and Streamlit (port 7860)
run in the same Docker container. HF Spaces exposes port 7860 publicly.

**One limitation:** The container filesystem is not a true persistent disk —
it persists across restarts but resets if the Space is rebuilt from scratch
(e.g. after a new code push). On rebuild, `start.sh` re-downloads the Cigna
PDF and re-runs ingest (~30 seconds). The database is rebuilt automatically
with no manual intervention.

**Why not Railway or Render for this deployment:**

Railway free tier has an ephemeral filesystem — the database resets on every
restart, requiring manual re-ingestion. Render's free tier sleeps after 15
minutes of inactivity, causing 30-60 second cold start delays. HF Spaces
has neither limitation on the CPU Basic free tier.

### API key management on HF Spaces

The Mistral API key is stored as a repository secret in HF Spaces Settings
→ Variables and secrets. It is injected as an environment variable at
container runtime. It is never committed to the repository.

The `get_client()` pattern in `generate.py` reads the key at function
call time rather than module import time:

```python
def get_client():
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    return Mistral(api_key=api_key)
```

This is required because HF Spaces injects secrets after the Python module
is imported. A global `client = Mistral(api_key=os.environ.get(...))` at
module level initialises with an empty string, producing
`Illegal header value b'Bearer '` on every API call.

### Git history cleanup

During deployment, three issues required git history rewriting:

**PDF files in history:** The NCCN, FDA label, and Cigna PDFs were
accidentally committed to git history. `git filter-branch` removed them
from all 12 commits. HF Spaces rejects files over 10MB and binary files
without Git LFS.

**Database in history:** `prior_auth_rag.db` was committed and then removed.
HF Spaces rejects binary files regardless of size without Xet storage.
The database is now built at container startup via `start.sh` instead of
being committed to the repository.

**API key exposure:** The Mistral API key was accidentally committed in
`.env` on the initial push. The key was immediately revoked and rotated.
`git rm --cached .env` removed it from tracking. The incident established
the correct pattern: `.env` in `.gitignore` before the first commit.
