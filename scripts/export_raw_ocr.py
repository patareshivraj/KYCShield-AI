import os
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.db.models import OCRPage, DocumentClassification, OCRResult, Document

db = SessionLocal()

print("# Raw OCR Text Baseline\n")

# Get latest OCRResults for each document type
docs = db.query(Document).join(DocumentClassification).all()

extracted_data = {}

for doc in docs:
    cls = doc.classification
    if not cls: continue
    doc_type = cls.document_type
    
    ocr = db.query(OCRResult).filter(OCRResult.document_id == doc.document_id).order_by(OCRResult.created_at.desc()).first()
    if not ocr: continue
    
    pages = db.query(OCRPage).filter(OCRPage.ocr_id == ocr.ocr_id).order_by(OCRPage.page_index).all()
    full_text = " ".join([p.raw_text for p in pages])
    
    extracted_data[doc_type] = full_text

for dtype in ["aadhaar", "pan", "bank_statement"]:
    print(f"## {dtype.upper()}\n")
    print(f"```text\n{extracted_data.get(dtype, 'Not found')}\n```\n")

