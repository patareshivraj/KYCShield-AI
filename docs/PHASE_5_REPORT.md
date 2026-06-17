# KYCShield AI — Phase 5 Metadata & File Forensics Layer

This report summarizes the implementation of the Phase 5 Metadata Forensics Engine. This phase generates the first layers of authentic forensic risk signals by isolating metadata traits without declaring absolute fraud verdicts.

## 1. Metadata Architecture
The forensic pipeline operates immediately following `phase4_complete`. The engine intercepts the uploaded raw binaries (`source_path`), routes to specific parser extensions based on the `file_type`, and then maps findings to dedicated forensic signal schemas.
*   **Images (JPG/PNG)**: `Pillow (PIL)` extracts and sanitizes raw EXIF metadata into JSON-safe dictionaries.
*   **Documents (PDF)**: `PyMuPDF (fitz)` intercepts embedded Object Dictionaries, extracting structural tags and embedded font data.

## 2. Forensics Schemas
The database persistence is fully decoupled into 3 tables linked via one-to-one UUID structures to `Document`. All schemas are explicitly declared in `forensics.schema.json`.
*   **`ForensicResult`**: Orchestrates `findings` arrays and traces `document_id`.
*   **`MetadataSnapshot`**: Persists the raw dictionary output of EXIF/PDF traits for audit-logging and future Phase 6 access.
*   **`ForensicFinding`**: Granular evidence schema logging `signal_id`, `severity`, `finding_name`, and isolated `evidence`.

## 3. Metadata Extraction Logic
*   **Image Mode**: Recursively reads `img.getexif()`, gracefully casting byte-level anomalies to `<binary>` or decoding them iteratively.
*   **PDF Mode**: Extracts `doc.metadata`, explicit Page Counts, and scrapes embedded binary fonts via `doc.get_page_fonts()`.

## 4. Detection Rules
*   **Editing Software Detection**: Identifies string permutations associated with known synthetic rendering paths: `[canva, photoshop, gimp, illustrator, word, libreoffice, reportlab]`. Triggered on EXIF `Software` headers or PDF `producer`/`creator` tags.
*   **Missing Data Checks**: Flags documents completely devoid of standardized camera EXIFs or valid PDF Producers.

## 5. Evidence Framework & Reserved Signals
In accordance with the architectural recommendation, all signals now map to reserved namespaces:
*   `S04`: Metadata Forensics (Image EXIF/Headers)
*   `S05`: PDF Forensics (Structural Producers)
*   `S06` - `S08`: Reserved for future Image/Pixel engines.

Each `ForensicFinding` adheres to the strict evidence output spec:
```json
{
  "signal_id": "S04",
  "finding_name": "editing_software_detected",
  "severity": "HIGH",
  "evidence": {"software": "Adobe Photoshop CC"},
  "source": "EXIF",
  "confidence": 1.0
}
```

## 6. Database Changes
*   Added `ForensicResult`, `MetadataSnapshot`, and `ForensicFinding` SQLAlchemy configurations.
*   Updated `Document` table to enable `forensic_result = relationship(...)`.

## 7. API Changes
`JobOrchestrator` triggers `forensics_svc.analyze_document()` synchronously. It gracefully executes the extraction sequence and resolves the job entity state to `"stage": "phase5_complete"`.

## 8. Test Results
The acceptance test `test_forensics.py` was executed across all three simulated document paths. Because the underlying mock inputs (`ai_test_ds/`) were built devoid of physical EXIF strings (synthetic nature), the engine accurately and deterministically detected the data absence.

## 9. Acceptance Results
```text
Document: aadhaar
File Type: image
Findings:
  * missing_metadata (MEDIUM)
    Evidence: {'details': 'No EXIF data found.'}

Severity: MEDIUM

Document: pan
File Type: image
Findings:
  * missing_metadata (MEDIUM)
    Evidence: {'details': 'No EXIF data found.'}

Severity: MEDIUM

Document: bank_statement
File Type: pdf
Findings:
  * missing_metadata (MEDIUM)
    Evidence: {'details': 'PDF has no producer or creator.'}

Severity: MEDIUM
```
