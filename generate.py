import os, json, re
from mistralai import Mistral
from dotenv import load_dotenv
load_dotenv()

def get_client():
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    return Mistral(api_key=api_key)

MODEL = "mistral-medium-latest"
INTENT_PROMPT = """Classify this input as one of two categories:
- SEARCH: a clinical query that requires knowledge base retrieval (PA request, drug criteria, guideline question, patient scenario)
- CHAT: conversational input that does not require retrieval (greetings, thanks, general chat)

Input: {query}

Respond with exactly one word: SEARCH or CHAT"""


def detect_intent(query: str) -> str:
    """
    Classify query as SEARCH or CHAT.
    CHAT queries skip knowledge base retrieval entirely.
    Returns: 'SEARCH' or 'CHAT'
    """
    prompt = INTENT_PROMPT.format(query=query)
    resp = get_client().chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    result = resp.choices[0].message.content.strip().upper()
    return "SEARCH" if "SEARCH" in result else "CHAT"
QUERY_TRANSFORM_PROMPT = """You are a clinical search query optimizer for a prior authorization RAG system.

Expand this query with relevant clinical synonyms, drug names, and standard terminology to improve retrieval from NCCN guidelines and payer policy documents.

Original query: {query}

Rules:
- Add drug brand names and generic names (pembrolizumab = Keytruda)
- Expand abbreviations (NSCLC = non-small cell lung cancer, PD-L1 = programmed death ligand 1)
- Add relevant clinical terms (first-line = first-line therapy = 1L = treatment naive)
- Keep it under 100 words
- Return only the expanded query, no explanation

Expanded query:"""


def transform_query(query: str) -> str:
    """
    Expand clinical query with synonyms and standard terminology
    to improve BM25 and semantic retrieval from guideline PDFs.
    Returns expanded query string.
    """
    prompt = QUERY_TRANSFORM_PROMPT.format(query=query)
    resp = get_client().chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    expanded = resp.choices[0].message.content.strip()
    print(f"Query transformed: {query[:50]}... → {expanded[:80]}...")
    return expanded
PII_DETECTION_PROMPT = """You are a HIPAA compliance checker. Scan this clinical text for Protected Health Information (PHI).

Check for:
- Patient full names (first + last)
- Social Security Numbers (SSN)
- Medical Record Numbers (MRN)
- Dates of birth (full date — month/day/year)
- Phone numbers
- Street addresses
- Email addresses
- Health plan beneficiary numbers

Text to scan:
{text}

Respond ONLY as JSON:
{{
  "contains_pii": true or false,
  "pii_types_found": ["list of PII types found, empty if none"],
  "safe_to_process": true or false
}}"""


def check_pii(text: str) -> dict:
    """
    Scan input text for HIPAA-defined Protected Health Information.
    Returns dict with contains_pii, pii_types_found, safe_to_process.
    If PII is detected, the pipeline should refuse to process.
    """
    prompt = PII_DETECTION_PROMPT.format(text=text[:2000])
    resp = get_client().chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.choices[0].message.content
    clean = re.sub(r"```json|```", "", raw).strip()
    print(f"PII CHECK RESULT: {clean}")
    try:
        return json.loads(clean)
    except Exception:
        return {
            "contains_pii": False,
            "pii_types_found": [],
            "safe_to_process": True
        }
NOTE_QUALITY_PROMPT = """You are a prior authorization specialist reviewing a clinical note.

Check whether the note contains ALL of the following required elements:
1. ICD-10 diagnosis code
2. Biomarker results (PD-L1 TPS %, EGFR status, ALK status)
3. Line of therapy (first-line, second-line, etc.)
4. ECOG performance status (0-4)
5. Prior treatment history

Clinical note:
{note}

Note: elements may be stated implicitly (e.g. 'ambulates independently' implies ECOG 0-1,
'treatment-naive' implies no prior therapy). Extract meaning, do not keyword match.

Respond ONLY as JSON with no other text:
{{
  "complete": true,
  "gaps": [],
  "summary": "one sentence summary of what is present"
}}

If incomplete:
{{
  "complete": false,
  "gaps": ["list each missing element clearly"],
  "summary": "one sentence summary of what is present"
}}"""

PA_DECISION_PROMPT = """You are an oncology prior authorization reviewer applying NCCN guidelines and payer criteria.

Patient data:
{patient_json}

Retrieved guideline context:
{context}

Evaluate whether this patient meets criteria for the requested treatment.
Check each criterion against the retrieved guidelines.

Respond ONLY as JSON with no other text:
{{
  "verdict": "APPROVED",
  "evidence_level": "Category 1",
  "criteria_checklist": [
    {{
      "criterion": "PD-L1 TPS >= 50%",
      "met": true,
      "rationale": "PD-L1 TPS 60% meets threshold",
      "source": "NCCN NSCLC v5.2026"
    }}
  ],
  "overall_rationale": "2-3 sentence summary",
  "appeal_recommended": false
}}

If criteria not met, use verdict: "CRITERIA NOT MET" and appeal_recommended: true."""


def check_note_quality(note: str) -> dict:
    prompt = NOTE_QUALITY_PROMPT.format(note=note)
    resp = get_client().chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.choices[0].message.content
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(clean)
    except:
        return {"complete": False, "gaps": ["Could not parse note"], "summary": ""}


def generate_pa_decision(patient_data: dict, context: str) -> dict:
    prompt = PA_DECISION_PROMPT.format(
        patient_json=json.dumps(patient_data, indent=2),
        context=context
    )
    resp = get_client().chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.choices[0].message.content
        
    clean = re.sub(r"```json|```", "", raw).strip()
    
    try:
        return json.loads(clean)
    except Exception as e:
        print(f"JSON PARSE ERROR: {e}")
        try:
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(clean[start:end])
        except Exception as e2:
            print(f"SECOND PARSE ERROR: {e2}")
        return {
            "verdict": "CRITERIA NOT MET",
            "evidence_level": "N/A",
            "criteria_checklist": [],
            "overall_rationale": "Could not parse decision",
            "appeal_recommended": True
        }