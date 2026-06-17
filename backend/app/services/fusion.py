from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.models import (
    Document, ForensicResult, ELAResult, NoiseResult, CompressionResult,
    FusionResult, EvidenceCluster, ClusterMember, OCRResult
)

class EvidenceFusionService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_document(self, document_id: str) -> FusionResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        fusion_result = FusionResult(document_id=document_id)
        self.db.add(fusion_result)
        self.db.flush()
        
        # 1. Evidence Collection
        findings = self._collect_findings(document_id)
        
        # 2. Document-Level / Metadata Clustering
        self._cluster_metadata(fusion_result, findings)
        
        # 3. Spatial and Field-Aware Clustering
        self._cluster_spatial(fusion_result, findings, document_id)
        
        # 4. Generate Summary
        self._generate_summary(fusion_result)
        
        self.db.commit()
        return fusion_result

    def _collect_findings(self, document_id: str):
        findings = []
        
        forensic = self.db.query(ForensicResult).filter(ForensicResult.document_id == document_id).first()
        if forensic and forensic.findings:
            for f in forensic.findings:
                findings.append({"id": f.finding_id, "signal_id": f.signal_id, "type": f.finding_name, "severity": f.severity, "confidence": f.confidence, "bbox": None, "obj": f})
                
        ela = self.db.query(ELAResult).filter(ELAResult.document_id == document_id).first()
        if ela and ela.findings:
            for f in ela.findings:
                findings.append({"id": f.finding_id, "signal_id": f.signal_id, "type": f.finding_type, "severity": f.severity, "confidence": f.confidence, "bbox": f.bbox, "obj": f})
                
        noise = self.db.query(NoiseResult).filter(NoiseResult.document_id == document_id).first()
        if noise and noise.findings:
            for f in noise.findings:
                findings.append({"id": f.finding_id, "signal_id": f.signal_id, "type": f.finding_type, "severity": f.severity, "confidence": f.confidence, "bbox": f.bbox, "obj": f})
                
        comp = self.db.query(CompressionResult).filter(CompressionResult.document_id == document_id).first()
        if comp and comp.findings:
            for f in comp.findings:
                findings.append({"id": f.finding_id, "signal_id": f.signal_id, "type": f.finding_type, "severity": f.severity, "confidence": f.confidence, "bbox": f.bbox, "obj": f})
                
        return findings

    def _cluster_metadata(self, fusion_result, findings):
        meta_findings = [f for f in findings if f["signal_id"] in ["S04", "S05"]]
        if not meta_findings:
            return
            
        cluster = EvidenceCluster(
            fusion_id=fusion_result.fusion_id,
            cluster_type="document_level",
            affected_fields=[],
            signals=list(set(f["signal_id"] for f in meta_findings)),
            primary_signal="S04" if any(f["signal_id"] == "S04" for f in meta_findings) else "S05",
            evidence_strength=self._calculate_strength(meta_findings),
            investigator_summary="Document-level metadata and file structure anomalies detected."
        )
        self.db.add(cluster)
        self.db.flush()
        
        for mf in meta_findings:
            self.db.add(ClusterMember(
                cluster_id=cluster.cluster_id, signal_id=mf["signal_id"], finding_id=mf["id"], finding_type=mf["type"], severity=mf["severity"], confidence=mf["confidence"]
            ))

    def _cluster_spatial(self, fusion_result, findings, document_id):
        spatial_findings = [f for f in findings if f["signal_id"] in ["S06", "S07", "S08"] and f["bbox"]]
        
        # Spatial clustering based on bbox intersection
        clusters = []
        for sf in spatial_findings:
            added = False
            for c in clusters:
                if self._bboxes_overlap(c["bbox"], sf["bbox"]):
                    c["findings"].append(sf)
                    c["bbox"] = self._union_bbox(c["bbox"], sf["bbox"])
                    added = True
                    break
            if not added:
                clusters.append({"bbox": sf["bbox"], "findings": [sf]})
                
        # Get OCR fields
        ocr = self.db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
        
        for c in clusters:
            affected_fields = []
            if ocr and ocr.fields:
                for field in ocr.fields:
                    f_box = field.evidence.get("bbox") if field.evidence else None
                    if f_box and len(f_box) == 4:
                        fx1 = min(p[0] for p in f_box)
                        fy1 = min(p[1] for p in f_box)
                        fx2 = max(p[0] for p in f_box)
                        fy2 = max(p[1] for p in f_box)
                        
                        f_bbox = [fx1, fy1, fx2, fy2]
                        if self._bboxes_overlap(c["bbox"], f_bbox):
                            affected_fields.append(field.field_name)
                            
            signals = list(set(f["signal_id"] for f in c["findings"]))
            
            cluster_type = "field_level" if affected_fields else "spatial"
            strength = self._calculate_strength(c["findings"])
            
            if len(affected_fields) > 0:
                summary = f"Multiple independent forensic signals ({', '.join(signals)}) overlap the {', '.join(affected_fields)} region."
            else:
                summary = f"Spatial anomaly detected with signals: {', '.join(signals)}."
                
            cluster = EvidenceCluster(
                fusion_id=fusion_result.fusion_id,
                cluster_type=cluster_type,
                affected_fields=list(set(affected_fields)),
                signals=signals,
                primary_signal=signals[0] if signals else None,
                evidence_strength=strength,
                bbox=c["bbox"],
                investigator_summary=summary
            )
            self.db.add(cluster)
            self.db.flush()
            
            for sf in c["findings"]:
                self.db.add(ClusterMember(
                    cluster_id=cluster.cluster_id, signal_id=sf["signal_id"], finding_id=sf["id"], finding_type=sf["type"], severity=sf["severity"], confidence=sf["confidence"]
                ))

    def _bboxes_overlap(self, b1, b2):
        return not (b1[2] < b2[0] or b1[0] > b2[2] or b1[3] < b2[1] or b1[1] > b2[3])

    def _union_bbox(self, b1, b2):
        return [min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3])]

    def _calculate_strength(self, findings):
        score = 0.0
        signals = set(f["signal_id"] for f in findings)
        
        # Base score by signal count
        if len(signals) == 1: score = 0.35
        elif len(signals) == 2: score = 0.65
        else: score = 0.85
        
        # Severity bump
        has_high = any(f["severity"] == "HIGH" for f in findings)
        has_med = any(f["severity"] == "MEDIUM" for f in findings)
        
        if has_high: score += 0.10
        elif has_med: score += 0.05
        
        return min(1.0, score)

    def _generate_summary(self, fusion_result):
        clusters = self.db.query(EvidenceCluster).filter(EvidenceCluster.fusion_id == fusion_result.fusion_id).all()
        
        fusion_result.fusion_summary = {
            "total_clusters": len(clusters),
            "document_level_clusters": len([c for c in clusters if c.cluster_type == "document_level"]),
            "field_level_clusters": len([c for c in clusters if c.cluster_type == "field_level"]),
            "signal_breakdown": {
                "S04": len([c for c in clusters if "S04" in c.signals]),
                "S05": len([c for c in clusters if "S05" in c.signals]),
                "S06": len([c for c in clusters if "S06" in c.signals]),
                "S07": len([c for c in clusters if "S07" in c.signals]),
                "S08": len([c for c in clusters if "S08" in c.signals])
            }
        }
