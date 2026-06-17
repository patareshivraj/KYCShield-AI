import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.models import Document, DocumentPage, ELAResult, ELAHeatmap, ELARegion, ELAFinding, OCRResult, ExtractedField

class ELAForensicsService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_base = "backend/storage/evidence"
        os.makedirs(os.path.join(self.storage_base, "ela"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_base, "heatmaps"), exist_ok=True)

    def analyze_document(self, document_id: str) -> ELAResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        ela_result = ELAResult(document_id=document_id)
        self.db.add(ela_result)
        self.db.flush()
        
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        ocr_result = self.db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
        
        for page in pages:
            self._process_page(ela_result, page, ocr_result)
            
        self.db.commit()
        return ela_result

    def _process_page(self, ela_result: ELAResult, page: DocumentPage, ocr_result: OCRResult):
        if not page.storage_ref or not os.path.exists(page.storage_ref):
            return
            
        # 1. Re-save image at Quality 90
        try:
            original = Image.open(page.storage_ref).convert("RGB")
        except Exception:
            return
            
        tmp_jpg = f"backend/storage/evidence/ela/tmp_{page.page_id}.jpg"
        original.save(tmp_jpg, "JPEG", quality=90)
        
        recompressed = Image.open(tmp_jpg)
        
        # 2. Compare and generate difference image
        diff = ImageChops.difference(original, recompressed)
        
        # 3. Amplify differences to produce ELA image
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 255.0 / max_diff if max_diff != 0 else 1.0
        
        ela_img = ImageEnhance.Brightness(diff).enhance(scale)
        
        ela_path = os.path.join(self.storage_base, "ela", f"{page.page_id}_ela.png")
        ela_img.save(ela_path)
        
        # 4. Generate Visual Heatmap (OpenCV Color Map)
        diff_cv = np.array(ela_img)
        diff_cv = diff_cv[:, :, ::-1].copy() # RGB to BGR
        gray = cv2.cvtColor(diff_cv, cv2.COLOR_BGR2GRAY)
        
        heatmap_cv = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        heatmap_path = os.path.join(self.storage_base, "heatmaps", f"{page.page_id}_heatmap.png")
        cv2.imwrite(heatmap_path, heatmap_cv)
        
        heatmap_model = ELAHeatmap(
            ela_id=ela_result.ela_id,
            page_index=page.page_index,
            ela_image_ref=ela_path,
            heatmap_image_ref=heatmap_path
        )
        self.db.add(heatmap_model)
        
        # 5. Region Detection
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 20:  # Ignore noise
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [cnt], 0, 255, -1)
            mean_val = cv2.mean(gray, mask=mask)[0]
            max_val = cv2.minMaxLoc(gray, mask=mask)[1]
            
            bbox = [float(x), float(y), float(x+w), float(y+h)]
            
            region_model = ELARegion(
                ela_id=ela_result.ela_id,
                page_index=page.page_index,
                bbox=bbox,
                area=float(area),
                mean_intensity=float(mean_val),
                max_intensity=float(max_val)
            )
            self.db.add(region_model)
            self.db.flush()
            
            # 6. Analyze and cross-reference with OCR
            self._analyze_region(ela_result, region_model, ocr_result, heatmap_path)

        if os.path.exists(tmp_jpg):
            os.remove(tmp_jpg)

    def _analyze_region(self, ela_result: ELAResult, region: ELARegion, ocr_result: OCRResult, heatmap_ref: str):
        # Determine base severity from intensity
        if region.max_intensity > 150 and region.area > 100:
            severity = "MEDIUM"
            confidence = 0.7
            finding_type = "compression_mismatch_region"
        elif region.mean_intensity > 50:
            severity = "LOW"
            confidence = 0.6
            finding_type = "ela_region_anomaly"
        else:
            return  # Skip low-level anomalies
            
        x1, y1, x2, y2 = region.bbox
        
        # Cross reference with OCR
        overlap_found = False
        target_field = None
        
        if ocr_result and ocr_result.fields:
            for field in ocr_result.fields:
                if not field.evidence or "bbox" not in field.evidence or not field.evidence["bbox"]:
                    continue
                
                # field.evidence["bbox"] is list of 4 points [[x,y], [x,y], [x,y], [x,y]]
                box = field.evidence["bbox"]
                if not box or len(box) != 4: continue
                
                fx1 = min(p[0] for p in box)
                fy1 = min(p[1] for p in box)
                fx2 = max(p[0] for p in box)
                fy2 = max(p[1] for p in box)
                
                # Check overlap
                if not (x2 < fx1 or x1 > fx2 or y2 < fy1 or y1 > fy2):
                    overlap_found = True
                    target_field = field
                    break
                    
        if overlap_found:
            finding_type = "text_region_suspicious"
            confidence += 0.2
            
            critical_fields = ["PAN Number", "Aadhaar Number", "DOB", "Account Number", "Transaction Count"]
            if target_field.field_name in critical_fields:
                severity = "HIGH"
                confidence = 0.95
                
        finding = ELAFinding(
            ela_id=ela_result.ela_id,
            signal_id="S06",
            finding_type=finding_type,
            severity=severity,
            confidence=min(1.0, confidence),
            bbox=region.bbox,
            region_statistics={
                "area": region.area,
                "mean_intensity": region.mean_intensity,
                "max_intensity": region.max_intensity,
                "overlap_field": target_field.field_name if target_field else None
            },
            heatmap_reference=heatmap_ref
        )
        self.db.add(finding)
