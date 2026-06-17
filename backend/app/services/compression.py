import os
import cv2
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.models import Document, DocumentPage, CompressionResult, CompressionArtifact, CompressionRegion, CompressionFinding, OCRResult, ExtractedField, ELAFinding, ELAResult, NoiseFinding, NoiseResult

class CompressionForensicsService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_base = "backend/storage/evidence"
        os.makedirs(os.path.join(self.storage_base, "compression"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_base, "artifacts"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_base, "blockmaps"), exist_ok=True)

    def analyze_document(self, document_id: str) -> CompressionResult:
        doc = self.db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError("Document not found")
            
        comp_result = CompressionResult(document_id=document_id)
        self.db.add(comp_result)
        self.db.flush()
        
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        ocr_result = self.db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
        ela_result = self.db.query(ELAResult).filter(ELAResult.document_id == document_id).first()
        noise_result = self.db.query(NoiseResult).filter(NoiseResult.document_id == document_id).first()
        
        for page in pages:
            self._process_page(comp_result, page, ocr_result, ela_result, noise_result)
            
        self.db.commit()
        return comp_result

    def _process_page(self, comp_result: CompressionResult, page: DocumentPage, ocr_result: OCRResult, ela_result: ELAResult, noise_result: NoiseResult):
        if not page.storage_ref or not os.path.exists(page.storage_ref):
            return
            
        img = cv2.imread(page.storage_ref)
        if img is None:
            return
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. JPEG Block Artifact Analysis (8x8 Grid Boundaries)
        # Compute differences at exactly 8x8 intervals to detect jpeg grid mismatches
        block_diff = np.zeros_like(gray, dtype=np.float32)
        h, w = gray.shape
        for i in range(8, h-8, 8):
            block_diff[i, :] = np.abs(gray[i, :].astype(np.float32) - gray[i-1, :].astype(np.float32))
        for j in range(8, w-8, 8):
            block_diff[:, j] = np.maximum(block_diff[:, j], np.abs(gray[:, j].astype(np.float32) - gray[:, j-1].astype(np.float32)))
            
        block_visual = cv2.normalize(block_diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        block_map_cv = cv2.applyColorMap(block_visual, cv2.COLORMAP_JET)
        blockmap_path = os.path.join(self.storage_base, "blockmaps", f"{page.page_id}_blockmap.png")
        cv2.imwrite(blockmap_path, block_map_cv)
        
        # 2. Compression Consistency / Recompression Heatmap
        # Apply a fast fourier transform or DCT approximation (here we use a simplistic high-frequency bandpass approximation)
        blur1 = cv2.GaussianBlur(gray, (5, 5), 0)
        blur2 = cv2.GaussianBlur(gray, (21, 21), 0)
        bandpass = cv2.absdiff(blur1, blur2)
        heat_visual = cv2.normalize(bandpass, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heat_map_cv = cv2.applyColorMap(heat_visual, cv2.COLORMAP_INFERNO)
        heatmap_path = os.path.join(self.storage_base, "compression", f"{page.page_id}_heatmap.png")
        cv2.imwrite(heatmap_path, heat_map_cv)
        
        # 3. PDF Rendering Artifact Analysis (Simulated via morphological artifacts if pdf)
        if page.derived_from_pdf:
            morph = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, np.ones((3,3), np.uint8))
            artifact_visual = cv2.normalize(morph, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        else:
            # Just another compression edge artifact pass for images
            artifact_visual = cv2.Canny(gray, 100, 200)
            
        artifact_map_cv = cv2.applyColorMap(artifact_visual, cv2.COLORMAP_WINTER)
        artifactmap_path = os.path.join(self.storage_base, "artifacts", f"{page.page_id}_artifactmap.png")
        cv2.imwrite(artifactmap_path, artifact_map_cv)
        
        # Save Maps
        for path, map_type in [(blockmap_path, "block_map"), (heatmap_path, "heat_map"), (artifactmap_path, "artifact_map")]:
            self.db.add(CompressionArtifact(compression_id=comp_result.compression_id, page_index=page.page_index, artifact_type=map_type, artifact_image_ref=path))
        self.db.flush()
        
        # Region Detection for each map
        self._detect_regions(comp_result, page, block_visual, blockmap_path, "compression_mismatch_region", ocr_result, ela_result, noise_result)
        self._detect_regions(comp_result, page, heat_visual, heatmap_path, "double_compression_region", ocr_result, ela_result, noise_result)
        
        if page.derived_from_pdf:
            self._detect_regions(comp_result, page, artifact_visual, artifactmap_path, "rendering_anomaly_region", ocr_result, ela_result, noise_result)
        else:
            self._detect_regions(comp_result, page, artifact_visual, artifactmap_path, "artifact_cluster_region", ocr_result, ela_result, noise_result)
        
    def _detect_regions(self, comp_result, page, map_gray, artifact_ref, region_type, ocr_result, ela_result, noise_result):
        # We look for regions that are heavily inconsistent (high values in the enhanced maps)
        _, thresh = cv2.threshold(map_gray, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 30:  # Ignore very small spikes
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            mask = np.zeros(map_gray.shape, np.uint8)
            cv2.drawContours(mask, [cnt], 0, 255, -1)
            mean_val = cv2.mean(map_gray, mask=mask)[0]
            max_val = cv2.minMaxLoc(map_gray, mask=mask)[1]
            
            bbox = [float(x), float(y), float(x+w), float(y+h)]
            
            region_model = CompressionRegion(
                compression_id=comp_result.compression_id,
                page_index=page.page_index,
                bbox=bbox,
                region_type=region_type,
                area=float(area),
                mean_value=float(mean_val),
                max_value=float(max_val)
            )
            self.db.add(region_model)
            self.db.flush()
            
            self._analyze_region(comp_result, region_model, ocr_result, ela_result, noise_result, artifact_ref)

    def _analyze_region(self, comp_result, region, ocr_result, ela_result, noise_result, artifact_ref):
        severity = "LOW"
        confidence = 0.6
        finding_type = region.region_type
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
        
        # Correlate with ELA (S06)
        overlap_ela = False
        if ela_result and ela_result.findings:
            for f in ela_result.findings:
                box = f.bbox
                if not box or len(box) != 4: continue
                ex1, ey1, ex2, ey2 = box
                if not (x2 < ex1 or x1 > ex2 or y2 < ey1 or y1 > ey2):
                    overlap_ela = True
                    if "S06" not in supporting_signals:
                        supporting_signals.append("S06")
                    break

        # Correlate with Noise (S07)
        overlap_noise = False
        if noise_result and noise_result.findings:
            for f in noise_result.findings:
                box = f.bbox
                if not box or len(box) != 4: continue
                nx1, ny1, nx2, ny2 = box
                if not (x2 < nx1 or x1 > nx2 or y2 < ny1 or y1 > ny2):
                    overlap_noise = True
                    if "S07" not in supporting_signals:
                        supporting_signals.append("S07")
                    break

        if overlap_ocr:
            confidence += 0.2
            critical_fields = ["PAN Number", "Aadhaar Number", "DOB", "Account Number", "Transaction Count"]
            if target_field and target_field.field_name in critical_fields:
                severity = "HIGH"
                confidence = 0.95
                
        # If there are multiple signals correlating to this region
        if len(supporting_signals) >= 1:
            finding_type = "multi_signal_region"
            severity = "HIGH"
            confidence = 0.95
            
        # FILTER: Prevent DB explosion. Only save if severity is MEDIUM/HIGH or there is multi-signal/OCR overlap.
        if severity == "LOW" and not overlap_ocr and len(supporting_signals) == 0:
            return
            
        finding = CompressionFinding(
            compression_id=comp_result.compression_id,
            signal_id="S08",
            finding_type=finding_type,
            severity=severity,
            confidence=min(1.0, confidence),
            bbox=region.bbox,
            compression_statistics={
                "area": region.area,
                "mean_value": region.mean_value,
                "max_value": region.max_value,
                "overlap_field": target_field.field_name if target_field else None
            },
            supporting_signals=supporting_signals,
            artifact_reference=artifact_ref
        )
        self.db.add(finding)
