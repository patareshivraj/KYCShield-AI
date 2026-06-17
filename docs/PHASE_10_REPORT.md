# KYCShield AI — Phase 10 Document Risk Engine Layer

This report summarizes the implementation of the Phase 10 Document Risk Engine. This engine consumes the deterministic forensic evidence clusters from Phase 9 and transforms them into an auditable, enterprise-ready risk assessment—proving why a document is flagged without relying on "black box" deep learning models.

## 1. Risk Architecture Principles
The engine was built strictly to enforce the principle: **Risk derives from Evidence. Evidence never derives from Risk.**
It does not have access to raw `S06`, `S07`, or `S08` findings. It is forced to query the `EvidenceCluster` relations, ensuring that any risk point it generates is guaranteed to be explainable by the Phase 9 cluster that produced it.

## 2. Risk Calculation Engine
The scoring logic operates without any machine learning. It relies on a rigorous configuration framework:

- **Field Importance Framework**: Assigns weights to OCR fields based on identity value.
  - `PAN Number` / `Aadhaar Number` / `Account Number` = 1.0 (Critical Identity Fields)
  - `DOB` / `Photo` / `Transaction Count` = 0.8 (Secondary Identity)
  - Margins / Backgrounds = 0.2 (Low Importance)

- **Signal Weighting**: Determines the structural reliability of a signal family.
  - `S08` (Compression) = 0.9
  - `S06` (ELA), `S07` (Noise) = 0.8
  - `S04` / `S05` (Metadata) = 0.4 / 0.5

The **Cluster Risk Contribution** formula dynamically combines the Evidence Strength from Phase 9, the Field Importance, the Signal Weight, and a bonus for signal diversity (e.g., S07 + S08 occurring together).

## 3. Explainability Layer
To ensure the system is "Investigator Ready", the engine does not just emit a `Risk Score`. It generates:
1.  **Risk Level**: `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
2.  **Top Drivers**: An array of the highest-risk textual explanations.
3.  **Critical Clusters**: A sorted list (`rank`) of the clusters that mathematically contributed the most risk to the document, complete with contribution scores.
4.  **Risk Factors**: Categorical indicators mapped automatically, such as `identity_field_tampering_risk` or `financial_data_modification_risk`.

## 4. Database Integration
Schemas are defined in `risk.schema.json`.
*   **`DocumentRiskAssessment`**: The root schema holding the 0-100 score and high-level summaries.
*   **`RiskFactor`**: The categories (e.g., `identity_field_tampering_risk`) and their total score allocations.
*   **`RiskContribution`**: The critical edge mapping the exact numeric risk points back to the responsible `cluster_id` from Phase 9.

## 5. Testing Results
`test_risk.py` processed all Phase 9 Evidence Clusters. The results demonstrate the engine's capability to explain its decisions dynamically:

```text
Document: pan
Risk Score: 61.575
Risk Level: HIGH
Executive Summary: Document exhibits HIGH risk. Multiple independent forensic anomalies affecting key fields.

Top Drivers:
  Multiple forensic signals (S08, S07, S06) overlap the PAN Number, DOB field; ...

Critical Clusters:
  1. Score: 36.38 - Multiple forensic signals (S08, S07, S06) overlap the PAN Number, DOB field
  2. Score: 7.20 - Multiple forensic signals (S07) overlap the DOB field

Risk Factors:
  * metadata_anomaly_risk (0.80)
  * identity_field_tampering_risk (57.98)
  * compression_anomaly_risk (2.80)
```

The system successfully recognized that the `PAN Number` cluster carried far more risk (Score: 36.38) than the `DOB` noise cluster (Score: 7.20), correctly ranking them for the investigator and rolling up the exact totals into `identity_field_tampering_risk`.

We are now in `phase10_complete`. The Document Risk Engine is operational.
