from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.db.models import Job
from backend.app.models.schemas import JobStatusResponse
from backend.app.core.schema_validator import SchemaValidator
from backend.app.core.exceptions import JobNotFoundError

router = APIRouter()

@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    response_data = {
        "schema_version": "1.0.0",
        "job_id": job.job_id,
        "applicant_id": job.applicant_id,
        "status": job.status,
        "stage": job.stage,
        "progress_pct": 100 if job.status in ["analyzed", "scored", "reported"] else (50 if job.status == "processing" else 0),
        "updated_at": job.updated_at,
        "error": job.error
    }
    
    # Error schema doesn't exist for job status per se in schemas, so we will not strictly validate unless it's ErrorResponse
    # But let's assume we don't have a status schema specifically in schemas directory, wait, the user asked to validate against Applicant, Document, DocumentPage, QualityProfile, Error
    # There is no status schema explicitly mentioned to validate against in task 10, but let's just return it.
    
    return response_data
