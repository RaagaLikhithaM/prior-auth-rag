# 04 — Clinical Workflows

## Who uses this system and how

This system is designed for two personas who operate at different
points in the oncology PA workflow. Understanding each persona's actual
work — not an imagined version of it — is what makes the two-layer
design defensible.

---

## Persona 1 — Oncology PA Coordinator

### Who she is

An oncology PA coordinator works at a cancer center or oncology practice
submitting prior authorization requests on behalf of physicians. She
receives treatment plans from oncologists — "start pembrolizumab
first-line for Mr. X with NSCLC, PD-L1 60%" — and must translate
those plans into PA submissions that meet each payer's specific
documentation requirements.

She is not making clinical decisions. She is translating clinical
decisions into administrative documentation. The bottleneck in her
workflow is not clinical judgment — it is knowing exactly what each
payer requires in the PA submission and verifying that the clinical
note contains all of it before submitting.

### Her workflow without this system

1. Receive treatment plan from oncologist
2. Identify the drug (pembrolizumab) and payer (Cigna)
3. Navigate to Cigna's policy portal and find Policy 1403
4. Read through the 51-page policy document to find the pembrolizumab
   section
5. Compare each Cigna requirement against the clinical note
6. If documentation is missing, contact the oncologist's office
7. Wait for updated note (1-3 days)
8. Submit PA
9. Wait 11-14 business days for decision

Steps 3-6 take 20-40 minutes per submission. A coordinator handling
20-30 PA submissions per day spends 6+ hours on criteria lookup and
documentation review alone.

### Her workflow with this system

1. Receive treatment plan
2. Open the PA form, enter patient demographics and clinical data
3. Paste the clinical note into the note field
4. Click submit
5. Layer 1 returns in 15 seconds — either PASS or a specific gap list
6. If PASS, Layer 2 returns in 30 seconds — either APPROVED with
   criteria checklist or CRITERIA NOT MET with specific criterion that
   failed
7. If gaps: contact oncologist with the exact list — "note is missing
   ECOG PS and PD-L1 assay type"
8. If approved: submit PA with high confidence the documentation is
   complete

**What changes:** The lookup time goes from 20-40 minutes to 30 seconds.
The gap list is specific — not "documentation may be incomplete" but
"PD-L1 TPS result is pending, no numeric value documented." The
coordinator contacts the oncologist once with the exact gaps, not
multiple times as issues are discovered during submission review.

### What the system must do for this persona

- Return the exact gap list, not a generic "incomplete" message
- Cite the specific NCCN criterion and Cigna policy section that each
  criterion comes from, so she can show the oncologist what is needed
- Refuse to return APPROVED if any required element is missing — a
  false positive is worse than a false negative in this context
- Run in under 60 seconds — she has 20-30 submissions per day

---

## Persona 2 — Oncologist reviewing PA criteria

### Who she is

An oncologist who wants to understand whether her clinical plan will
survive payer review before investing time in a detailed submission.
She is clinically confident — she knows pembrolizumab is appropriate
for this patient. What she needs is the administrative framework:
what does Cigna specifically require, and does her note already contain
it?

### Her workflow with this system

Types a brief clinical scenario and gets back:
- Whether the indication meets NCCN Category 1 criteria
- Which specific criteria are met and which are not
- The exact NCCN guideline citation so she can document it in the chart
- What additional documentation would strengthen the submission

**What makes this valuable:** The oncologist does not have to navigate
Cigna's policy portal or cross-reference the NCCN guideline manually.
The system does the cross-referencing and returns a citation-backed
summary in 30 seconds.

---

## The authorization request lifecycle — a concrete example

**Submission:** 62-year-old male, stage IIIA NSCLC adenocarcinoma,
PD-L1 TPS 60% by Dako 22C3, EGFR negative, ALK negative, ECOG PS 1,
treatment naive. Requesting pembrolizumab 200mg IV Q3W first-line.

**Stage 1 — PII check:** No patient names, no SSNs, no MRNs, no dates
of birth. Clean.

**Stage 2 — Layer 1 quality gate:** Five elements checked:
- ICD-10 code: C34.12 — present
- Biomarkers: PD-L1 TPS 60% (Dako 22C3), EGFR negative, ALK negative
  — present and specific
- Line of therapy: first-line — present
- ECOG PS: 1 — present
- Prior treatment history: treatment naive — present

Result: COMPLETE. Note proceeds to Layer 2.

**Stage 3 — Intent detection:** Query built from form fields is a
clinical PA request. SEARCH. Proceeds to query transformation.

**Stage 4 — Query transformation:** Expanded to include full drug
names, spelled-out abbreviations, trial names, and clinical synonyms.
"Pembrolizumab (Keytruda) 200mg IV Q3W NSCLC stage IIIA PD-L1 60% 1L
EGFR negative ALK negative" becomes a 100-word expanded query including
"programmed death ligand 1 tumor proportion score KEYNOTE-024 Category
1 preferred treatment naive first-line adenocarcinoma."

**Stage 5 — Hybrid search:** BM25 finds chunks containing exact terms
("PD-L1 TPS >= 50%", "EGFR genomic tumor aberrations", "KEYNOTE-024").
Semantic search finds chunks about pembrolizumab NSCLC eligibility
more broadly. RRF merges and returns the 5 most relevant chunks —
dominated by the NCCN first-line therapy algorithm pages and the FDA
indication language.

**Stage 6 — Layer 2 evaluation:** Seven criteria evaluated against
retrieved chunks:

1. Histology (NSCLC adenocarcinoma) — MET
2. Stage with no driver mutations — MET (stage IIIA, EGFR/ALK/ROS1
   negative)
3. PD-L1 TPS >= 50% by Dako 22C3 — MET (60% exceeds threshold)
4. ECOG PS 0-1 — MET (ECOG 1)
5. Treatment naive first-line — MET
6. No contraindications — MET (none documented)
7. Dose 200mg IV Q3W — MET (matches FDA labeling)

Verdict: APPROVED — NCCN Category 1 (Preferred). appeal_recommended:
false.

**Total elapsed time:** 25-35 seconds.

---

## The edge cases — what the system catches

### Edge case 1 — EGFR positive patient (note_05)

A 58-year-old female with NSCLC, PD-L1 55%, but EGFR exon 19 deletion
positive. Requesting pembrolizumab monotherapy first-line.

Layer 1 PASSES — the note is complete. All five elements are present.
Layer 2 retrieves NCCN chunks and evaluates criteria. The EGFR exclusion
criterion fails: "EGFR positive — per NCCN guidelines, EGFR mutation-
positive patients must receive osimertinib (Tagrisso) first-line, not
pembrolizumab monotherapy."

Verdict: CRITERIA NOT MET. appeal_recommended: true.

**Why this matters:** The note was complete and the coordinator would
have submitted it. Layer 2 caught the clinical error before a wasted
submission — and before a patient received an incorrect treatment plan.

### Edge case 2 — PD-L1 result pending (note_03)

A 70-year-old male with stage IVA NSCLC. PD-L1 testing sent to
pathology — results pending at time of note. All other elements present.

Layer 1 FAILS: "PD-L1 TPS numeric result not documented — pending
status does not constitute a result."

The gap list is specific: the coordinator knows exactly what to wait
for before submitting. Submitting a PA with pending PD-L1 would result
in an automatic denial — Cigna Policy 1403 requires a documented
numeric TPS value.

### Edge case 3 — Real clinical note messiness (note_04)

A real de-identified clinical note from MTSamples.com for small cell
lung cancer (not NSCLC). The note mentions carboplatin/etoposide
chemotherapy, no biomarker testing, no ECOG PS, no ICD-10 code, and
the wrong cancer type for pembrolizumab eligibility.

Layer 1 FAILS with multiple gaps:
- Wrong cancer type (SCLC not NSCLC)
- No ICD-10 code
- No PD-L1 result
- No EGFR/ALK testing documented
- No ECOG PS

**Why this test exists:** Real clinical notes are not structured forms.
They are narrative documents that may omit required PA elements. Layer
1 must handle real note messiness, not just clean synthetic scenarios.

---

## Clinical safety behaviors built into the workflow

### PII before everything

A PA coordinator with 15 years of experience might instinctively type
"Patient: John Smith, MRN 987654, DOB 03/15/1964, PD-L1 60%, stage
IIIA NSCLC." The system catches this before any data leaves the server.
The rejection message names the specific PHI types found and explains
how to resubmit in de-identified form.

### Incomplete note stops the pipeline

Layer 2 never runs on an incomplete note. This is a deliberate design
decision. A PA system that evaluates NCCN criteria and returns APPROVED
on a note missing the ECOG PS has solved the wrong problem — the
submission will be denied by Cigna for missing documentation even if
the clinical criteria are met. Layer 1 must PASS before Layer 2 runs.

### Insufficient evidence is a valid verdict

If hybrid search returns a top chunk below the 0.70 similarity
threshold, the pipeline returns "INSUFFICIENT EVIDENCE" instead of
generating a verdict. In clinical PA, an unsupported approval is worse
than no answer — it creates false confidence in a submission that will
be denied.

### Citations on every criterion

Every Layer 2 criterion includes a source field with the NCCN guideline
version and page number. This serves two purposes: (1) the PA
coordinator can verify the criterion against the actual guideline, and
(2) the PA submission documentation can cite the specific guideline
version, which strengthens the appeal if the initial request is denied.

### Appeal flag on denials

When Layer 2 returns CRITERIA NOT MET, `appeal_recommended` is set to
true. For EGFR-positive cases, appeal is futile — the exclusion is
absolute. But for borderline cases — ECOG PS 2, PD-L1 45% — the appeal
flag prompts the coordinator to gather additional documentation before
the appeal rather than submitting the same incomplete record.
