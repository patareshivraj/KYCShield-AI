import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import DocumentClassification, FusionResult, Document

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 9 EVIDENCE FUSION TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "fusion_test"})

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

# Wait for processing
time.sleep(18)

print("\n--- EVIDENCE CLUSTERS ---")

def print_fusion(doc_id):
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    cls = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc_id).first()
    fusion = db.query(FusionResult).filter(FusionResult.document_id == doc_id).first()
    
    if fusion:
        doc_type = cls.document_type if cls else "unknown"
        print(f"\nDocument: {doc_type}")
        print(f"Summary: {fusion.fusion_summary}")
        
        i = 1
        for cluster in fusion.clusters:
            print(f"\n  Cluster {i} ({cluster.cluster_type})")
            print(f"  Affected Fields: {cluster.affected_fields}")
            print(f"  Signals: {cluster.signals}")
            print(f"  Evidence Strength: {cluster.evidence_strength}")
            print(f"  Summary: {cluster.investigator_summary}")
            i += 1
            
    else:
        print(f"\nFusion failed for doc {doc_id}")

for did in doc_ids:
    print_fusion(did)
