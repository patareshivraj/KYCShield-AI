import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Document, OCRResult

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 4 OCR & STRUCTURED FIELD EXTRACTION TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "ocr_test"})

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

# Wait for processing
time.sleep(8)

print("\n--- EXTRACTION RESULTS ---")

def print_ocr_result(doc_id, expected_type):
    ocr_model = db.query(OCRResult).filter(OCRResult.document_id == doc_id).first()
    if ocr_model:
        print(f"\nDocument Type: {expected_type}")
        print(f"Overall Confidence: {ocr_model.overall_confidence}")
        print("Extracted Fields:")
        for field in ocr_model.fields:
            print(f"  - {field.field_name}: {field.field_value}")
            print(f"    Confidence: {field.confidence}, Valid: {field.is_valid}")
            print(f"    Evidence: {field.evidence}")
    else:
        print(f"\nOCR failed for {expected_type} (no DB record)")

print_ocr_result(doc_ids[0], "aadhaar")
print_ocr_result(doc_ids[1], "pan")
print_ocr_result(doc_ids[2], "bank_statement")
