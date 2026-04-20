# 07 — Clinical Domain

## Oncology prior authorization — the problem this system addresses

This system operates in one clinical domain: oncology drug prior
authorization, specifically for PD-1/PD-L1 checkpoint inhibitor
immunotherapy in non-small cell lung cancer.

This document explains the clinical context in depth — the drug
mechanism, the trial evidence, the NCCN guideline structure, the payer
criteria, and the specific clinical distinctions the system must get
right to produce a valid verdict.

---

## Non-small cell lung cancer — epidemiology

NSCLC accounts for approximately 84% of all lung cancer diagnoses in
the United States. In 2024, approximately 238,000 Americans were
diagnosed with lung cancer. Stage IIIB/IV NSCLC — the population
eligible for first-line pembrolizumab monotherapy — has a 5-year
survival rate of approximately 8% with platinum-based chemotherapy
alone.

The introduction of pembrolizumab for PD-L1 high NSCLC changed this.
KEYNOTE-024 demonstrated a 5-year overall survival rate of 31.9% in
the pembrolizumab arm vs 16.3% in the chemotherapy arm — a nearly
2× improvement for an eligible population.

This is the clinical urgency behind the PA problem. A 14-day delay in
starting pembrolizumab for a patient with stage IV NSCLC is not an
administrative inconvenience — it is 14 days of tumor progression in
a disease where the treatment window matters.

---

## Pembrolizumab mechanism

Pembrolizumab (Keytruda, Merck) is a humanised IgG4 monoclonal antibody
that binds to PD-1 (programmed death receptor-1) on T lymphocytes and
blocks its interaction with PD-L1 and PD-L2 ligands.

**The mechanism:**
- Tumor cells express PD-L1 on their surface to evade immune destruction
- PD-L1 binds to PD-1 on cytotoxic T cells, inhibiting their activity
- Pembrolizumab occupies PD-1, preventing PD-L1 from binding
- T cells remain active and attack the tumor

**Why PD-L1 TPS matters:** PD-L1 TPS (Tumor Proportion Score) measures
the percentage of tumor cells with membranous PD-L1 staining. Higher
TPS indicates greater PD-L1 expression on the tumor, which correlates
with greater likelihood of response to PD-1 blockade. The 50% threshold
for Category 1 monotherapy eligibility comes directly from KEYNOTE-024
trial design and results.

**Why EGFR/ALK must be negative:** Patients with EGFR mutations (exon
19 deletions, L858R, exon 20 insertions) or ALK rearrangements have
specific oncogenic drivers that respond to targeted tyrosine kinase
inhibitors (osimertinib for EGFR, alectinib for ALK) with superior
outcomes compared to immunotherapy. These patients were excluded from
KEYNOTE-024. NCCN guidelines and FDA labeling both specify EGFR/ALK-
negative as a prerequisite for pembrolizumab monotherapy. The system
must catch EGFR-positive submissions and return CRITERIA NOT MET.

---

## KEYNOTE-024 — the trial behind the approval

KEYNOTE-024 (NCT02142738) was the pivotal phase 3 trial that established
pembrolizumab as first-line standard of care for high PD-L1 NSCLC.

**Enrollment criteria relevant to this system:**
- Histologically confirmed stage IV NSCLC (squamous or non-squamous)
- PD-L1 TPS >= 50% by Dako 22C3 pharmDx assay
- No sensitizing EGFR mutations or ALK rearrangements
- ECOG PS 0-1
- No prior systemic treatment for metastatic disease
- No active autoimmune disease requiring systemic treatment

These enrollment criteria define the PA eligibility criteria. The five
elements Layer 1 checks exist precisely because the FDA and NCCN used
KEYNOTE-024 eligibility as the basis for the pembrolizumab indication.

**Key results:**
- Progression-free survival: 10.3 months vs 6.0 months (HR 0.50, p<0.001)
- Overall survival HR: 0.63 (95% CI 0.47-0.86) at final analysis
- 5-year overall survival: 31.9% vs 16.3%
- Objective response rate: 44.8% vs 27.8%
- Complete response rate: 5.3% vs 1.0%

KEYNOTE-042 extended the pembrolizumab indication to PD-L1 TPS >= 1%
(Category 2A for 1-49%, Category 1 for >= 50%). This system focuses
on the >= 50% Category 1 indication from KEYNOTE-024 — the highest
evidence level, most commonly approved by payers without additional
medical necessity review.

---

## PD-L1 testing — why assay type matters for PA

Not all PD-L1 assays are equivalent for PA purposes. Four PD-L1 IHC
assays are commercially available:

| Assay | Manufacturer | FDA companion diagnostic for |
|---|---|---|
| 22C3 pharmDx | Dako (Agilent) | Pembrolizumab — NSCLC, TNBC, cervical, others |
| 28-8 pharmDx | Dako (Agilent) | Nivolumab — NSCLC, melanoma |
| SP142 | Ventana (Roche) | Atezolizumab — NSCLC, TNBC |
| SP263 | Ventana (Roche) | Durvalumab — NSCLC |

The FDA approved pembrolizumab in NSCLC specifically based on PD-L1
measured by the **Dako 22C3 pharmDx assay**. The SP142 assay
systematically underestimates PD-L1 TPS compared to 22C3 — a patient
scoring 45% on SP142 may score 55% on 22C3. Payers that require 22C3
specifically will deny a claim that reports PD-L1 by SP142.

**Why this matters for Layer 1:** The quality gate checks that PD-L1
is documented as a numeric TPS value. A complete note should specify
both the value AND the assay: "PD-L1 TPS 60% by Dako 22C3 assay."
"PD-L1 elevated" fails the gate. "PD-L1 positive" fails the gate.
"PD-L1 60%" passes but "PD-L1 60% by Dako 22C3" is stronger
documentation for the payer.

---

## ECOG performance status — clinical and PA significance

The ECOG scale measures functional status:

| Score | Description | Pembrolizumab eligibility |
|---|---|---|
| 0 | Fully active, no restrictions | Eligible (KEYNOTE-024) |
| 1 | Restricted strenuous activity, ambulatory | Eligible (KEYNOTE-024) |
| 2 | Ambulatory > 50% of waking hours, limited self-care | Not in KEYNOTE-024; some payers require medical review |
| 3 | Limited self-care, confined to bed/chair > 50% | Excluded from KEYNOTE-024; generally not covered |
| 4 | Completely disabled | Excluded; not covered |

**Why ECOG is one of the five Layer 1 required elements:**

KEYNOTE-024 enrolled only ECOG PS 0-1 patients. The FDA approved
pembrolizumab based on this population. Payers use KEYNOTE-024
eligibility as the coverage criteria. A clinical note that does not
document ECOG PS cannot demonstrate that the patient meets trial
eligibility, and the PA will be denied.

Common documentation failures:
- ECOG PS documented in the chart but not in the PA note
- ECOG PS described narratively ("patient is ambulatory and performing
  ADLs") without a numeric score — Layer 1's implicit language handling
  should catch "ambulatory and performing ADLs" as implying ECOG 0-1
- ECOG PS assessed at a prior visit but not documented at the current
  visit

---

## ICD-10 coding for NSCLC

ICD-10-CM codes used in the demo and test scenarios:

| ICD-10 | Description | Notes |
|---|---|---|
| C34.10 | Malignant neoplasm, upper lobe, unspecified | Use when laterality unknown |
| C34.11 | Malignant neoplasm, upper lobe, right | Right upper lobe primary |
| C34.12 | Malignant neoplasm, upper lobe, left | Demo scenario |
| C34.20 | Malignant neoplasm, middle lobe, unspecified | — |
| C34.30 | Malignant neoplasm, lower lobe, unspecified | — |
| C34.31 | Malignant neoplasm, lower lobe, right | note_05 test scenario |
| C34.90 | Malignant neoplasm, unspecified | Avoid — too nonspecific |

**C-category codes** (C00-D49) route to oncology PA workflows in payer
systems. An incorrect code — J18.9 for pneumonia, or C34.90 instead
of C34.12 — routes the request to the wrong criteria module and
produces an automatic denial.

**HCPCS J9271** is the billing code for pembrolizumab. Each 1mg = 1
unit. A 200mg dose = 200 units billed. The J-code must match the drug
in the PA request — J9271 for pembrolizumab, not J9299 (nivolumab).

---

## The NCCN category system and PA implications

NCCN assigns evidence and consensus categories to every treatment
recommendation. These categories have direct PA implications:

**Category 1 — High-level evidence + uniform NCCN consensus**
Based on high-quality data (phase 3 RCTs). Most commercial payers
auto-approve Category 1 recommendations when documentation is complete.
Pembrolizumab monotherapy for PD-L1 >= 50% NSCLC is Category 1 based
on KEYNOTE-024 phase 3 data.

**Category 2A — Lower-level evidence + uniform consensus**
Based on lower-quality evidence but with uniform expert agreement.
Generally covered by payers, may require peer-to-peer review for
high-cost agents. Pembrolizumab for PD-L1 1-49% (KEYNOTE-042) is
Category 2A.

**Category 2B — Lower-level evidence + non-uniform consensus**
Some NCCN experts disagree. Higher likelihood of payer medical
necessity review. Some payers do not cover Category 2B without
additional documentation.

**Category 3 — Major disagreement**
Reserved for highly controversial areas. Rarely covered without appeal.

**Why the system returns the evidence level:** A PA coordinator who
receives "APPROVED — Category 1 (Preferred)" knows the submission has
the strongest possible clinical backing. A coordinator who receives
"APPROVED — Category 2B" knows to expect additional payer review and
should gather supplementary documentation proactively.

---

## Biomarker testing requirements for NSCLC PA

NCCN NSCLC v5.2026 recommends testing for multiple biomarkers before
first-line therapy. Documenting that these tests were performed — and
documenting the results — strengthens the PA submission:

**Required for pembrolizumab monotherapy (EGFR/ALK/ROS1 must be negative):**
- EGFR mutation testing (exon 19 del, exon 21 L858R, exon 20 ins, others)
- ALK rearrangement (IHC or FISH)
- ROS1 rearrangement (FISH or NGS)
- PD-L1 TPS by Dako 22C3 assay

**Recommended (results affect treatment sequencing but not eligibility):**
- KRAS G12C mutation (targeted therapy option second-line)
- MET exon 14 skipping mutation
- RET rearrangement
- NTRK fusion
- BRAF V600E mutation
- HER2 amplification/mutation

A PA note that documents all required testing and results is
significantly stronger than one that documents only PD-L1. Payers may
request additional documentation for EGFR/ALK if not explicitly stated
as negative — "we assumed negative" is not acceptable in a PA context.

---

## Future clinical domain extensions

This system is designed for pembrolizumab in NSCLC. The architecture
supports extension to any oncology indication by adding the relevant
PDF documents to the knowledge base.

**High-priority extensions:**

| Extension | Documents needed | PA volume |
|---|---|---|
| Pembrolizumab in other NSCLC lines | Same NCCN, second-line algorithm | High |
| Pembrolizumab + chemo (KEYNOTE-189, KEYNOTE-407) | Same NCCN, combination section | High |
| Nivolumab NSCLC | NCCN NSCLC, FDA nivolumab label, payer policies | High |
| Pembrolizumab in TNBC | NCCN Breast Cancer guidelines, KEYNOTE-522 | Medium |
| Pembrolizumab in cervical cancer | NCCN Cervical Cancer guidelines | Medium |
| Atezolizumab in NSCLC | NCCN NSCLC, FDA atezolizumab label | Medium |

Each extension requires only adding PDFs to `data/pdfs/` and re-running
`python ingest.py`. The pipeline, the two-layer logic, the API, and the
UI do not change. The system becomes a multi-indication oncology PA
tool by accumulating documents.
