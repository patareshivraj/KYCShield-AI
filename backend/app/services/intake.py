import os
import hashlib
import uuid
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.exceptions import ValidationError, UnsupportedFormatError
from backend.app.db.models import Applicant, Job, Document

class IntakeService:
    def __init__(self, db: Session):
        self.db = db

    def process_upload(self, aadhaar: UploadFile, pan: UploadFile, bank_statement: UploadFile, external_ref: str):
        # Create applicant and job
        applicant = Applicant(external_reference=external_ref)
        self.db.add(applicant)
        self.db.flush()
        
        job = Job(applicant_id=applicant.applicant_id)
        self.db.add(job)
        self.db.flush()
        
        uploads = {
            "aadhaar": aadhaar,
            "pan": pan,
            "bank_statement": bank_statement
        }
        
        doc_ids = {}
        missing = []
        
        for doc_type, file in uploads.items():
            if not file:
                missing.append(doc_type)
                continue
                
            self._validate_file(file)
            doc = self._store_and_create_document(file, doc_type, applicant.applicant_id)
            doc_ids[doc_type] = doc.document_id
            
        self.db.commit()
        
        return applicant.applicant_id, job.job_id, doc_ids, missing

    def _validate_file(self, file: UploadFile):
        if file.content_type not in settings.ALLOWED_MIME_TYPES:
            raise UnsupportedFormatError(f"MIME type {file.content_type} not supported")
        
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > settings.MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"File size exceeds limit of {settings.MAX_FILE_SIZE_BYTES} bytes")

    def _store_and_create_document(self, file: UploadFile, doc_type: str, applicant_id: str) -> Document:
        ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'bin'
        source_id = str(uuid.uuid4())
        source_path = os.path.join(settings.STORAGE_DIR, "source", f"{source_id}.{ext}")
        
        sha256 = hashlib.sha256()
        with open(source_path, "wb") as buffer:
            while chunk := file.file.read(8192):
                sha256.update(chunk)
                buffer.write(chunk)
        
        doc = Document(
            applicant_id=applicant_id,
            document_type=doc_type,
            source_format=ext,
            source_checksum_sha256=sha256.hexdigest(),
            source_path=source_path,
            page_count=1  # Will be updated by Registry
        )
        self.db.add(doc)
        self.db.flush()
        return doc
