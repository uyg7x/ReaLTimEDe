import cv2
import numpy as np
from ultralytics import YOLO
import os
from collections import defaultdict
import logging

class WildlifeDetector:
    def __init__(self, models_config: dict, target_classes: list, device: str = "cpu", active_mode: str = "default"):
        self.target_classes = [c.lower() for c in target_classes]
        self.device = device
        self.active_mode = active_mode
        self.models = {}
        self.class_names = {}
        self.logger = logging.getLogger(__name__)
        
        # 🔹 STRICT per-class confidence thresholds (INCREASED for accuracy)
        self.conf_thresholds = {
            "cheetah": 0.65,
            "crocodile": 0.70,
            "giraffe": 0.70,
            "rhino": 0.65,
            "elephant": 0.70,
            "bear": 0.65,
            "tiger": 0.70,
            "leopard": 0.65,
            "dog": 0.80,       # Very High: block false dogs
            "person": 0.60,
            "bird": 0.55,
            "boar": 0.65,
            "truck": 0.60,
            "default": 0.55    # Increased from 0.45
        }

        # 🔹 Size & Aspect Ratio Filters (pixels) - ADJUSTED
        self.size_filters = {
            "dog": {"min_w": 60, "min_h": 50, "max_ratio": 2.5},
            "bear": {"min_w": 80, "min_h": 60, "max_ratio": 2.5},
            "tiger": {"min_w": 80, "min_h": 60, "max_ratio": 2.8},
            "leopard": {"min_w": 70, "min_h": 50, "max_ratio": 2.8},
            "elephant": {"min_w": 120, "min_h": 80, "max_ratio": 2.0},
            "cheetah": {"min_w": 70, "min_h": 50, "max_ratio": 3.0},
            "giraffe": {"min_w": 80, "min_h": 100, "max_ratio": 2.0},
            "rhino": {"min_w": 100, "min_h": 70, "max_ratio": 2.5},
            "crocodile": {"min_w": 80, "min_h": 40, "max_ratio": 4.0},
            "boar": {"min_w": 60, "min_h": 40, "max_ratio": 2.5},
        }

        # 🔹 Temporal Consistency (track last 5 frames)
        self.frame_history = defaultdict(list)
        self.consistency_threshold = 3

        # Load models
        for name, path in models_config.items():
            if os.path.exists(path):
                self.models[name] = YOLO(path)
                self.class_names[name] = self.models[name].names
                print(f"✅ Loaded model: {name}")
            else:
                print(f"⚠️ Missing model: {path}")

        if not self.models:
            raise RuntimeError("No models loaded. Check paths.")

        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    def _preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = self.clahe.apply(gray)
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(frame, 0.4, enhanced_bgr, 0.6, 0)

    def _passes_filters(self, cls: str, bbox: list) -> bool:
        if cls not in self.size_filters:
            return True
        x1, y1, x2, y2 = bbox
        w, h = x2-x1, y2-y1
        filt = self.size_filters[cls]
        if w < filt["min_w"] or h < filt["min_h"]:
            return False
        if w/h > filt["max_ratio"] or h/w > filt["max_ratio"]:
            return False
        return True

    def detect(self, frame):
        proc = self._preprocess(frame)
        raw_dets = []

        if self.active_mode == "default":
            raw_dets = self._run("default", proc)
        elif self.active_mode == "custom":
            raw_dets = self._run("custom", proc)
        elif self.active_mode == "cascade":
            raw_dets = self._run_cascade(proc)

        # 🔹 Apply strict filtering + temporal consistency
        final = []
        filtered_count = {"confidence": 0, "size": 0, "consistency": 0}
        
        for det in raw_dets:
            cls, conf, bbox = det["class"], det["confidence"], det["bbox"]
            thresh = self.conf_thresholds.get(cls, self.conf_thresholds["default"])
            
            # Step 1: Filter by confidence
            if conf < thresh:
                filtered_count["confidence"] += 1
                continue
            
            # Step 2: Filter by size/aspect ratio
            if not self._passes_filters(cls, bbox):
                filtered_count["size"] += 1
                continue

            # Step 3: Temporal consistency check - verify detection appears in same area
            is_consistent = self._check_temporal_consistency(cls, bbox)
            
            if not is_consistent:
                filtered_count["consistency"] += 1
                continue
                
            final.append(det)
        
        # Log detection stats every 60 frames
        if raw_dets and len(raw_dets) > 0:
            self.logger.debug(f"Detection stats: {len(raw_dets)} raw → {len(final)} final | " +
                            f"conf:{filtered_count['confidence']} size:{filtered_count['size']} " +
                            f"consistency:{filtered_count['consistency']}")
        
        return final

    def _check_temporal_consistency(self, cls: str, current_bbox: list) -> bool:
        """Check if detection is consistent with recent history (same area)"""
        if cls not in self.frame_history:
            self.frame_history[cls] = []
        
        history = self.frame_history[cls]
        x1, y1, x2, y2 = current_bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1)
        
        # Need at least 2 consistent frames out of last 3
        consistent_count = 0
        required_matches = 2
        
        for prev_bbox in history:
            px1, py1, px2, py2 = prev_bbox
            p_center_x = (px1 + px2) / 2
            p_center_y = (py1 + py2) / 2
            p_area = (px2 - px1) * (py2 - py1)
            
            # Check spatial overlap (centers within 50 pixels)
            center_dist = ((center_x - p_center_x)**2 + (center_y - p_center_y)**2)**0.5
            area_ratio = min(area, p_area) / max(area, p_area) if max(area, p_area) > 0 else 0
            
            # Consider consistent if centers are close AND sizes are similar
            if center_dist < 50 and area_ratio > 0.5:
                consistent_count += 1
        
        # Update history (keep last 3 frames)
        history.append(current_bbox)
        if len(history) > 3:
            history.pop(0)
        
        # Require at least 2 consistent detections (current + 1 previous)
        return consistent_count >= required_matches - 1

    def _run(self, model_name, frame):
        results = self.models[model_name](frame, verbose=False, conf=0.30, iou=0.45, device=self.device)
        return self._parse(results, model_name)

    def _run_cascade(self, frame):
        dets = self._run("default", frame)
        # Skip cascade if too slow; just use filtered default
        return dets

    def _parse(self, results, model_name):
        dets = []
        for r in results:
            for box in r.boxes:
                cls = self.class_names[model_name][int(box.cls[0])].lower()
                conf = float(box.conf[0])
                if cls in self.target_classes:
                    dets.append({
                        "class": cls,
                        "confidence": conf,
                        "bbox": list(map(int, box.xyxy[0]))
                    })
        
        # Apply NMS to remove duplicate detections of same object
        if dets:
            dets = self._apply_nms(dets)
        
        return dets

    def _apply_nms(self, detections, iou_threshold=0.5):
        """Remove duplicate detections of the same object"""
        if not detections:
            return []
        
        # Group by class
        by_class = defaultdict(list)
        for det in detections:
            by_class[det["class"]].append(det)
        
        final = []
        for cls, cls_dets in by_class.items():
            # Sort by confidence (highest first)
            cls_dets.sort(key=lambda x: x["confidence"], reverse=True)
            
            kept = []
            while cls_dets:
                # Keep highest confidence detection
                best = cls_dets.pop(0)
                kept.append(best)
                
                # Remove overlapping detections
                cls_dets = [d for d in cls_dets if self._iou(best["bbox"], d["bbox"]) < iou_threshold]
            
            final.extend(kept)
        
        return final

    def _iou(self, box1, box2):
        """Calculate Intersection over Union"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0