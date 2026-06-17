# KYCShield AI - Phase 2 Test Strategy

## 1. Unit Tests
- **Intake Service:** Mock `UploadFile` and `db.add` to verify validation logic, MIME checks, and size limits. Ensure correct error raises for oversized or unsupported files.
- **Registry Service (Normalization):** Use dummy image and PDF files to ensure that PyMuPDF correctly rasterizes PDFs and Pillow correctly converts images to PNG. Assert the generation of `DocumentPage` records.
- **Quality Service (S00):** Feed deliberately blurred, low-resolution, and perfectly clear images into `QualityService`. Assert `pass`, `warn`, and `fail` gates on the `QualityProfile`.

## 2. Integration Tests
- **API Pipeline:** Using `TestClient`, simulate `POST /api/v1/applicants/upload` with valid files. Capture the `job_id`. Then poll `GET /api/v1/jobs/{job_id}/status`. Verify state transitions from `uploaded` -> `queued` -> `processing` -> `analyzed`.

## 3. Schema Validation Tests
- Mock valid and invalid responses (Applicant, Document, QualityProfile, Error) and pass them to `SchemaValidator`.
- Ensure JSON Schema strict compliance.

## 4. Normalization Tests
- Test edge cases: 20+ page PDFs (should cut off at limit), corrupted images (should gracefully fail), different color spaces (CMYK, RGBA).

## 5. Quality Assessment Tests
- Test `cv2.Laplacian` variance thresholds.
- Test extremely dark images (`mean_val < 50`) to ensure they fail exposure checks.

Run all tests via:
```bash
python -m pytest tests/
```
