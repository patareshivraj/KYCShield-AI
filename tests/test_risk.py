import os
import time
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import DocumentClassification, DocumentRiskAssessment, Document

client = TestClient(app)
db = SessionLocal()

print("--- PHASE 10 DOCUMENT RISK ENGINE TEST ---")

aadhaar_path = "ai_test_ds/ai_aadhaar.jpg"
pan_path = "ai_test_ds/ai_pan.jpg"
bank_path = "ai_test_ds/ai_bank_statement.pdf"

with open(aadhaar_path, "rb") as a, open(pan_path, "rb") as p, open(bank_path, "rb") as b:
    resp = client.post("/api/v1/applicants/upload", files={
        "aadhaar": ("ai_aadhaar.jpg", a, "image/jpeg"),
        "pan": ("ai_pan.jpg", p, "image/jpeg"),
        "bank_statement": ("ai_bank_statement.pdf", b, "application/pdf")
    }, data={"external_reference": "risk_test"})

job_id = resp.json()["job_id"]
doc_ids = resp.json()["documents"]

# Wait for processing
time.sleep(20)

print("\n--- RISK ASSESSMENTS ---")

def print_risk(doc_id):
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    cls = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc_id).first()
    risk = db.query(DocumentRiskAssessment).filter(DocumentRiskAssessment.document_id == doc_id).first()
    
    if risk:
        doc_type = cls.document_type if cls else "unknown"
        print(f"\nDocument: {doc_type}")
        print(f"Risk Score: {risk.risk_score}")
        print(f"Risk Level: {risk.risk_level}")
        print(f"Executive Summary: {risk.executive_summary}")
        
        print("\nTop Drivers:")
        print(f"  {risk.investigator_summary}")
        
        print("\nCritical Clusters:")
        for idx, cc in enumerate(risk.critical_clusters[:3]):
            print(f"  {idx+1}. Score: {cc.risk_contribution_score:.2f} - {cc.explanation}")
            
        print("\nRisk Factors:")
        for rf in risk.factors:
            print(f"  * {rf.factor_name} ({rf.contribution_score:.2f})")
            
    else:
        print(f"\nRisk assessment failed for doc {doc_id}")

for did in doc_ids:
    print_risk(did)
