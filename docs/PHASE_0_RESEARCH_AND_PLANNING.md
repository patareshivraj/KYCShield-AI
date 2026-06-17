# Phase 0 — Research & Planning (Signed Off)

**Status:** APPROVED  
**Date:** 2026-06-17

The complete Phase 0 research document is maintained at:

[`.cursor/plans/kycshield_phase_0_859f4c65.plan.md`](../.cursor/plans/kycshield_phase_0_859f4c65.plan.md)

## Frozen Decisions (Summary)

| Area | Decision |
|---|---|
| Product framing | Trustworthiness assessment — not identity verification |
| Documents | Aadhaar, PAN, Bank Statement (SBI, HDFC, ICICI, Axis, Kotak only) |
| Formats | JPG, JPEG, PNG, PDF |
| Pipeline | S00 Quality → OCR → Forensics → Structural → Applicant Fusion → Scoring → Report |
| S00 | Document Quality Assessment — P0 gate before OCR/forensics |
| Constraints | OSS-first, local-first, no cloud/gov APIs, no face/deepfake/AML |
| Risk model | Evidence fusion; no "AI says fake"; bands: Low / Review / High / Inconclusive |
| Fraud taxonomy | Visual, Metadata, Content, Layout, Synthetic Generation |

## Phase 1 Dependency

Architecture and contracts: [PHASE_1_ARCHITECTURE_AND_SYSTEM_DESIGN.md](./PHASE_1_ARCHITECTURE_AND_SYSTEM_DESIGN.md)
