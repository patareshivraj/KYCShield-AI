from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.db.session import get_db
from backend.app.db.models import (
    Applicant, Document, DocumentPage, Job, OCRResult, DocumentRiskAssessment, EvidenceCluster,
    CompressionArtifact, NoiseMap, ELAResult, ForensicResult
)
import os

router = APIRouter()

@router.get("/applicants", response_model=List[Dict[str, Any]])
def list_applicants(db: Session = Depends(get_db)):
    applicants = db.query(Applicant).order_by(Applicant.created_at.desc()).all()
    results = []
    for app in applicants:
        latest_job = db.query(Job).filter(Job.applicant_id == app.applicant_id).order_by(Job.created_at.desc()).first()
        results.append({
            "applicant_id": app.applicant_id,
            "external_reference": app.external_reference,
            "created_at": app.created_at,
            "job_status": latest_job.status if latest_job else "unknown",
            "job_stage": latest_job.stage if latest_job else "unknown"
        })
    return results

@router.get("/applicants/{applicant_id}", response_model=Dict[str, Any])
def get_applicant(applicant_id: str, db: Session = Depends(get_db)):
    app = db.query(Applicant).filter(Applicant.applicant_id == applicant_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Applicant not found")
        
    docs = db.query(Document).filter(Document.applicant_id == applicant_id).all()
    
    doc_results = []
    for doc in docs:
        risk = db.query(DocumentRiskAssessment).filter(DocumentRiskAssessment.document_id == doc.document_id).first()
        doc_results.append({
            "document_id": doc.document_id,
            "document_type": doc.document_type,
            "original_filename": doc.original_filename,
            "risk_score": risk.risk_score if risk else None,
            "risk_level": risk.risk_level if risk else "UNKNOWN"
        })
        
    return {
        "applicant_id": app.applicant_id,
        "external_reference": app.external_reference,
        "created_at": app.created_at,
        "documents": doc_results
    }

@router.get("/documents/{document_id}", response_model=Dict[str, Any])
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    risk = db.query(DocumentRiskAssessment).filter(DocumentRiskAssessment.document_id == document_id).first()
    ocr = db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
    
    clusters = []
    if doc.fusion_result:
        for c in doc.fusion_result.clusters:
            clusters.append({
                "cluster_id": c.cluster_id,
                "cluster_type": c.cluster_type,
                "affected_fields": c.affected_fields,
                "signals": c.signals,
                "evidence_strength": c.evidence_strength,
                "bbox": c.bbox,
                "investigator_summary": c.investigator_summary
            })
            
    risk_data = None
    if risk:
        risk_data = {
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "executive_summary": risk.executive_summary,
            "investigator_summary": risk.investigator_summary,
            "critical_clusters": [{"score": rc.risk_contribution_score, "explanation": rc.explanation} for rc in risk.critical_clusters],
            "factors": [{"name": rf.factor_name, "score": rf.contribution_score} for rf in risk.factors]
        }
        
    return {
        "document_id": doc.document_id,
        "document_type": doc.document_type,
        "risk": risk_data,
        "ocr_fields": [{"name": f.field_name, "value": f.field_value, "confidence": f.confidence, "bbox": f.evidence.get("bbox") if f.evidence else None} for f in ocr.fields] if ocr else [],
        "clusters": clusters
    }

@router.get("/documents/{document_id}/image")
def get_document_image(document_id: str, db: Session = Depends(get_db)):
    page = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_index).first()
    if not page or not page.storage_ref or not os.path.exists(page.storage_ref):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(page.storage_ref)

@router.get("/documents/{document_id}/artifacts/{artifact_type}")
def get_document_artifact(document_id: str, artifact_type: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    path = None
    if artifact_type == "ela" and doc.ela_result and doc.ela_result.heatmap_reference:
        path = doc.ela_result.heatmap_reference
    elif artifact_type == "noise" and doc.noise_result and doc.noise_result.maps:
        noise_map = next((m for m in doc.noise_result.maps if m.map_type == "median_noise"), None)
        if noise_map: path = noise_map.map_reference
    elif artifact_type == "compression" and doc.compression_result and doc.compression_result.artifacts:
        heat_map = next((a for a in doc.compression_result.artifacts if a.artifact_type == "heat_map"), None)
        if heat_map: path = heat_map.artifact_image_ref
        
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    return FileResponse(path)
