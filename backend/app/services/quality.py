import cv2
import numpy as np
from sqlalchemy.orm import Session
from backend.app.db.models import Document, QualityProfile

class QualityService:
    def __init__(self, db: Session):
        self.db = db

    def assess_job(self, job_id: str):
        from backend.app.db.models import Job
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return
            
        docs = self.db.query(Document).filter(Document.applicant_id == job.applicant_id).all()
        for doc in docs:
            self._assess_document(doc)
            
        self.db.commit()

    def _assess_document(self, doc: Document):
        if not doc.pages:
            return
            
        # Assess first page for MVP
        page = doc.pages[0]
        img = cv2.imread(page.storage_ref)
        if img is None:
            return
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Blur (Laplacian variance)
        blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(1.0, blur_val / 500.0)
        blur_gate = "pass" if blur_score > 0.3 else ("warn" if blur_score > 0.1 else "fail")
        
        # 2. Resolution
        res_score = min(1.0, (page.width_px * page.height_px) / 2000000.0)
        res_gate = "pass" if res_score > 0.4 else ("warn" if res_score > 0.2 else "fail")
        
        # 3. Exposure
        mean_val = np.mean(gray)
        if mean_val < 50:
            exp_gate = "fail"
        elif mean_val < 80 or mean_val > 220:
            exp_gate = "warn"
        else:
            exp_gate = "pass"
            
        # 4. Rotation
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        skew_degrees = 0.0
        if lines is not None:
            angles = [line[0][1] for line in lines]
            skew_degrees = np.degrees(np.median(angles))
            # Normalize to -45 to 45
            if skew_degrees > 45:
                skew_degrees -= 90
                
        rot_score = max(0.0, 1.0 - abs(skew_degrees)/90.0)
        rot_gate = "pass" if abs(skew_degrees) < 5 else ("warn" if abs(skew_degrees) < 15 else "fail")
        
        # 5. Crop Completeness
        h, w = gray.shape
        margin = int(min(h, w) * 0.05) # 5% margin
        # Check edges on the boundaries
        border_pixels = np.count_nonzero(edges[0:margin, :]) + np.count_nonzero(edges[h-margin:h, :]) + \
                        np.count_nonzero(edges[:, 0:margin]) + np.count_nonzero(edges[:, w-margin:w])
        total_margin_area = (h * margin * 2) + (w * margin * 2)
        crop_ratio = border_pixels / float(total_margin_area + 1)
        
        crop_score = max(0.0, 1.0 - (crop_ratio * 10))
        crop_gate = "pass" if crop_score > 0.7 else ("warn" if crop_score > 0.4 else "fail")

        # Combine
        gates = [blur_gate, res_gate, exp_gate, rot_gate, crop_gate]
        if "fail" in gates:
            overall_gate = "fail"
        elif "warn" in gates:
            overall_gate = "warn"
        else:
            overall_gate = "pass"
            
        overall_score = float((blur_score + res_score + rot_score + crop_score) / 4.0)
        
        qp = QualityProfile(
            document_id=doc.document_id,
            overall_gate=overall_gate,
            overall_score=overall_score,
            metrics={
                "blur": {"score": float(blur_score), "gate": blur_gate},
                "resolution": {"score": float(res_score), "gate": res_gate, "width_px": int(page.width_px), "height_px": int(page.height_px)},
                "rotation": {"score": float(rot_score), "gate": rot_gate, "skew_degrees": float(skew_degrees)},
                "crop_completeness": {"score": float(crop_score), "gate": crop_gate},
                "exposure": {"overexposure": 0.0 if mean_val <= 200 else float((mean_val-200)/55.0), 
                             "underexposure": 0.0 if mean_val >= 50 else float((50-mean_val)/50.0), 
                             "gate": exp_gate}
            },
            confidence_cap_tier_c=0.5 if overall_gate == "warn" else (0.0 if overall_gate == "fail" else 1.0),
            limitations="basic heuristics"
        )
        self.db.add(qp)
