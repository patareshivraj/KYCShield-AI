from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.schemas import SchemaBase

class ClassificationSignals(BaseModel):
    matched_keywords: List[str] = []
    matched_patterns: List[str] = []

class DocumentClassificationResponse(SchemaBase):
    classification_id: str
    document_id: str
    document_type: str
    confidence: float
    classifier_version: str
    signals: ClassificationSignals
    created_at: datetime
