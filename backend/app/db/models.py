from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Applicant(Base):
    __tablename__ = "applicants"
    
    applicant_id = Column(String, primary_key=True, default=generate_uuid)
    external_reference = Column(String, nullable=True)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    documents = relationship("Document", back_populates="applicant")
    jobs = relationship("Job", back_populates="applicant")

class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True, default=generate_uuid)
    applicant_id = Column(String, ForeignKey("applicants.applicant_id"))
    status = Column(String, default="queued")
    stage = Column(String, nullable=True)
    error = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    applicant = relationship("Applicant", back_populates="jobs")

class Document(Base):
    __tablename__ = "documents"
    
    document_id = Column(String, primary_key=True, default=generate_uuid)
    applicant_id = Column(String, ForeignKey("applicants.applicant_id"))
    document_type = Column(String)  # aadhaar | pan | bank_statement
    bank_id = Column(String, nullable=True)
    source_format = Column(String)
    source_checksum_sha256 = Column(String)
    source_path = Column(String)
    page_count = Column(Integer, default=1)
    file_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    applicant = relationship("Applicant", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document")
    quality_profile = relationship("QualityProfile", back_populates="document", uselist=False)
    classification = relationship("DocumentClassification", back_populates="document", uselist=False)
    ocr_result = relationship("OCRResult", back_populates="document", uselist=False)

class DocumentPage(Base):
    __tablename__ = "document_pages"
    
    page_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"))
    page_index = Column(Integer)
    width_px = Column(Integer)
    height_px = Column(Integer)
    dpi_estimate = Column(Integer, nullable=True)
    storage_ref = Column(String)
    derived_from_pdf = Column(Boolean, default=False)
    
    document = relationship("Document", back_populates="pages")

class QualityProfile(Base):
    __tablename__ = "quality_profiles"
    
    profile_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    overall_gate = Column(String)  # pass | warn | fail
    overall_score = Column(Float)
    metrics = Column(JSON)
    confidence_cap_tier_c = Column(Float, default=1.0)
    limitations = Column(String, nullable=True)
    
    document = relationship("Document", back_populates="quality_profile")

class DocumentClassification(Base):
    __tablename__ = "document_classifications"
    
    classification_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    document_type = Column(String)  # aadhaar | pan | bank_statement | unknown
    confidence = Column(Float)
    classifier_version = Column(String, default="1.0.0")
    signals = Column(JSON)  # {matched_keywords: [], matched_patterns: []}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="classification")

class OCRResult(Base):
    __tablename__ = "ocr_results"
    
    ocr_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    engine_used = Column(String)
    overall_confidence = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="ocr_result")
    pages = relationship("OCRPage", back_populates="ocr_result")
    fields = relationship("ExtractedField", back_populates="ocr_result")

class OCRPage(Base):
    __tablename__ = "ocr_pages"
    
    ocr_page_id = Column(String, primary_key=True, default=generate_uuid)
    ocr_id = Column(String, ForeignKey("ocr_results.ocr_id"))
    page_index = Column(Integer)
    page_confidence = Column(Float)
    raw_text = Column(String)
    words = Column(JSON)  # List of dicts with text, bbox, confidence
    
    ocr_result = relationship("OCRResult", back_populates="pages")

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    
    field_id = Column(String, primary_key=True, default=generate_uuid)
    ocr_id = Column(String, ForeignKey("ocr_results.ocr_id"))
    field_name = Column(String)
    field_value = Column(String)
    confidence = Column(Float)
    is_valid = Column(Boolean, default=True)
    evidence = Column(JSON)  # {source_text, bbox, page_index}
    
    ocr_result = relationship("OCRResult", back_populates="fields")
