# 02 — Knowledge Base

## What is in the knowledge base and why

The knowledge base was designed to cover the complete oncology prior
authorization workflow for pembrolizumab in NSCLC — from clinical
guideline criteria through payer policy requirements through regulatory
approval evidence. Three documents are included, each answering a
different question that a PA reviewer must answer.

Every document is publicly available, clinically authoritative, and
accessible without a subscription. The total knowledge base is 486
pages and 1,230 chunks.

---

## Document inventory

### 1. NCCN Clinical Practice Guidelines in Oncology — Non-Small Cell Lung Cancer, Version 5.2026

**Source:** National Comprehensive Cancer Network  
**URL:** nccn.org — Guidelines — Non-Small Cell Lung Cancer  
**Access:** Free registration required  
**Pages:** 302 | **Chunks:** 847  
**Date:** March 13, 2026  
**Clinical authority:** The definitive evidence-graded guideline for NSCLC management in the US. Every major oncology payer uses NCCN guidelines as the clinical evidence standard for cancer drug PA criteria.

**Why this is the primary document:** When a payer policy says
"pembrolizumab is covered for NSCLC meeting NCCN criteria," they mean
the specific NCCN recommendation categories in this document. Category
1 (high-level evidence, uniform consensus) is the evidence level that
triggers auto-approval at most commercial payers. This document defines
whether a patient meets Category 1.

**Key clinical content the system answers from this document:**

- First-line pembrolizumab monotherapy indication: PD-L1 TPS >= 50%,
  EGFR/ALK/ROS1 negative, ECOG PS 0-1, treatment naive, stage IIIB/IV
  or unresectable stage III
- Evidence level: Category 1 (Preferred) — based on KEYNOTE-024 and
  KEYNOTE-042 phase 3 RCT data
- Biomarker testing requirements before first-line therapy: EGFR, ALK,
  ROS1, PD-L1, KRAS G12C, MET exon 14, RET, NTRK, BRAF V600E
- Second-line options for previously treated patients
- Stage-specific treatment algorithms (resectable vs unresectable stage
  III, stage IV non-squamous, stage IV squamous)
- Dose: pembrolizumab 200mg IV Q3W or 400mg IV Q6W

**Why 847 chunks:** NCCN guidelines are structured as decision algorithms
with footnotes, appendices, and evidence tables. Each section represents
a distinct decision point in the treatment algorithm. 512-token chunks
capture individual recommendation statements with qualifying conditions
without pulling in content from adjacent algorithm branches.

**Evidence category system in this document:**

| Category | Meaning | PA significance |
|---|---|---|
| Category 1 | High-level evidence + uniform NCCN consensus | Auto-approved at most payers |
| Category 2A | Lower evidence + uniform consensus | Generally covered |
| Category 2B | Lower evidence + non-uniform consensus | May require medical necessity review |
| Category 3 | Major disagreement | Likely denied, appeal required |

---

### 2. Pembrolizumab (Keytruda) FDA Prescribing Information — 2023

**Source:** Merck via FDA accessdata.fda.gov  
**URL:** https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/125514s103lbl.pdf  
**Access:** Direct PDF, no login required  
**Pages:** 133 | **Chunks:** 292  
**Clinical authority:** FDA-approved prescribing information — legally binding for coverage purposes.

**Why this document alongside NCCN:** NCCN and FDA labeling answer
different questions. NCCN says what is clinically appropriate. The FDA
label says what is legally approved. For PA purposes, payers typically
require that the requested indication matches either FDA labeling OR a
NCCN Category 1 or 2A recommendation. Both must be present in the
knowledge base to answer both sides of the coverage question.

**Key clinical content:**

Section 1 — Indications and usage: The exact FDA-approved indication
language for NSCLC — "as a single agent for the first-line treatment
of patients with metastatic NSCLC whose tumors have high PD-L1
expression (TPS >= 50%) with no EGFR or ALK genomic tumor aberrations,
as determined by an FDA-approved test." This language is what payer
systems are programmed to match.

Section 14 — Clinical studies: KEYNOTE-024 efficacy data — PFS HR 0.50,
OS HR 0.63 at 5 years — and the eligibility criteria that define the
approved patient population.

Section 2 — Dosage: 200mg IV Q3W or 400mg IV Q6W. The requested dose
in the PA submission must match this labeling. A request for 300mg
would be denied as off-label.

Section 5 — Warnings: Immune-mediated adverse reactions — pneumonitis,
colitis, hepatitis, endocrinopathies, nephritis — that are relevant to
contraindication documentation in the clinical note.

**Why the 50% threshold is in this document:** The companion diagnostic
for pembrolizumab in NSCLC is the Dako PD-L1 IHC 22C3 pharmDx assay.
The FDA approved pembrolizumab specifically based on TPS measured by
this assay. The FDA label cites this assay by name. A PD-L1 result
measured by SP142 or SP263 is not the approved companion diagnostic —
this distinction matters for PA.

---

### 3. Cigna Drug Coverage Policy 1403 — Oncology Medications

**Source:** Cigna Healthcare  
**URL:** static.cigna.com/assets/chcp/pdf/coveragePolicies/pharmacy/ph_1403_coveragepositioncriteria_oncology.pdf  
**Access:** Public document, no login required  
**Effective date:** April 1, 2026  
**Pages:** 51 | **Chunks:** 91  
**Clinical authority:** Payer criteria document — not a clinical guideline.

**Why this document is different from the other two:** NCCN and the FDA
label answer clinical and regulatory questions. Cigna Policy 1403
answers the administrative question — what documentation does Cigna
specifically require to approve this drug? These are not the same
question. A patient with perfect NCCN Category 1 eligibility can be
denied by Cigna if the PA submission uses the wrong ICD-10 code, omits
the PD-L1 assay type, or fails to document ECOG PS explicitly.

**Key content:**

- Coverage position criteria for pembrolizumab by indication
- Required documentation checklist for NSCLC submissions
- Step therapy requirements where applicable
- Medical necessity criteria language that maps to Layer 2 verdict
- Exclusion criteria — conditions under which pembrolizumab is not
  covered regardless of clinical indication

**The critical distinction this document enables:** The system can
simultaneously answer "does this patient meet NCCN criteria?" (from
documents 1 and 2) and "does this submission meet Cigna's documentation
requirements?" (from document 3). No single source answers both.

---

## The clinical question each document answers

| Clinical question | Primary source | Secondary source |
|---|---|---|
| Is pembrolizumab monotherapy clinically appropriate? | NCCN NSCLC v5.2026 | Cigna Policy 1403 |
| What is the FDA-approved indication exactly? | FDA prescribing information | — |
| What does the payer require for approval? | Cigna Policy 1403 | FDA label (indication match) |
| What PD-L1 threshold is required? | NCCN v5.2026 | FDA label |
| Which assay measures PD-L1 for this indication? | FDA label | NCCN v5.2026 |
| What ECOG PS is required? | NCCN v5.2026 (KEYNOTE trial eligibility) | Cigna Policy 1403 |
| What dose is approved? | FDA prescribing information | NCCN v5.2026 |
| Are EGFR/ALK-positive patients excluded? | NCCN v5.2026 | FDA label |

---

## What the knowledge base does NOT cover

**Intentional gaps:**

- Real-time formulary data — these change quarterly and cannot be kept
  current from static PDFs
- Other payer policies — UnitedHealthcare, Aetna, BCBS have separate
  PA criteria documents; only Cigna Policy 1403 is included
- Second-line pembrolizumab combinations — KEYNOTE-189, KEYNOTE-407
  data for pembrolizumab + chemotherapy combinations
- Paediatric oncology — NCCN guidelines and trial data in the KB are
  for adult patients

**Gaps filled in a production system:**

- All major payer oncology policies (UHC Medical Policy MP.100.001,
  Aetna Clinical Policy Bulletin 0557)
- NCCN guidelines for other cancer types (breast, colorectal, melanoma)
- HCPCS J-code billing requirements
- Real-time drug formulary status via payer API
- FHIR-connected patient data via Epic SMART on FHIR

---

## How chunks map to Layer 2 criteria

The Layer 2 verdict evaluates seven criteria for the demo scenario.
Here is which document each criterion retrieves from:

| Layer 2 criterion | Retrieved from | Typical page range |
|---|---|---|
| Histology: NSCLC (non-squamous or squamous) | NCCN v5.2026 | MS-36, algorithm pages |
| Stage with no actionable driver mutations | NCCN v5.2026 | Algorithm pages, footnotes |
| PD-L1 TPS >= 50% (Dako 22C3 assay) | NCCN v5.2026 + FDA label | MS-36; Section 1 |
| No EGFR/ALK/ROS1 alterations | NCCN v5.2026 + FDA label | Molecular testing section |
| ECOG PS 0-1 | NCCN v5.2026 (KEYNOTE eligibility) | p. 77, algorithm footnotes |
| Treatment-naive first-line | NCCN v5.2026 | First-line therapy algorithm |
| Pembrolizumab 200mg IV Q3W dosing | FDA label + NCCN | Section 2; drug monograph |

The most valuable retrieval moment is criterion 3 — PD-L1 threshold.
Both NCCN and the FDA label contain relevant chunks. RRF merges the
two ranked lists and the most directly cited criterion pages rank first,
producing a citation that references both the clinical guideline
authority and the regulatory approval.
