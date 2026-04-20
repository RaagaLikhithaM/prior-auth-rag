import os, json, re
from mistralai import Mistral

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY", ""))
MODEL = "mistral-medium-latest"

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
    resp = client.chat.complete(
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
    resp = client.chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.choices[0].message.content
    print(f"\n=== MISTRAL RAW RESPONSE ===\n{raw}\n=== END ===\n")
    
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