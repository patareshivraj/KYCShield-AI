import os
import cv2
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.models import Document, DocumentPage, NoiseResult, NoiseMap, NoiseRegion, NoiseFinding, OCRResult, ExtractedField, ELAFinding, ELAResult

class NoiseForensicsService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_base = "backend/storage/evidence"
        os.makedirs(os.path.join(self.storage_base, "noise"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_base, "textures"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_base, "sharpness"), exist_ok=True)

    def analyze_document(self, document_id: str) -> NoiseResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        noise_result = NoiseResult(document_id=document_id)
        self.db.add(noise_result)
        self.db.flush()
        
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        ocr_result = self.db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
        ela_result = self.db.query(ELAResult).filter(ELAResult.document_id == document_id).first()
        
        for page in pages:
            self._process_page(noise_result, page, ocr_result, ela_result)
            
        self.db.commit()
        return noise_result

    def _process_page(self, noise_result: NoiseResult, page: DocumentPage, ocr_result: OCRResult, ela_result: ELAResult):
        if not page.storage_ref or not os.path.exists(page.storage_ref):
            return
            
        img = cv2.imread(page.storage_ref)
        if img is None:
            return
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Noise Residual Extraction (Median Filter Residual)
        median = cv2.medianBlur(gray, 5)
        noise_residual = cv2.absdiff(gray, median)
        # Amplify noise for visualization
        noise_visual = cv2.normalize(noise_residual, None, 0, 255, cv2.NORM_MINMAX)
        noise_map_cv = cv2.applyColorMap(noise_visual, cv2.COLORMAP_BONE)
        
        noise_path = os.path.join(self.storage_base, "noise", f"{page.page_id}_noise.png")
        cv2.imwrite(noise_path, noise_map_cv)
        
        # 2. Local Texture Analysis (Gradient Magnitude)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        texture_mag = cv2.magnitude(sobelx, sobely)
        texture_visual = cv2.normalize(texture_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        texture_map_cv = cv2.applyColorMap(texture_visual, cv2.COLORMAP_VIRIDIS)
        
        texture_path = os.path.join(self.storage_base, "textures", f"{page.page_id}_texture.png")
        cv2.imwrite(texture_path, texture_map_cv)
        
        # 3. Sharpness Consistency (Laplacian Variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_visual = cv2.normalize(np.abs(laplacian), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        sharpness_map_cv = cv2.applyColorMap(sharpness_visual, cv2.COLORMAP_HOT)
        
        sharpness_path = os.path.join(self.storage_base, "sharpness", f"{page.page_id}_sharpness.png")
        cv2.imwrite(sharpness_path, sharpness_map_cv)
        
        # Save Maps
        for path, map_type in [(noise_path, "noise"), (texture_path, "texture"), (sharpness_path, "sharpness")]:
            self.db.add(NoiseMap(noise_id=noise_result.noise_id, page_index=page.page_index, map_type=map_type, map_image_ref=path))
        self.db.flush()
        
        # Region Detection for each map
        self._detect_regions(noise_result, page, noise_visual, noise_path, "noise_anomaly", ocr_result, ela_result)
        self._detect_regions(noise_result, page, texture_visual, texture_path, "texture_anomaly", ocr_result, ela_result)
        self._detect_regions(noise_result, page, sharpness_visual, sharpness_path, "sharpness_anomaly", ocr_result, ela_result)
        
    def _detect_regions(self, noise_result, page, map_gray, heatmap_ref, region_type, ocr_result, ela_result):
        # We look for regions that are heavily inconsistent (high values in the enhanced maps)
        # We will use a lower threshold to find things since ai_test_ds might be clean
        _, thresh = cv2.threshold(map_gray, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 20:  # Ignore very small noise spikes
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            mask = np.zeros(map_gray.shape, np.uint8)
            cv2.drawContours(mask, [cnt], 0, 255, -1)
            mean_val = cv2.mean(map_gray, mask=mask)[0]
            max_val = cv2.minMaxLoc(map_gray, mask=mask)[1]
            
            bbox = [float(x), float(y), float(x+w), float(y+h)]
            
            region_model = NoiseRegion(
                noise_id=noise_result.noise_id,
                page_index=page.page_index,
                bbox=bbox,
                region_type=region_type,
                area=float(area),
                mean_value=float(mean_val),
                max_value=float(max_val)
            )
            self.db.add(region_model)
            self.db.flush()
            
            self._analyze_region(noise_result, region_model, ocr_result, ela_result, heatmap_ref)

    def _analyze_region(self, noise_result, region, ocr_result, ela_result, heatmap_ref):
        severity = "LOW"
        confidence = 0.6
        finding_type = region.region_type.replace("anomaly", "mismatch_region")
        supporting_signals = []
        
        x1, y1, x2, y2 = region.bbox
        
        overlap_ocr = False
        target_field = None
        
        if ocr_result and ocr_result.fields:
            for field in ocr_result.fields:
                box = field.evidence.get("bbox", []) if field.evidence else []
                if not box or len(box) != 4: continue
                
                fx1 = min(p[0] for p in box)
                fy1 = min(p[1] for p in box)
                fx2 = max(p[0] for p in box)
                fy2 = max(p[1] for p in box)
                
                if not (x2 < fx1 or x1 > fx2 or y2 < fy1 or y1 > fy2):
                    overlap_ocr = True
                    target_field = field
                    break
        
        overlap_ela = False
        if ela_result and ela_result.findings:
            for ela_finding in ela_result.findings:
                box = ela_finding.bbox
                if not box or len(box) != 4: continue
                
                ex1, ey1, ex2, ey2 = box
                if not (x2 < ex1 or x1 > ex2 or y2 < ey1 or y1 > ey2):
                    overlap_ela = True
                    supporting_signals.append("S06")
                    break

        if overlap_ocr:
            confidence += 0.2
            critical_fields = ["PAN Number", "Aadhaar Number", "DOB", "Account Number", "Transaction Count"]
            if target_field and target_field.field_name in critical_fields:
                severity = "HIGH"
                confidence = 0.95
                
        if overlap_ela:
            finding_type = "multi_signal_region"
            severity = "HIGH"
            confidence = 0.95
            
        # FILTER: Prevent DB explosion. Only save if severity is MEDIUM/HIGH or there is multi-signal/OCR overlap.
        if severity == "LOW" and not overlap_ocr and not overlap_ela:
            return
            
        finding = NoiseFinding(
            noise_id=noise_result.noise_id,
            signal_id="S07",
            finding_type=finding_type,
            severity=severity,
            confidence=min(1.0, confidence),
            bbox=region.bbox,
            region_statistics={
                "area": region.area,
                "mean_value": region.mean_value,
                "max_value": region.max_value,
                "overlap_field": target_field.field_name if target_field else None
            },
            supporting_signals=supporting_signals,
            heatmap_reference=heatmap_ref
        )
        self.db.add(finding)
