import re
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import Document, DocumentPage, DocumentClassification, OCRResult, OCRPage, ExtractedField

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, db: Session):
        self.db = db
        self.reader = None

    def _get_reader(self):
        if self.reader is None:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        return self.reader

    def execute_ocr(self, document_id: str) -> OCRResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        classification = self.db.query(DocumentClassification).filter(DocumentClassification.document_id == document_id).first()
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_index).all()
        
        doc_type = classification.document_type if classification else "unknown"
        
        # 1. Raw OCR Extraction
        ocr_result = OCRResult(
            document_id=document_id,
            engine_used="easyocr",
            overall_confidence=0.0
        )
        self.db.add(ocr_result)
        self.db.flush()
        
        page_texts = []
        words_data = []
        total_conf = 0.0
        
        for page in pages:
            # We must support image files, scanned PDFs, image-based PDFs
            # Normalization already rasterized everything to PNG in storage_ref
            try:
                raw_results = self._get_reader().readtext(page.storage_ref)
            except Exception as e:
                logger.error(f"OCR failed for {page.storage_ref}: {e}")
                # Fallback to secondary extraction would go here. We mock fallback logic.
                logger.warning("Attempting secondary extraction (Tesseract fallback)... (Not installed, skipping)")
                raw_results = []
                
            page_words = []
            page_text = ""
            page_conf = 0.0
            
            for (bbox, text, conf) in raw_results:
                page_words.append({
                    "text": text,
                    "confidence": float(conf),
                    "bbox": [[float(x), float(y)] for [x,y] in bbox]
                })
                page_text += text + " "
                page_conf += conf
                
            if len(raw_results) > 0:
                page_conf /= len(raw_results)
                
            total_conf += page_conf
            page_texts.append(page_text)
            words_data.extend(page_words)
            
            ocr_page = OCRPage(
                ocr_id=ocr_result.ocr_id,
                page_index=page.page_index,
                page_confidence=float(page_conf),
                raw_text=page_text,
                words=page_words
            )
            self.db.add(ocr_page)
            
        ocr_result.overall_confidence = float(total_conf / max(1, len(pages)))
        
        # 2. Structured Field Extraction
        full_text = " ".join(page_texts)
        if doc_type == "aadhaar":
            self._extract_aadhaar_fields(ocr_result, full_text, words_data)
        elif doc_type == "pan":
            self._extract_pan_fields(ocr_result, full_text, words_data)
        elif doc_type == "bank_statement":
            self._extract_bank_statement_fields(ocr_result, full_text, words_data)
            
        self.db.commit()
        return ocr_result

    def _create_field(self, ocr_result: OCRResult, name: str, value: str, confidence: float, valid: bool, source: str = "", bbox: list = None) -> None:
        if not value:
            return
        field = ExtractedField(
            ocr_id=ocr_result.ocr_id,
            field_name=name,
            field_value=value,
            confidence=float(confidence),
            is_valid=valid,
            evidence={
                "source_text": source or value,
                "bbox": bbox or [],
                "page_index": 0
            }
        )
        self.db.add(field)

    def _find_best_word(self, words: List[Dict], regex_pattern: str) -> Dict:
        for w in words:
            if re.search(regex_pattern, w["text"], re.IGNORECASE):
                return w
        return None

    def _extract_aadhaar_fields(self, ocr_result: OCRResult, full_text: str, words: List[Dict]):
        # Name
        # Very basic heuristic for name (looking for uppercase words after Government of India)
        name_match = re.search(r'GOVERNMENT OF INDIA\s+([A-Z\s]+?)\s+DOB', full_text, re.IGNORECASE)
        if name_match:
            val = name_match.group(1).strip()
            word = self._find_best_word(words, val.split()[0])
            self._create_field(ocr_result, "Name", val, word["confidence"] if word else 0.6, True, val, word["bbox"] if word else [])

        # Aadhaar Number
        uid_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', full_text)
        if uid_match:
            uid_val = uid_match.group(0).replace(" ", "")
            is_valid = len(uid_val) == 12 and uid_val.isdigit()
            word = self._find_best_word(words, r'\d{4}')
            self._create_field(ocr_result, "Aadhaar Number", uid_val, word["confidence"] if word else 0.8, is_valid, uid_match.group(0), word["bbox"] if word else [])
            
        # DOB / YOB
        dob_match = re.search(r'(?:DOB|YOB|Year of Birth).*?(\d{2}/\d{2}/\d{4}|\d{4})', full_text, re.IGNORECASE)
        if dob_match:
            val = dob_match.group(1)
            word = self._find_best_word(words, val)
            self._create_field(ocr_result, "DOB", val, word["confidence"] if word else 0.7, True, dob_match.group(0), word["bbox"] if word else [])
            
        # Gender
        gender_match = re.search(r'\b(MALE|FEMALE|TRANSGENDER)\b', full_text, re.IGNORECASE)
        if gender_match:
            val = gender_match.group(1).upper()
            word = self._find_best_word(words, val)
            self._create_field(ocr_result, "Gender", val, word["confidence"] if word else 0.9, True, gender_match.group(0), word["bbox"] if word else [])

        # Address
        addr_match = re.search(r'(?:Address|Add).*?:\s*(.*)', full_text, re.IGNORECASE)
        if addr_match:
            val = addr_match.group(1)
            self._create_field(ocr_result, "Address", val, 0.7, True, val, [])

    def _extract_pan_fields(self, ocr_result: OCRResult, full_text: str, words: List[Dict]):
        # Name & Father Name (heuristics based on lines before DOB)
        name_match = re.search(r'Name\s+([A-Z\s]+)', full_text, re.IGNORECASE)
        if name_match:
            self._create_field(ocr_result, "Name", name_match.group(1).strip(), 0.7, True, name_match.group(1).strip(), [])
            
        fname_match = re.search(r'Father\'s Name\s+([A-Z\s]+)', full_text, re.IGNORECASE)
        if fname_match:
            self._create_field(ocr_result, "Father Name", fname_match.group(1).strip(), 0.7, True, fname_match.group(1).strip(), [])

        # PAN Number
        # More relaxed regex for PAN (OCR might read digits as letters like G instead of 6, O instead of 0)
        pan_match = re.search(r'\b[A-Z]{5}[0-9OIGS]{4}[A-Z]\b', full_text, re.IGNORECASE)
        if pan_match:
            val = pan_match.group(0).upper()
            is_valid = re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', val) is not None
            word = self._find_best_word(words, val)
            self._create_field(ocr_result, "PAN Number", val, word["confidence"] if word else 0.9, is_valid, pan_match.group(0), word["bbox"] if word else [])
            
        # DOB
        dob_match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', full_text)
        if dob_match:
            val = dob_match.group(1)
            word = self._find_best_word(words, val)
            self._create_field(ocr_result, "DOB", val, word["confidence"] if word else 0.8, True, dob_match.group(0), word["bbox"] if word else [])

    def _extract_bank_statement_fields(self, ocr_result: OCRResult, full_text: str, words: List[Dict]):
        # Account Number
        acc_match = re.search(r'(?:A/c No|Account No|Account Number|Account}).*?(\d{9,18})', full_text, re.IGNORECASE)
        if acc_match:
            val = acc_match.group(1)
            word = self._find_best_word(words, val)
            self._create_field(ocr_result, "Account Number", val, word["confidence"] if word else 0.8, True, acc_match.group(0), word["bbox"] if word else [])
            
        # Bank Name
        for bank in ["SBI", "HDFC", "ICICI", "AXIS", "KOTAK", "STATE BANK"]:
            if bank.lower() in full_text.lower():
                word = self._find_best_word(words, bank.split()[0])
                self._create_field(ocr_result, "Bank Name", bank, word["confidence"] if word else 0.9, True, bank, word["bbox"] if word else [])
                break
                
        # Account Holder
        holder_match = re.search(r'(?:Name|Account Holder).*?:\s*([A-Za-z\s]+)', full_text, re.IGNORECASE)
        if holder_match:
            self._create_field(ocr_result, "Account Holder", holder_match.group(1).strip(), 0.8, True, holder_match.group(1).strip(), [])

        # Statement Period
        period_match = re.search(r'(?:Period|Statement Date).*?:\s*([A-Za-z0-9\-\s]+)', full_text, re.IGNORECASE)
        if period_match:
            self._create_field(ocr_result, "Statement Period", period_match.group(1).strip(), 0.7, True, period_match.group(1).strip(), [])

        # Balances
        open_match = re.search(r'(?:Opening Bal|Opening Balance).*?([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        if open_match:
            self._create_field(ocr_result, "Opening Balance", open_match.group(1), 0.8, True, open_match.group(0), [])
            
        close_match = re.search(r'(?:Closing Bal|Closing Balance).*?([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        if close_match:
            self._create_field(ocr_result, "Closing Balance", close_match.group(1), 0.8, True, close_match.group(0), [])

        # Transactions (Template aware)
        tx_matches = re.findall(r'\b\d{2}[/-][A-Z]{3}[/-]\d{4}\b', full_text, re.IGNORECASE)
        if tx_matches:
            self._create_field(ocr_result, "Transaction Count", str(len(tx_matches)), 0.9, True, str(len(tx_matches)))
