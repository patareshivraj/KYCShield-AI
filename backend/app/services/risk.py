from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.models import (
    Document, FusionResult, EvidenceCluster, DocumentRiskAssessment, RiskFactor, RiskContribution
)

class DocumentRiskEngine:
    def __init__(self, db: Session):
        self.db = db
        
        # Task 4 & 5: Configurations
        self.FIELD_WEIGHTS = {
            "PAN Number": 1.0,
            "Aadhaar Number": 1.0,
            "Account Number": 1.0,
            "DOB": 0.8,
            "Photo": 0.8,
            "Transaction Count": 0.8,
            "Name": 0.7,
            "Address": 0.5,
            "Statement Period": 0.5
        }
        
        self.SIGNAL_WEIGHTS = {
            "S04": 0.4,
            "S05": 0.5,
            "S06": 0.8,
            "S07": 0.8,
            "S08": 0.9
        }

    def analyze_document(self, document_id: str) -> DocumentRiskAssessment:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        fusion_result = self.db.query(FusionResult).filter(FusionResult.document_id == document_id).first()
        if not fusion_result:
            raise ValueError("Evidence Fusion not complete")
            
        assessment = DocumentRiskAssessment(document_id=document_id)
        self.db.add(assessment)
        self.db.flush()
        
        clusters = self.db.query(EvidenceCluster).filter(EvidenceCluster.fusion_id == fusion_result.fusion_id).all()
        
        # Calculate cluster contributions
        total_risk = 0.0
        contributions = []
        factors_map = {}
        
        for cluster in clusters:
            contrib_score, explanation = self._calculate_cluster_contribution(cluster)
            
            if contrib_score > 0:
                contributions.append({
                    "cluster": cluster,
                    "score": contrib_score,
                    "explanation": explanation
                })
                total_risk += contrib_score
                
                # Derive Risk Factors
                self._map_risk_factors(cluster, contrib_score, factors_map)
                
        # Top Drivers
        contributions.sort(key=lambda x: x["score"], reverse=True)
        top_drivers = []
        
        for idx, contrib in enumerate(contributions):
            rc = RiskContribution(
                assessment_id=assessment.assessment_id,
                cluster_id=contrib["cluster"].cluster_id,
                risk_contribution_score=contrib["score"],
                rank=idx + 1,
                explanation=contrib["explanation"]
            )
            self.db.add(rc)
            if idx < 3:
                top_drivers.append(contrib["explanation"])
                
        # Apply Risk Factors
        for f_name, f_data in factors_map.items():
            self.db.add(RiskFactor(
                assessment_id=assessment.assessment_id,
                factor_name=f_name,
                contribution_score=f_data["score"],
                description=f_data["desc"]
            ))
            
        # Task 8: Risk Score 0-100
        final_score = min(100.0, total_risk)
        
        if final_score <= 20: level = "LOW"
        elif final_score <= 50: level = "MODERATE"
        elif final_score <= 75: level = "HIGH"
        else: level = "CRITICAL"
        
        assessment.risk_score = final_score
        assessment.risk_level = level
        
        # Summaries
        if final_score > 50:
            exec_sum = f"Document exhibits {level} risk. Multiple independent forensic anomalies affecting key fields."
        else:
            exec_sum = f"Document exhibits {level} risk. Minor structural anomalies detected."
            
        assessment.executive_summary = exec_sum
        assessment.investigator_summary = "; ".join(top_drivers) if top_drivers else "No significant risk drivers."
        
        self.db.commit()
        return assessment
        
    def _calculate_cluster_contribution(self, cluster: EvidenceCluster):
        # Base on evidence strength
        score = cluster.evidence_strength * 25.0  # Base scale 0-25
        
        field_multiplier = 0.2  # Base for no fields
        if cluster.affected_fields:
            field_multiplier = max([self.FIELD_WEIGHTS.get(f, 0.2) for f in cluster.affected_fields])
            
        signal_multiplier = max([self.SIGNAL_WEIGHTS.get(s, 0.4) for s in cluster.signals]) if cluster.signals else 0.4
        
        # Formula: strength * field_importance * signal_importance + diversity_bonus
        final_contrib = score * field_multiplier * signal_multiplier
        
        if len(cluster.signals) >= 2:
            final_contrib += 15.0  # Bonus for multi-signal fusion
            
        explanation = f"Multiple forensic signals ({', '.join(cluster.signals)}) overlap the {', '.join(cluster.affected_fields)} field" if cluster.affected_fields else f"Forensic signals ({', '.join(cluster.signals)}) detected in background"
        
        return final_contrib, explanation
        
    def _map_risk_factors(self, cluster: EvidenceCluster, score: float, factors_map: dict):
        if cluster.affected_fields:
            # Check if identity fields
            identity = ["PAN Number", "Aadhaar Number", "DOB", "Name", "Photo"]
            financial = ["Account Number", "Transaction Count", "Statement Period"]
            
            if any(f in identity for f in cluster.affected_fields):
                factors_map["identity_field_tampering_risk"] = {
                    "score": factors_map.get("identity_field_tampering_risk", {}).get("score", 0) + score,
                    "desc": "Forensic anomalies overlap core identity fields."
                }
            if any(f in financial for f in cluster.affected_fields):
                factors_map["financial_data_modification_risk"] = {
                    "score": factors_map.get("financial_data_modification_risk", {}).get("score", 0) + score,
                    "desc": "Forensic anomalies overlap financial transaction data."
                }
        else:
            if "S04" in cluster.signals or "S05" in cluster.signals:
                factors_map["metadata_anomaly_risk"] = {
                    "score": factors_map.get("metadata_anomaly_risk", {}).get("score", 0) + score,
                    "desc": "Metadata inconsistencies present."
                }
            else:
                factors_map["compression_anomaly_risk"] = {
                    "score": factors_map.get("compression_anomaly_risk", {}).get("score", 0) + score,
                    "desc": "Image structural anomalies present."
                }
