from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval import hybrid_search
from generate import check_note_quality, generate_pa_decision,detect_intent,transform_query,check_pii

app = FastAPI(
    title="Prior Authorization RAG API",
    description="Oncology PA pipeline — NCCN criteria retrieval for pembrolizumab",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


class PARequest(BaseModel):
    age: int
    sex: str
    ecog: str
    dx: str
    icd: str
    stage: str
    hist: str
    pdl1: float
    egfr: str
    alk: str
    ros1: str
    agent: str
    line: str
    regimen: str
    prior: str
    note: Optional[str] = ""


@app.get("/")
def root():
    return {
        "service": "prior-auth-rag",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
@app.post("/ingest")
async def ingest_files(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF files for ingestion into the knowledge base.
    Files are saved to data/pdfs/ and ingested immediately.
    """
    import shutil
    from ingest import ingest_pdf

    os.makedirs("data/pdfs", exist_ok=True)
    results = []

    for file in files:
        if not file.filename.endswith(".pdf"):
            results.append({
                "filename": file.filename,
                "status": "rejected",
                "reason": "only PDF files are accepted"
            })
            continue

        dest = os.path.join("data/pdfs", file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = ingest_pdf(dest)
        results.append({
            "filename": file.filename,
            "status": result["status"],
            "pages": result.get("pages", 0),
            "chunks": result.get("chunks", 0)
        })

    return {"ingested": results}

@app.post("/authorize")
def authorize(req: PARequest):
    data = req.dict()
    pii_check = check_pii(data.get("note", "") + " " + data.get("dx", ""))
    print(f"PII RESULT: {pii_check}")
    if pii_check.get("contains_pii"):
        return {
            "layer1_status": "REJECTED",
            "gaps": [],
            "layer2_status": "BLOCKED",
            "verdict": None,
            "message": (
                f"Submission rejected: Protected Health Information (PHI) detected. "
                f"Found: {', '.join(pii_check.get('pii_types_found', []))}. "
                f"Please de-identify the clinical note before submission per HIPAA Safe Harbor guidelines."
            ),
            "tracker": build_tracker(data, None, ["PHI detected in submission"])
        }

    note_text = data.get("note", "").strip()
    if not note_text:
        note_text = json.dumps({
            "diagnosis": data["dx"],
            "icd": data["icd"],
            "stage": data["stage"],
            "pdl1": data["pdl1"],
            "egfr": data["egfr"],
            "alk": data["alk"],
            "ecog": data["ecog"],
            "line": data["line"],
            "prior_treatment": data["prior"],
            "agent": data["agent"]
        })
    quality = check_note_quality(note_text)

    if not quality.get("complete", True):
        return {
            "layer1_status": "INCOMPLETE",
            "gaps": quality.get("gaps", []),
            "layer1_summary": quality.get("summary", ""),
            "layer2_status": "BLOCKED",
            "verdict": None,
            "tracker": build_tracker(data, None, quality.get("gaps", []))
        }

    query = (
        f"{data['agent']} {data['dx']} stage {data['stage']} "
        f"PD-L1 {data['pdl1']}% {data['line']} "
        f"EGFR {data['egfr']} ALK {data['alk']}"
    )
    intent = detect_intent(query)
    if intent == "CHAT":
        return {
            "layer1_status": "PASS",
            "gaps": [],
            "layer2_status": "CHAT",
            "verdict": None,
            "message": "This appears to be a conversational query. Please submit a clinical PA request.",
            "tracker": build_tracker(data, None, [])
        }

    query = transform_query(query)
    result = hybrid_search(query)
    if not result["sufficient"]:
        return {
            "layer1_status": "PASS",
            "gaps": [],
            "layer2_status": "INSUFFICIENT EVIDENCE",
            "verdict": None,
            "tracker": build_tracker(data, None, [])
        }

    context = "\n\n".join([c["text"] for c in result["chunks"]])
    decision = generate_pa_decision(data, context)

    return {
        "layer1_status": "PASS",
        "gaps": [],
        "layer1_summary": quality.get("summary", ""),
        "layer2_status": decision.get("verdict", "CRITERIA NOT MET"),
        "verdict": decision,
        "tracker": build_tracker(data, decision, [])
    }


def build_tracker(data: dict, decision: dict, gaps: list) -> dict:
    return {
        "patient_id": f"PA-{abs(hash(data['icd'] + data['agent'])) % 90000 + 10000}",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "agent": data["agent"],
        "icd10": data["icd"],
        "diagnosis": data["dx"],
        "stage": data["stage"],
        "pdl1_tps": f"{data['pdl1']}%",
        "egfr": data["egfr"],
        "alk": data["alk"],
        "ecog_ps": data["ecog"],
        "line_of_therapy": data["line"],
        "layer1_note_quality": "PASS" if not gaps else "FAIL",
        "layer1_gaps": gaps,
        "layer2_verdict": decision.get("verdict", "BLOCKED") if decision else "BLOCKED",
        "evidence_level": decision.get("evidence_level", "N/A") if decision else "N/A",
        "criteria_summary": decision.get("criteria_checklist", []) if decision else [],
        "nccn_reference": "NCCN NSCLC Guidelines v5.2026",
        "appeal_recommended": decision.get("appeal_recommended", True) if decision else True
    }