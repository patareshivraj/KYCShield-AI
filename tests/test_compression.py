import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import DocumentClassification, CompressionResult, Document

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 8 COMPRESSION FORENSICS TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "compression_test"})

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

# Wait for processing
time.sleep(15)

print("\n--- COMPRESSION RESULTS ---")

def print_compression(doc_id):
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    cls = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc_id).first()
    comp = db.query(CompressionResult).filter(CompressionResult.document_id == doc_id).first()
    
    if comp:
        doc_type = cls.document_type if cls else "unknown"
        print(f"\nDocument: {doc_type}")
        
        print("Findings:")
        max_sev = "INFO"
        sevs = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        for finding in comp.findings:
            print(f"  * {finding.finding_type} ({finding.severity})")
            print(f"    Confidence: {finding.confidence}")
            print(f"    Signals: {finding.supporting_signals}")
            print(f"    Evidence: {finding.compression_statistics}")
            if sevs[finding.severity] > sevs[max_sev]:
                max_sev = finding.severity
                
        print(f"\nArtifact Maps Generated: {len(comp.artifacts)}")
        print(f"Regions Analyzed: {len(comp.regions)}")
        print(f"Severity: {max_sev}")
    else:
        print(f"\nCompression analysis failed for doc {doc_id}")

for did in doc_ids:
    print_compression(did)
