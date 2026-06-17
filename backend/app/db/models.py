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
    forensic_result = relationship("ForensicResult", back_populates="document", uselist=False)
    ela_result = relationship("ELAResult", back_populates="document", uselist=False)
    noise_result = relationship("NoiseResult", back_populates="document", uselist=False)
    compression_result = relationship("CompressionResult", back_populates="document", uselist=False)
    fusion_result = relationship("FusionResult", back_populates="document", uselist=False)
    risk_assessment = relationship("DocumentRiskAssessment", back_populates="document", uselist=False)

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

class ForensicResult(Base):
    __tablename__ = "forensic_results"
    
    forensic_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="forensic_result")
    metadata_snapshot = relationship("MetadataSnapshot", back_populates="forensic_result", uselist=False)
    findings = relationship("ForensicFinding", back_populates="forensic_result")

class MetadataSnapshot(Base):
    __tablename__ = "metadata_snapshots"
    
    snapshot_id = Column(String, primary_key=True, default=generate_uuid)
    forensic_id = Column(String, ForeignKey("forensic_results.forensic_id"), unique=True)
    file_type = Column(String)  # image | pdf
    raw_metadata = Column(JSON)  # EXIF tags, PDF info dict
    
    forensic_result = relationship("ForensicResult", back_populates="metadata_snapshot")

class ForensicFinding(Base):
    __tablename__ = "forensic_findings"
    
    finding_id = Column(String, primary_key=True, default=generate_uuid)
    forensic_id = Column(String, ForeignKey("forensic_results.forensic_id"))
    signal_id = Column(String)  # S04, S05, S06, etc.
    finding_name = Column(String)
    severity = Column(String)  # INFO, LOW, MEDIUM, HIGH
    confidence = Column(Float)
    evidence = Column(JSON)  # Key-value evidence
    source = Column(String)  # EXIF, PDF_DICT, OCR_COMPARISON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    forensic_result = relationship("ForensicResult", back_populates="findings")

class ELAResult(Base):
    __tablename__ = "ela_results"
    
    ela_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="ela_result")
    heatmaps = relationship("ELAHeatmap", back_populates="ela_result")
    regions = relationship("ELARegion", back_populates="ela_result")
    findings = relationship("ELAFinding", back_populates="ela_result")

class ELAHeatmap(Base):
    __tablename__ = "ela_heatmaps"
    
    heatmap_id = Column(String, primary_key=True, default=generate_uuid)
    ela_id = Column(String, ForeignKey("ela_results.ela_id"))
    page_index = Column(Integer)
    ela_image_ref = Column(String)
    heatmap_image_ref = Column(String)
    
    ela_result = relationship("ELAResult", back_populates="heatmaps")

class ELARegion(Base):
    __tablename__ = "ela_regions"
    
    region_id = Column(String, primary_key=True, default=generate_uuid)
    ela_id = Column(String, ForeignKey("ela_results.ela_id"))
    page_index = Column(Integer)
    bbox = Column(JSON)  # [x, y, w, h]
    area = Column(Float)
    mean_intensity = Column(Float)
    max_intensity = Column(Float)
    
    ela_result = relationship("ELAResult", back_populates="regions")

class ELAFinding(Base):
    __tablename__ = "ela_findings"
    
    finding_id = Column(String, primary_key=True, default=generate_uuid)
    ela_id = Column(String, ForeignKey("ela_results.ela_id"))
    signal_id = Column(String, default="S06")
    finding_type = Column(String)
    severity = Column(String)
    confidence = Column(Float)
    bbox = Column(JSON)
    region_statistics = Column(JSON)
    heatmap_reference = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    ela_result = relationship("ELAResult", back_populates="findings")

class NoiseResult(Base):
    __tablename__ = "noise_results"
    
    noise_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="noise_result")
    maps = relationship("NoiseMap", back_populates="noise_result")
    regions = relationship("NoiseRegion", back_populates="noise_result")
    findings = relationship("NoiseFinding", back_populates="noise_result")

class NoiseMap(Base):
    __tablename__ = "noise_maps"
    
    map_id = Column(String, primary_key=True, default=generate_uuid)
    noise_id = Column(String, ForeignKey("noise_results.noise_id"))
    page_index = Column(Integer)
    map_type = Column(String)  # noise | texture | sharpness
    map_image_ref = Column(String)
    
    noise_result = relationship("NoiseResult", back_populates="maps")

class NoiseRegion(Base):
    __tablename__ = "noise_regions"
    
    region_id = Column(String, primary_key=True, default=generate_uuid)
    noise_id = Column(String, ForeignKey("noise_results.noise_id"))
    page_index = Column(Integer)
    bbox = Column(JSON)  # [x, y, w, h]
    region_type = Column(String) # noise_anomaly, texture_anomaly, sharpness_anomaly
    area = Column(Float)
    mean_value = Column(Float)
    max_value = Column(Float)
    
    noise_result = relationship("NoiseResult", back_populates="regions")

class NoiseFinding(Base):
    __tablename__ = "noise_findings"
    
    finding_id = Column(String, primary_key=True, default=generate_uuid)
    noise_id = Column(String, ForeignKey("noise_results.noise_id"))
    signal_id = Column(String, default="S07")
    finding_type = Column(String)
    severity = Column(String)
    confidence = Column(Float)
    bbox = Column(JSON)
    region_statistics = Column(JSON)
    supporting_signals = Column(JSON)
    heatmap_reference = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    noise_result = relationship("NoiseResult", back_populates="findings")

class CompressionResult(Base):
    __tablename__ = "compression_results"
    
    compression_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    document = relationship("Document", back_populates="compression_result")
    artifacts = relationship("CompressionArtifact", back_populates="compression_result")
    regions = relationship("CompressionRegion", back_populates="compression_result")
    findings = relationship("CompressionFinding", back_populates="compression_result")

class CompressionArtifact(Base):
    __tablename__ = "compression_artifacts"
    
    artifact_id = Column(String, primary_key=True, default=generate_uuid)
    compression_id = Column(String, ForeignKey("compression_results.compression_id"))
    page_index = Column(Integer)
    artifact_type = Column(String)  # block_map | heat_map | artifact_map
    artifact_image_ref = Column(String)
    
    compression_result = relationship("CompressionResult", back_populates="artifacts")

class CompressionRegion(Base):
    __tablename__ = "compression_regions"
    
    region_id = Column(String, primary_key=True, default=generate_uuid)
    compression_id = Column(String, ForeignKey("compression_results.compression_id"))
    page_index = Column(Integer)
    bbox = Column(JSON)  # [x, y, w, h]
    region_type = Column(String) # block_anomaly, double_compression, etc.
    area = Column(Float)
    mean_value = Column(Float)
    max_value = Column(Float)
    
    compression_result = relationship("CompressionResult", back_populates="regions")

class CompressionFinding(Base):
    __tablename__ = "compression_findings"
    
    finding_id = Column(String, primary_key=True, default=generate_uuid)
    compression_id = Column(String, ForeignKey("compression_results.compression_id"))
    signal_id = Column(String, default="S08")
    finding_type = Column(String)
    severity = Column(String)
    confidence = Column(Float)
    bbox = Column(JSON)
    compression_statistics = Column(JSON)
    supporting_signals = Column(JSON)
    artifact_reference = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    compression_result = relationship("CompressionResult", back_populates="findings")

class FusionResult(Base):
    __tablename__ = "fusion_results"
    
    fusion_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fusion_summary = Column(JSON)  # total_clusters, document_level_clusters, field_level_clusters, signal_breakdown
    
    document = relationship("Document", back_populates="fusion_result")
    clusters = relationship("EvidenceCluster", back_populates="fusion_result")

class EvidenceCluster(Base):
    __tablename__ = "evidence_clusters"
    
    cluster_id = Column(String, primary_key=True, default=generate_uuid)
    fusion_id = Column(String, ForeignKey("fusion_results.fusion_id"))
    cluster_type = Column(String)  # document_level | field_level | spatial
    affected_fields = Column(JSON)  # ["PAN Number"]
    signals = Column(JSON)  # ["S06", "S07", "S08"]
    primary_signal = Column(String)
    evidence_strength = Column(Float)  # 0.0 -> 1.0
    bbox = Column(JSON, nullable=True)  # Union bounding box
    investigator_summary = Column(String)
    
    fusion_result = relationship("FusionResult", back_populates="clusters")
    members = relationship("ClusterMember", back_populates="cluster")

class ClusterMember(Base):
    __tablename__ = "cluster_members"
    
    member_id = Column(String, primary_key=True, default=generate_uuid)
    cluster_id = Column(String, ForeignKey("evidence_clusters.cluster_id"))
    signal_id = Column(String)
    finding_id = Column(String)
    finding_type = Column(String)
    severity = Column(String)
    confidence = Column(Float)
    
    cluster = relationship("EvidenceCluster", back_populates="members")

class DocumentRiskAssessment(Base):
    __tablename__ = "document_risk_assessments"
    
    assessment_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.document_id"), unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    risk_score = Column(Float)  # 0 to 100
    risk_level = Column(String) # LOW, MODERATE, HIGH, CRITICAL
    
    executive_summary = Column(String)
    investigator_summary = Column(String)
    technical_summary = Column(String)
    
    document = relationship("Document", back_populates="risk_assessment")
    factors = relationship("RiskFactor", back_populates="assessment")
    critical_clusters = relationship("RiskContribution", back_populates="assessment")

class RiskFactor(Base):
    __tablename__ = "risk_factors"
    
    factor_id = Column(String, primary_key=True, default=generate_uuid)
    assessment_id = Column(String, ForeignKey("document_risk_assessments.assessment_id"))
    factor_name = Column(String)  # e.g. identity_field_tampering_risk
    contribution_score = Column(Float)
    description = Column(String)
    
    assessment = relationship("DocumentRiskAssessment", back_populates="factors")

class RiskContribution(Base):
    __tablename__ = "risk_contributions"
    
    contribution_id = Column(String, primary_key=True, default=generate_uuid)
    assessment_id = Column(String, ForeignKey("document_risk_assessments.assessment_id"))
    cluster_id = Column(String, ForeignKey("evidence_clusters.cluster_id"))
    
    risk_contribution_score = Column(Float)
    rank = Column(Integer)
    explanation = Column(String)
    
    assessment = relationship("DocumentRiskAssessment", back_populates="critical_clusters")
    cluster = relationship("EvidenceCluster")

