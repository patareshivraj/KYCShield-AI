from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.api.dependencies import get_intake_service, get_orchestrator, get_db
from backend.app.services.intake import IntakeService
from backend.app.core.orchestrator import JobOrchestrator
from backend.app.models.schemas import ApplicantResponse
from backend.app.core.schema_validator import SchemaValidator

router = APIRouter()

@router.post("/upload", response_model=ApplicantResponse, status_code=201)
async def upload_documents(
    background_tasks: BackgroundTasks,
    aadhaar: Optional[UploadFile] = File(None),
    pan: Optional[UploadFile] = File(None),
    bank_statement: Optional[UploadFile] = File(None),
    external_reference: Optional[str] = Form(None),
    intake: IntakeService = Depends(get_intake_service),
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    db: Session = Depends(get_db)
):
    app_id, job_id, docs, missing = intake.process_upload(
        aadhaar=aadhaar,
        pan=pan,
        bank_statement=bank_statement,
        external_ref=external_reference
    )
    
    # Trigger background processing
    background_tasks.add_task(orchestrator.process_job_sync, job_id)
    
    # Fetch from db for timestamps
    from backend.app.db.models import Applicant
    applicant = db.query(Applicant).filter(Applicant.applicant_id == app_id).first()
    
    response_data = {
        "schema_version": "1.0.0",
        "applicant_id": app_id,
        "job_id": job_id,
        "documents": list(docs.values()),
        "status": "queued",
        "completeness": {
            "aadhaar": "aadhaar" in docs,
            "pan": "pan" in docs,
            "bank_statement": "bank_statement" in docs,
            "missing": missing
        },
        "created_at": applicant.created_at.isoformat(),
        "updated_at": applicant.updated_at.isoformat()
    }
    if applicant.external_reference:
        response_data["external_reference"] = applicant.external_reference
    
    # Validate against schema
    validated = SchemaValidator.validate_response("applicant", response_data)
    return validated
