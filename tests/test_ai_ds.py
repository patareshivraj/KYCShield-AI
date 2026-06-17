import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Applicant, Document, QualityProfile

client = TestClient(app)
db = SessionLocal()

print("--- TESTING WITH AI_TEST_DS ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "ai_test_ds_run"})

upload_data = resp.json()
print("Upload Status Code:", resp.status_code)
print("Upload Response:", json.dumps(upload_data, indent=2))

if resp.status_code != 201:
    print("Upload failed. Exiting.")
    exit(1)

job_id = upload_data["job_id"]
doc_ids = upload_data["documents"]

# Wait for background task to process the files
time.sleep(3)

status_resp = client.get(f"/api/v1/jobs/{job_id}/status")
print("\nJob Status:", json.dumps(status_resp.json(), indent=2))

print("\n--- QUALITY PROFILES FOR UPLOADED DOCUMENTS ---")
for doc_id in doc_ids:
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    if not doc:
        continue
    
    qp = db.query(QualityProfile).filter(QualityProfile.document_id == doc_id).first()
    
    print(f"\nDocument Type: {doc.document_type}")
    print(f"Source: {doc.source_format}")
    print(f"Pages Normalized: {doc.page_count}")
    
    if qp:
        print("Quality Gate:", qp.overall_gate)
        print("Overall Score:", qp.overall_score)
        print("Detailed Metrics:", json.dumps(qp.metrics, indent=2))
    else:
        print("QualityProfile not found for this document.")
