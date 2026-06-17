from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.services.intake import IntakeService
from backend.app.core.orchestrator import JobOrchestrator

def get_intake_service(db: Session = Depends(get_db)) -> IntakeService:
    return IntakeService(db)

def get_orchestrator(db: Session = Depends(get_db)) -> JobOrchestrator:
    return JobOrchestrator(db)
