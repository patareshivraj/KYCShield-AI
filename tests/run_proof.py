import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Applicant, Document, DocumentPage, QualityProfile

client = TestClient(app)

print("--- TEST 1: Normal Upload ---")
with open("tests/fixtures/Aadhaar.pdf", "rb") as a, open("tests/fixtures/PAN.jpg", "rb") as p, open("tests/fixtures/BankStatement.pdf", "rb") as b:
    resp1 = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("Aadhaar.pdf", a, "application/pdf"),
        "pan": ("PAN.jpg", p, "image/jpeg"),
        "bank_statement": ("BankStatement.pdf", b, "application/pdf")
    })
print("Upload Response:", json.dumps(resp1.json(), indent=2))
job_id = resp1.json().get("job_id")

# Wait for background tasks
time.sleep(2)

resp1_status = client.get(f"/api/v1/jobs/{job_id}/status")
print("\nStatus Response:", json.dumps(resp1_status.json(), indent=2))

print("\n--- TEST 2: 20 MB File ---")
with open("tests/fixtures/large.pdf", "rb") as f:
    resp2 = client.post("/api/v1/applicants/upload", files={"aadhaar": ("large.pdf", f, "application/pdf")})
print("Large File Response:", resp2.json())

print("\n--- TEST 3: Executable File ---")
with open("tests/fixtures/malicious.exe", "rb") as f:
    resp3 = client.post("/api/v1/applicants/upload", files={"aadhaar": ("malicious.exe", f, "application/x-msdownload")})
print("Exe File Response:", resp3.json())

print("\n--- TEST 4: Rotated Image ---")
with open("tests/fixtures/rotated.jpg", "rb") as f:
    resp4 = client.post("/api/v1/applicants/upload", files={"pan": ("rotated.jpg", f, "image/jpeg")})
time.sleep(1)
db = SessionLocal()
doc_id = resp4.json()["documents"][0]
qp = db.query(QualityProfile).filter(QualityProfile.document_id == doc_id).first()
if qp:
    print("Rotated Image Quality Profile Metrics:", json.dumps(qp.metrics["rotation"], indent=2))

print("\n--- TEST 5: Cropped Image ---")
with open("tests/fixtures/cropped.jpg", "rb") as f:
    resp5 = client.post("/api/v1/applicants/upload", files={"pan": ("cropped.jpg", f, "image/jpeg")})
time.sleep(1)
doc_id_crop = resp5.json()["documents"][0]
qp_crop = db.query(QualityProfile).filter(QualityProfile.document_id == doc_id_crop).first()
if qp_crop:
    print("Cropped Image Quality Profile Metrics:", json.dumps(qp_crop.metrics["crop_completeness"], indent=2))

print("\n--- DATABASE PROOF ---")
apps = db.query(Applicant).count()
docs = db.query(Document).count()
pages = db.query(DocumentPage).count()
qps = db.query(QualityProfile).count()
print(f"Applicants: {apps}, Documents: {docs}, Pages: {pages}, QualityProfiles: {qps}")

print("\n--- STORAGE DIRECTORY PROOF ---")
for root, dirs, files in os.walk("backend/storage"):
    print(f"{root}/ ({len(files)} files)")
