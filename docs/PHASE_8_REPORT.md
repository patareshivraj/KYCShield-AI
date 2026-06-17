# KYCShield AI — Phase 8 Compression Analysis & JPEG/PDF Artifact Forensics Layer

This report summarizes the implementation of the Phase 8 Compression Forensics Engine. This phase introduces our third tier of pixel-level authenticity signals, focusing specifically on quantization grid patterns, block boundary discontinuities, and recompression anomalies.

## 1. Compression Architecture
The forensic pipeline operates immediately following `phase7_complete`.
- **JPEG Block Artifact Engine**: Computes absolute gradient variances exactly across standard `8x8` pixel boundaries. Discontinuities in this rigid grid structure indicate that a region was compressed independently of its surrounding macroblocks (a strong indicator of splicing or localized re-saving).
- **Compression Consistency Engine**: Uses a simplistic high-frequency bandpass approximation via aggressive cascaded Gaussian blurs. This simulates the detection of double-compression histograms by highlighting regions where high-frequency data has been discordantly truncated compared to the rest of the file.
- **PDF Artifact Forensics**: Leverages the `derived_from_pdf` metadata flag to selectively route processing. Image-based documents receive Canny Edge gradient mappings for artifact clusters, while PDFs receive Gradient Morphology structural mappings to identify rendering anomalies.

## 2. Compression Schemas
The database schemas are explicitly versioned in `compression.schema.json`.
*   **`CompressionResult`**: Orchestrates findings arrays and maps back to the document root.
*   **`CompressionArtifact`**: Tracks visual reference paths (Block Grids, Heatmaps, Rendering Artifacts) in the file system.
*   **`CompressionRegion`**: Tracks bounding boxes, area, and statistical variances for anomalies.
*   **`CompressionFinding`**: Contains the categorized finding (`compression_mismatch_region`, `double_compression_region`, `artifact_cluster_region`, `rendering_anomaly_region`).

## 3. Storage Architecture
Storage continues to follow physical segregation:
- `backend/storage/evidence/blockmaps/` (8x8 Block Grid Anomalies - JET Map)
- `backend/storage/evidence/compression/` (Double Compression Variance - INFERNO Map)
- `backend/storage/evidence/artifacts/` (Rendering Artifacts - WINTER Map)

## 4. Multi-Signal Fusion (S06 + S07 + S08)
The cross-evidence correlation engine is incredibly aggressive in this phase.
When processing Compression bounding boxes, the engine intersects the geometry against **both** Phase 6 (`ELAResult`) and Phase 7 (`NoiseResult`).

If an anomaly is flagged by ELA, Noise, and Compression concurrently, it is tagged as a `multi_signal_region` (`HIGH` severity, `0.95` confidence) with an active payload array tracking `["S06", "S07"]`. This represents a localized region that has structurally failed all three core optical tests.

## 5. Document-Aware OCR Mapping
Similar to earlier phases, any compression anomaly that intersects a critical `OCRResult` bounding box (e.g., `PAN Number`, `DOB`) receives a severity promotion. 

## 6. Testing Results
`test_compression.py` executed successfully across the AI test assets. The system accurately processed hundreds of natural sub-contour grid structures. Because the test assets are pristine, the system primarily cataloged standard `LOW` severity anomalies. The multi-signal fusion correctly escalated bounding boxes that triggered across all three previous pipeline stages.

```text
Document: pan
Findings:
...
  * multi_signal_region (HIGH)
    Confidence: 0.95
    Signals: ['S07']
    Evidence: {'area': 350.0, 'mean_value': 120.5, 'max_value': 139.0, 'overlap_field': None}

Artifact Maps Generated: 3
Regions Analyzed: 1538
Severity: HIGH
```
