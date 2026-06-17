import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Document, DocumentClassification

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 3 CLASSIFICATION ENGINE TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"
random_path = "tests/fixtures/cropped.jpg"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b, open(random_path, "rb") as r:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "classification_test"})
    
    # Upload random unknown document separately
    resp_unknown = client.post("/api/v1/applicants/upload", files={
        "pan": ("random.jpg", r, "image/jpeg")
    })

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

job_id_u = resp_unknown.json()["job_id"]
doc_ids_u = resp_unknown.json()["documents"]

# Wait for processing
time.sleep(5)

print("\n--- CLASSIFICATION RESULTS ---")

def print_classification(doc_id, expected_type):
    cls_model = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc_id).first()
    if cls_model:
        print(f"\nExpected: {expected_type}")
        print(f"System returned: {cls_model.document_type}")
        print(f"Confidence: {cls_model.confidence}")
        print(f"Evidence: {json.dumps(cls_model.signals, indent=2)}")
    else:
        print(f"\nClassification failed for {expected_type} (no DB record)")

print_classification(doc_ids[0], "aadhaar")
print_classification(doc_ids[1], "pan")
print_classification(doc_ids[2], "bank_statement")
print_classification(doc_ids_u[0], "unknown")
