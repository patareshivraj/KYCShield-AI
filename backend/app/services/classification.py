import re
import cv2
import logging
from typing import Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from backend.app.db.models import Document, DocumentPage, DocumentClassification

logger = logging.getLogger(__name__)

class DocumentClassifier:
    def __init__(self, db: Session):
        self.db = db
        self.reader = None

    def _get_reader(self):
        if self.reader is None:
            import easyocr
            # Load only english for faster execution
            self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        return self.reader

    def classify_document(self, document_id: str) -> DocumentClassification:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_index).all()
        
        full_text = ""
        for page in pages:
            # Use PyMuPDF if it's a PDF to get perfectly accurate text quickly
            page_text = ""
            if doc.source_format.lower() == 'pdf':
                try:
                    import fitz
                    pdf_doc = fitz.open(doc.source_path)
                    if page.page_index < len(pdf_doc):
                        pdf_page = pdf_doc[page.page_index]
                        page_text = pdf_page.get_text().strip()
                except Exception as e:
                    logger.warning(f"Failed to extract text via fitz for {doc.source_path}: {e}")
            
            # If no text was extracted (e.g. image-based PDF) or it's an image, use OCR
            if not page_text:
                try:
                    result = self._get_reader().readtext(page.storage_ref, detail=0)
                    page_text = " ".join(result)
                except Exception as e:
                    logger.warning(f"Failed to extract text via OCR for {page.storage_ref}: {e}")
                    
            full_text += page_text.upper() + " "
        
        doc_type, confidence, signals = self._apply_rules(full_text)
        
        classification = DocumentClassification(
            document_id=doc.document_id,
            document_type=doc_type,
            confidence=confidence,
            signals=signals
        )
        self.db.add(classification)
        self.db.flush()
        return classification

    def _apply_rules(self, text: str) -> Tuple[str, float, Dict[str, Any]]:
        # Check Aadhaar
        aadhaar_kws = ["AADHAAR", "GOVERNMENT OF INDIA", "UNIQUE IDENTIFICATION"]
        matched_a = [kw for kw in aadhaar_kws if kw in text]
        
        # Check PAN
        pan_kws = ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER"]
        matched_p = [kw for kw in pan_kws if kw in text]
        
        # Check Bank Statement
        bank_kws = ["STATEMENT", "OPENING BAL", "CLOSING BAL", "ACCOUNT"]
        matched_b = [kw for kw in bank_kws if kw in text]
        bank_ids = ["SBI", "HDFC", "ICICI", "AXIS", "KOTAK", "STATE BANK"]
        matched_b_ids = [kw for kw in bank_ids if kw in text]
        
        # Patterns
        uid_pattern = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
        pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]'
        
        matched_a_pats = []
        if re.search(uid_pattern, text):
            matched_a_pats.append("12-digit UID")
            
        matched_p_pats = []
        if re.search(pan_pattern, text):
            matched_p_pats.append("PAN regex")
            
        scores = {
            "aadhaar": (len(matched_a) * 0.3) + (0.4 if matched_a_pats else 0),
            "pan": (len(matched_p) * 0.4) + (0.5 if matched_p_pats else 0),
            "bank_statement": (len(matched_b) * 0.2) + (len(matched_b_ids) * 0.3)
        }
        
        best_class = max(scores, key=scores.get)
        best_score = scores[best_class]
        
        # If no strong signals
        if best_score < 0.4:
            return "unknown", 0.0, {"matched_keywords": [], "matched_patterns": []}
            
        signals = {"matched_keywords": [], "matched_patterns": []}
        if best_class == "aadhaar":
            signals["matched_keywords"] = matched_a
            signals["matched_patterns"] = matched_a_pats
        elif best_class == "pan":
            signals["matched_keywords"] = matched_p
            signals["matched_patterns"] = matched_p_pats
        elif best_class == "bank_statement":
            signals["matched_keywords"] = matched_b + matched_b_ids
            signals["matched_patterns"] = []
            
        confidence = min(1.0, best_score)
        return best_class, confidence, signals
