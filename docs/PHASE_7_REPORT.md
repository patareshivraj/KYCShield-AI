# KYCShield AI — Phase 7 Noise Consistency & Local Texture Forensics Layer

This report summarizes the implementation of the Phase 7 Noise Forensics Engine. This phase introduces our second tier of pixel-level authenticity signals, extracting structural manipulation artifacts through advanced high-pass filtering and statistical gradient analysis.

## 1. Noise Architecture
The forensic pipeline operates immediately following `phase6_complete`.
- **Noise Residual Engine**: Uses Median Filtering (`cv2.medianBlur`) paired with an absolute difference matrix to extract high-frequency structural noise residuals. Unaltered images possess a uniform noise blanket; spliced or cloned areas exhibit harsh localized discrepancies.
- **Local Texture Engine**: Uses Sobel operators (`cv2.Sobel`) to compute the gradient magnitude across horizontal and vertical channels, generating a texture variance map.
- **Sharpness Engine**: Uses Laplacian Variance (`cv2.Laplacian`) to isolate over-sharpened or unnaturally blurred insertions.

## 2. Noise Schemas
The database schemas are explicitly versioned in `noise.schema.json`.
*   **`NoiseResult`**: Orchestrates findings arrays and maps back to the document root.
*   **`NoiseMap`**: Tracks visual reference paths (Median Noise, Texture Magnitude, Laplacian Sharpness) in the file system.
*   **`NoiseRegion`**: A high-performance metadata array tracking bounding boxes, area, mean value, and max value for isolated anomalous zones.
*   **`NoiseFinding`**: Contains the final categorized finding (`noise_mismatch_region`, `texture_mismatch_region`, `sharpness_mismatch_region`).

## 3. Storage Architecture
Storage follows standard artifact segregation:
- `backend/storage/evidence/noise/` (Median Filter Residuals - BONE Map)
- `backend/storage/evidence/textures/` (Gradient Magnitude - VIRIDIS Map)
- `backend/storage/evidence/sharpness/` (Laplacian Variance - HOT Map)

## 4. Document-Aware Mapping (OCR Overlap)
The system retrieves Phase 4 `OCRResult` bounding boxes. It computationally intersects Noise Region bounding boxes with OCR Text bounding boxes.
- **If overlap occurs**: Confidence increases `+0.2`.
- **If target is Critical (PAN/Aadhaar/DOB/Account Number)**: Severity upgrades to `HIGH`. Confidence hard-caps to `0.95`.

## 5. Cross-Evidence Correlation
The engine directly imports `ELAFinding` objects generated during Phase 6. 
- **If an ELA bounding box and a Noise bounding box overlap**: The finding upgrades to `multi_signal_region`.
- This represents a compounded forensic signal, immediately elevating the Severity to `HIGH`.

## 6. Testing Results
`test_noise.py` executed successfully across all test assets. 

The threshold logic detected natural fluctuations (especially near text) resulting in multiple `LOW` severity anomalies. Crucially, the system mapped regions against OCR and ELA outputs, proving the correlation architecture works as intended for future Risk Engine deployment.

```text
Document: bank_statement
Findings:
...
  * sharpness_mismatch_region (LOW)
    Confidence: 0.6
    Signals: []
    Evidence: {'area': 22.0, 'mean_value': 78.4, 'max_value': 108.0, 'overlap_field': None}
...
Maps Generated: 3
Regions Analyzed: 2363
Severity: HIGH
```
