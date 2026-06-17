import os
import fitz  # PyMuPDF
from PIL import Image
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.models import Document, DocumentPage

class RegistryService:
    def __init__(self, db: Session):
        self.db = db

    def normalize_documents(self, job_id: str):
        # Get applicant for job
        from backend.app.db.models import Job
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return
            
        docs = self.db.query(Document).filter(Document.applicant_id == job.applicant_id).all()
        for doc in docs:
            self._normalize_document(doc)
        
        self.db.commit()

    def _normalize_document(self, doc: Document):
        if doc.source_format == "pdf":
            self._normalize_pdf(doc)
        else:
            self._normalize_image(doc)

    def _normalize_pdf(self, doc: Document):
        doc2 = fitz.open(doc.source_path)
        doc.page_count = len(doc2)
        
        for i in range(len(doc2)):
            if i >= settings.MAX_PDF_PAGES:
                break
                
            page = doc2.load_page(i)
            pix = page.get_pixmap(dpi=300)
            
            page_id = f"{doc.document_id}_p{i}"
            out_path = os.path.join(settings.STORAGE_DIR, "normalized", f"{page_id}.png")
            pix.save(out_path)
            
            doc_page = DocumentPage(
                document_id=doc.document_id,
                page_index=i,
                width_px=pix.width,
                height_px=pix.height,
                dpi_estimate=300,
                storage_ref=out_path,
                derived_from_pdf=True
            )
            self.db.add(doc_page)

    def _normalize_image(self, doc: Document):
        doc.page_count = 1
        with Image.open(doc.source_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
                
            page_id = f"{doc.document_id}_p0"
            out_path = os.path.join(settings.STORAGE_DIR, "normalized", f"{page_id}.png")
            img.save(out_path, "PNG")
            
            doc_page = DocumentPage(
                document_id=doc.document_id,
                page_index=0,
                width_px=img.width,
                height_px=img.height,
                dpi_estimate=img.info.get('dpi', (300, 300))[0],
                storage_ref=out_path,
                derived_from_pdf=False
            )
            self.db.add(doc_page)
