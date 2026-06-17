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
            
            # Stop here for Phase 2 scope
            self._update_state(job, "analyzed", "phase2_complete")
            
        except Exception as e:
            logger.exception("Job failed")
            job.status = "failed"
            job.error = {"message": str(e)}
            self.db.commit()

    def _update_state(self, job: Job, status: str, stage: str):
        job.status = status
        job.stage = stage
        self.db.commit()
