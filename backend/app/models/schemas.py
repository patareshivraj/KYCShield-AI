from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SchemaBase(BaseModel):
    schema_version: str = "1.0.0"
    model_config = ConfigDict(from_attributes=True)

class DocumentIds(BaseModel):
    aadhaar: Optional[str] = None
    pan: Optional[str] = None
    bank_statement: Optional[str] = None

class Completeness(BaseModel):
    aadhaar: bool = False
    pan: bool = False
    bank_statement: bool = False
    missing: List[str] = []

class ApplicantResponse(SchemaBase):
    applicant_id: str
    external_reference: Optional[str] = None
    job_id: str
    status: str
    documents: List[str]
    completeness: Completeness
    created_at: datetime
    updated_at: datetime

class JobStatusResponse(SchemaBase):
    job_id: str
    applicant_id: str
    status: str
    stage: Optional[str] = None
    progress_pct: int = 0
    updated_at: datetime
    error: Optional[Dict[str, Any]] = None

class ErrorResponse(SchemaBase):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
