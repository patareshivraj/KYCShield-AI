# KYCShield AI — Evaluation Dataset Corpus

**Phase 1:** Structure and schemas only. No real PII samples committed.

## Purpose

Offline labeled corpus for harness benchmarking against Phase 0 success metrics (M1–M9).

## Categories

| Directory | Purpose |
|---|---|
| `clean/` | Legitimate documents (synthetic or licensed) |
| `tampered/` | Known edits with labeled regions |
| `synthetic/` | AI/template-generated fakes |
| `cross_doc_mismatch/` | Multi-document packages with intentional inconsistency |
| `quality_failures/` | S00 stress cases (blur, WhatsApp recompression, etc.) |

## Sample Layout

Single document:

```text
{tier}/{document_type}/sample_XXX/
├── {file}.pdf|jpg
├── metadata.json
└── ground_truth.json
```

Applicant package (`cross_doc_mismatch/packages/`):

```text
pkg_XXX/
├── aadhaar.jpg
├── pan.jpg
├── statement.pdf
├── metadata.json
└── ground_truth.json
```

## Schemas

- Sample metadata: see Phase 1 doc Section 12.2
- Ground truth: [`ground_truth.schema.json`](./ground_truth.schema.json)

## Ethics

- Never commit real customer PII
- Use synthetic or explicitly licensed samples
- Document consent in `metadata.json`

## Bank Statement Subfolders

Under `clean/bank_statement/` and equivalents:

`sbi/`, `hdfc/`, `icici/`, `axis/`, `kotak/`
