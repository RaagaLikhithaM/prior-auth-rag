import streamlit as st
import requests
import json
import os

st.set_page_config(
    page_title="Oncology Prior Authorization — NCCN Criteria RAG Agent",
    layout="wide"
)

API = os.environ.get("API_URL", "http://localhost:8000")

st.title("Oncology Prior Authorization")
st.caption(
    "Two-layer RAG pipeline — clinical note quality gate + "
    "NCCN criteria retrieval for pembrolizumab PA decisions. "
    "Demo: 62-year-old, stage IIIA NSCLC, PD-L1 60%, EGFR negative."
)

with st.form("pa_form"):

    st.subheader("Patient demographics")
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input("Age", value=62, min_value=18, max_value=110)
        sex = st.selectbox("Sex", ["Male", "Female", "Non-binary"])
    with col2:
        ecog = st.selectbox(
            "ECOG performance status",
            [
                "0 — Fully active",
                "1 — Restricted strenuous activity",
                "2 — Ambulatory, up more than 50% of waking hours",
                "3 — Limited self-care",
                "4 — Completely disabled"
            ],
            index=1
        )
    with col3:
        icd = st.text_input("ICD-10 code", value="C34.12")

    st.subheader("Diagnosis")
    col4, col5 = st.columns(2)
    with col4:
        dx = st.text_input(
            "Primary diagnosis",
            value="Non-small cell lung cancer (NSCLC)"
        )
        stage = st.selectbox(
            "Stage",
            ["I", "II", "IIIA", "IIIB", "IVA", "IVB"],
            index=2
        )
    with col5:
        hist = st.selectbox(
            "Histology",
            ["Adenocarcinoma", "Squamous cell", "Large cell", "Other/NOS"],
            index=0
        )

    st.subheader("Biomarkers")
    col6, col7, col8 = st.columns(3)
    with col6:
        pdl1 = st.number_input(
            "PD-L1 TPS (%)",
            value=60.0,
            min_value=0.0,
            max_value=100.0,
            help="Tumor Proportion Score by Dako 22C3 assay"
        )
        egfr = st.selectbox(
            "EGFR mutation status",
            ["Negative", "Positive — exon 19 del", "Positive — L858R",
             "Positive — other", "Not tested"],
            index=0
        )
    with col7:
        alk = st.selectbox(
            "ALK rearrangement",
            ["Negative", "Positive", "Not tested"],
            index=0
        )
        ros1 = st.selectbox(
            "ROS1 rearrangement",
            ["Negative", "Positive", "Not tested"],
            index=0
        )
    with col8:
        kras = st.selectbox(
            "KRAS G12C",
            ["Negative", "Positive", "Not tested"],
            index=0
        )

    st.subheader("Treatment request")
    col9, col10 = st.columns(2)
    with col9:
        agent = st.text_input(
            "Requested agent",
            value="Pembrolizumab (Keytruda) 200mg IV Q3W"
        )
        line = st.selectbox(
            "Line of therapy",
            ["1L — First-line", "2L — Second-line", "3L+ — Third or later"],
            index=0
        )
    with col10:
        regimen = st.text_input(
            "Indication",
            value="Monotherapy — metastatic NSCLC, PD-L1 TPS >= 50%"
        )
        prior = st.selectbox(
            "Prior treatment history",
            [
                "None — treatment naive",
                "Prior platinum doublet chemotherapy",
                "Prior immunotherapy",
                "Prior targeted therapy"
            ],
            index=0
        )

    st.subheader("Clinical note")
    st.caption(
        "Layer 1 quality gate runs on this note. "
        "Paste physician SOAP note or leave as demo text."
    )
    note = st.text_area(
        "Clinical note",
        height=140,
        value=(
            "62-year-old male presenting for oncology consultation. "
            "Diagnosis: Non-small cell lung cancer, adenocarcinoma, "
            "stage IIIA (T2bN2M0), ICD-10 C34.12. "
            "Molecular profiling: PD-L1 TPS 60% by Dako 22C3 assay. "
            "EGFR negative (exon 19 del, exon 21 L858R, exon 20 ins). "
            "ALK negative by IHC D5F3. ROS1 negative by FISH. "
            "ECOG performance status 1. "
            "Treatment history: none — patient is treatment naive. "
            "Requesting pembrolizumab 200mg IV Q3W monotherapy, "
            "first-line, per NCCN Category 1 recommendation for "
            "PD-L1 TPS >= 50% without actionable driver mutations."
        )
    )

    submitted = st.form_submit_button(
        "Run prior authorization pipeline",
        use_container_width=True
    )

if submitted:
    ecog_num = ecog.split("—")[0].strip()
    line_code = line.split("—")[0].strip()

    payload = dict(
        age=int(age),
        sex=sex,
        ecog=ecog_num,
        dx=dx,
        icd=icd,
        stage=stage,
        hist=hist,
        pdl1=float(pdl1),
        egfr=egfr,
        alk=alk,
        ros1=ros1,
        agent=agent,
        line=line_code,
        regimen=regimen,
        prior=prior,
        note=note
    )

    with st.spinner("Running two-layer RAG pipeline..."):
        try:
            r = requests.post(
                f"{API}/authorize",
                json=payload,
                timeout=60
            )
            result = r.json()
        except Exception as e:
            st.error(f"API connection error: {e}")
            st.info(
                "Make sure the FastAPI server is running: "
                "uvicorn server.main:app --reload --port 8000"
            )
            st.stop()

    l1 = result.get("layer1_status", "")

    st.divider()
    st.subheader("Layer 1 — Note quality gate")
    if l1 == "REJECTED":
        st.error("REJECTED — Protected Health Information detected")
        st.write(result.get("message", ""))
        st.stop()

    if l1 == "INCOMPLETE":
        st.error("INCOMPLETE — pipeline halted")
        st.write(
            "The following required elements are missing "
            "from the clinical note:"
        )
        for gap in result.get("gaps", []):
            st.write(f"- {gap}")
        st.write(
            "Please complete the clinical note and resubmit. "
            "No NCCN guideline retrieval was performed."
        )
        st.stop()

    st.success("PASS — all required elements present")
    if result.get("layer1_summary"):
        st.caption(result["layer1_summary"])

    st.divider()
    st.subheader("Layer 2 — NCCN criteria evaluation")

    l2 = result.get("layer2_status", "")
    verdict = result.get("verdict", {})

    if l2 == "APPROVED":
        st.success(
            f"APPROVED — {verdict.get('evidence_level', 'NCCN Category 1')}"
        )
    elif l2 == "INSUFFICIENT EVIDENCE":
        st.warning(
            "Insufficient evidence returned from knowledge base. "
            "Check that PDFs are ingested correctly."
        )
        st.stop()
    else:
        st.warning("CRITERIA NOT MET — see checklist below")

    if verdict:
        st.write(verdict.get("overall_rationale", ""))

        st.subheader("Criteria checklist")
        for c in verdict.get("criteria_checklist", []):
            status = "MET" if c.get("met") else "NOT MET"
            st.write(
                f"**{status}** — {c.get('criterion')}  \n"
                f"{c.get('rationale')}  \n"
                f"Source: {c.get('source')}"
            )
            st.divider()

    st.subheader("PA decision tracker")
    st.caption(
        "Structured JSON output — mirrors StackAI "
        "Generate Tracker Entry agent"
    )
    st.json(result.get("tracker", {}))