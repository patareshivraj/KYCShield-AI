import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import DocumentClassification, ForensicResult, Document

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 5 METADATA & FILE FORENSICS TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "forensics_test"})

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

# Wait for processing
time.sleep(8)

print("\n--- FORENSICS RESULTS ---")

def print_forensics(doc_id):
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    cls = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc_id).first()
    forensic = db.query(ForensicResult).filter(ForensicResult.document_id == doc_id).first()
    
    if forensic:
        doc_type = cls.document_type if cls else "unknown"
        print(f"\nDocument: {doc_type}")
        print(f"File Type: {forensic.metadata_snapshot.file_type}")
        print("Findings:")
        
        max_sev = "INFO"
        sevs = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        for finding in forensic.findings:
            print(f"  * {finding.finding_name} ({finding.severity})")
            print(f"    Evidence: {finding.evidence}")
            if sevs[finding.severity] > sevs[max_sev]:
                max_sev = finding.severity
                
        print(f"\nSeverity: {max_sev}")
    else:
        print(f"\nForensics failed for doc {doc_id}")

for did in doc_ids:
    print_forensics(did)
