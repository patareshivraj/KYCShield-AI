import logging
from sqlalchemy.orm import Session
from backend.app.db.models import Job
from backend.app.services.registry import RegistryService
from backend.app.services.quality import QualityService

logger = logging.getLogger(__name__)

class JobOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.registry = RegistryService(db)
        self.quality = QualityService(db)

    def process_job_sync(self, job_id: str):
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return
            
        try:
            # Transition to processing
            self._update_state(job, "processing", "normalization")
            
            # Run Normalization
            self.registry.normalize_documents(job_id)
            
            # Run S00 Quality
            self._update_state(job, "processing", "quality")
            self.quality.assess_job(job_id)
            
            # Classification Phase
            self._update_state(job, "processing", "classification")
            from backend.app.services.classification import DocumentClassifier
            classifier = DocumentClassifier(self.db)
            
            from backend.app.db.models import Document
            docs = self.db.query(Document).filter(Document.applicant_id == job.applicant_id).all()
            for doc in docs:
                classifier.classify_document(doc.document_id)
                
            # OCR Extraction Phase
            self._update_state(job, "processing", "ocr")
            from backend.app.services.ocr import OCRService
            ocr_svc = OCRService(self.db)
            for doc in docs:
                ocr_svc.execute_ocr(doc.document_id)
                
            # Forensics Phase
            self._update_state(job, "processing", "forensics")
            from backend.app.services.forensics import MetadataForensicsService
            forensics_svc = MetadataForensicsService(self.db)
            for doc in docs:
                forensics_svc.analyze_document(doc.document_id)
                
            # ELA Phase
            self._update_state(job, "processing", "ela")
            from backend.app.services.ela import ELAForensicsService
            ela_svc = ELAForensicsService(self.db)
            for doc in docs:
                ela_svc.analyze_document(doc.document_id)
                
            # Noise Forensics Phase
            self._update_state(job, "processing", "noise")
            from backend.app.services.noise import NoiseForensicsService
            noise_svc = NoiseForensicsService(self.db)
            for doc in docs:
                noise_svc.analyze_document(doc.document_id)
            
            # Job Complete
            job.status = "analyzed"
            job.stage = "phase7_complete"
            job.progress_pct = 100
            self.db.commit()
            
        except Exception as e:
            logger.exception("Job failed")
            job.status = "failed"
            job.error = {"message": str(e)}
            self.db.commit()

    def _update_state(self, job: Job, status: str, stage: str):
        job.status = status
        job.stage = stage
        self.db.commit()
