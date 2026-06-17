import os
import json
from datetime import datetime, timezone
from PIL import Image, ExifTags
import fitz
from sqlalchemy.orm import Session
from backend.app.db.models import Document, DocumentPage, ForensicResult, MetadataSnapshot, ForensicFinding, OCRResult

class MetadataForensicsService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_document(self, document_id: str) -> ForensicResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        forensic_result = ForensicResult(document_id=document_id)
        self.db.add(forensic_result)
        self.db.flush()
        
        file_path = doc.source_path
        ext = os.path.splitext(file_path)[1].lower()
        
        raw_metadata = {}
        file_type = "unknown"
        
        if ext in ['.jpg', '.jpeg', '.png']:
            file_type = "image"
            raw_metadata = self._extract_image_metadata(file_path)
            self._analyze_image_metadata(forensic_result, raw_metadata)
        elif ext == '.pdf':
            file_type = "pdf"
            raw_metadata = self._extract_pdf_metadata(file_path)
            self._analyze_pdf_metadata(forensic_result, raw_metadata)
            
        snapshot = MetadataSnapshot(
            forensic_id=forensic_result.forensic_id,
            file_type=file_type,
            raw_metadata=raw_metadata
        )
        self.db.add(snapshot)
        
        # Consistency checks across OCR and Metadata
        self._analyze_consistency(forensic_result, doc)
        
        self.db.commit()
        return forensic_result

    def _extract_image_metadata(self, file_path: str) -> dict:
        metadata = {}
        try:
            with Image.open(file_path) as img:
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                metadata["size"] = list(img.size)
                
                exifdata = img.getexif()
                if exifdata:
                    exif_dict = {}
                    for tag_id in exifdata:
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        data = exifdata.get(tag_id)
                        # Handle bytes
                        if isinstance(data, bytes):
                            try:
                                data = data.decode('utf-8', errors='ignore')
                            except:
                                data = "<binary>"
                        exif_dict[str(tag)] = str(data)
                    metadata["exif"] = exif_dict
                else:
                    metadata["exif"] = {}
        except Exception as e:
            metadata["error"] = str(e)
        return metadata

    def _extract_pdf_metadata(self, file_path: str) -> dict:
        metadata = {}
        try:
            with fitz.open(file_path) as doc:
                metadata["page_count"] = doc.page_count
                metadata["is_encrypted"] = doc.is_encrypted
                metadata["metadata"] = doc.metadata
                
                # Check for embedded fonts
                fonts = []
                for i in range(doc.page_count):
                    for font in doc.get_page_fonts(i):
                        fonts.append(font[3])
                metadata["fonts"] = list(set(fonts))
                
        except Exception as e:
            metadata["error"] = str(e)
        return metadata

    def _add_finding(self, forensic_result: ForensicResult, signal_id: str, name: str, severity: str, evidence: dict, source: str, conf: float = 1.0):
        finding = ForensicFinding(
            forensic_id=forensic_result.forensic_id,
            signal_id=signal_id,
            finding_name=name,
            severity=severity,
            confidence=conf,
            evidence=evidence,
            source=source
        )
        self.db.add(finding)

    def _analyze_image_metadata(self, forensic_result: ForensicResult, metadata: dict):
        exif = metadata.get("exif", {})
        
        if not exif:
            self._add_finding(forensic_result, "S04", "missing_metadata", "MEDIUM", {"details": "No EXIF data found."}, "EXIF")
            return
            
        software = exif.get("Software", "").lower()
        if not software:
            self._add_finding(forensic_result, "S04", "missing_software_metadata", "INFO", {"details": "Software EXIF tag missing."}, "EXIF")
        else:
            suspicious_software = ["photoshop", "gimp", "canva", "paint", "illustrator"]
            for sus in suspicious_software:
                if sus in software:
                    self._add_finding(forensic_result, "S04", "editing_software_detected", "HIGH", {"software": exif.get("Software")}, "EXIF")

        # Creation vs Modification dates
        datetime_orig = exif.get("DateTimeOriginal")
        datetime_mod = exif.get("DateTime")
        if datetime_orig and datetime_mod and datetime_orig != datetime_mod:
            self._add_finding(forensic_result, "S04", "metadata_inconsistent", "LOW", {"orig": datetime_orig, "mod": datetime_mod}, "EXIF")

    def _analyze_pdf_metadata(self, forensic_result: ForensicResult, metadata: dict):
        pdf_meta = metadata.get("metadata", {})
        producer = pdf_meta.get("producer", "").lower()
        creator = pdf_meta.get("creator", "").lower()
        
        if not producer and not creator:
            self._add_finding(forensic_result, "S05", "missing_metadata", "MEDIUM", {"details": "PDF has no producer or creator."}, "PDF_DICT")
            
        suspicious_producers = ["canva", "photoshop", "illustrator", "word", "libreoffice", "reportlab"]
        detected = False
        
        for sus in suspicious_producers:
            if sus in producer or sus in creator:
                detected = True
                self._add_finding(forensic_result, "S05", "editing_software_detected", "MEDIUM", {"producer": pdf_meta.get("producer"), "creator": pdf_meta.get("creator")}, "PDF_DICT")
                break
                
        if not detected and producer:
            self._add_finding(forensic_result, "S05", "producer_detected", "INFO", {"producer": pdf_meta.get("producer")}, "PDF_DICT")
            
        if metadata.get("is_encrypted"):
            self._add_finding(forensic_result, "S05", "unexpected_pdf_structure", "LOW", {"details": "PDF is encrypted"}, "PDF_DICT")

    def _analyze_consistency(self, forensic_result: ForensicResult, doc: Document):
        ocr = self.db.query(OCRResult).filter(OCRResult.document_id == doc.document_id).first()
        if not ocr:
            return
            
        # Example OCR vs Metadata consistency logic
        # if Document Type is Bank Statement and OCR has Period matching 2021 but PDF was created in 2026
        # This requires robust date parsing, so we implement a placeholder logic for now
        
        pass
