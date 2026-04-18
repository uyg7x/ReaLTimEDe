import cv2
import numpy as np
from ultralytics import YOLO
import os
from collections import defaultdict, deque

class WildlifeDetector:
    def __init__(self, models_config: dict, target_classes: list, device: str = "cpu", active_mode: str = "default"):
        """
        Initialize dual-model wildlife detector with strict filtering.
        
        Args:
            models_config: dict with model names and paths/names
            target_classes: list of class names to detect
            device: "cpu" or "cuda"
            active_mode: "default", "custom", or "cascade"
        """
        self.target_classes = [c.lower() for c in target_classes]
        self.device = device
        self.active_mode = active_mode
        self.models = {}
        self.class_names = {}
        
        # 🔹 STRICT per-class confidence thresholds (tune these!)
        self.conf_thresholds = {
            # Land mammals
            "dog": 0.75, "cat": 0.70, "elephant": 0.65, "bear": 0.60, 
            "tiger": 0.65, "leopard": 0.60, "lion": 0.65, "cheetah": 0.60,
            "giraffe": 0.60, "rhino": 0.65, "hippo": 0.65, "boar": 0.55,
            "sheep": 0.50, "cow": 0.50, "horse": 0.50, "zebra": 0.55,
            # Birds
            "bird": 0.50, "eagle": 0.55, "owl": 0.55,
            # Water animals
            "crocodile": 0.65, "alligator": 0.65, "turtle": 0.55, 
            "fish": 0.45, "frog": 0.50,
            # Vehicles & objects
            "truck": 0.50, "car": 0.50, "motorcycle": 0.50, "bicycle": 0.45,
            "bottle": 0.40, "cup": 0.40, "fork": 0.40, "knife": 0.40, "spoon": 0.40,
            # Default fallback
            "person": 0.50,
            "default": 0.45
        }

        # 🔹 Shape/Size Filters (width, height, min_area, max_aspect_ratio)
        # aspect_ratio = width / height
        self.shape_filters = {
            "giraffe":    {"min_h": 100, "min_w": 30, "max_ar": 0.5},   # Tall & thin
            "crocodile":  {"min_w": 60,  "min_h": 15, "max_ar": 6.0},   # Long & flat
            "alligator":  {"min_w": 60,  "min_h": 15, "max_ar": 6.0},
            "elephant":   {"min_area": 4000, "max_ar": 2.0},
            "bear":       {"min_area": 1200, "max_ar": 2.5},
            "tiger":      {"min_area": 1000, "max_ar": 3.0},
            "leopard":    {"min_area": 800,  "max_ar": 3.0},
            "lion":       {"min_area": 1000, "max_ar": 3.0},
            "cheetah":    {"min_area": 800,  "max_ar": 3.5},
            "rhino":      {"min_area": 2000, "max_ar": 2.0},
            "hippo":      {"min_area": 2500, "max_ar": 2.0},
            "dog":        {"min_area": 600,  "max_ar": 3.0},
            "cat":        {"min_area": 400,  "max_ar": 3.0},
            "bird":       {"min_area": 200,  "max_ar": 4.0},
            "turtle":     {"min_area": 300,  "max_ar": 2.0},
            "fish":       {"min_area": 400,  "max_ar": 5.0},
            "frog":       {"min_area": 150,  "max_ar": 2.5},
        }

        # 🔹 Temporal Consistency (require N consecutive frames to trigger alert)
        self.history = {cls: deque(maxlen=3) for cls in target_classes}
        self.consistency_required = {"bird": 2, "fish": 3, "frog": 3, "default": 3}

        # 🔹 Load models (YOLO auto-downloads if path is a model name)
        print("🔧 Loading detection models...")
        for name, path in models_config.items():
            try:
                # YOLO() accepts both file paths AND model names (auto-downloads from Ultralytics)
                self.models[name] = YOLO(path)
                self.class_names[name] = self.models[name].names
                print(f"✅ Loaded model: {name} ({path})")
            except Exception as e:
                print(f"⚠️ Failed to load {name} ({path}): {e}")

        if not self.models:
            raise RuntimeError("❌ No models loaded. Check paths or internet connection.")

        # 🔹 Preprocessing for low-light/jungle conditions
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    def _preprocess(self, frame):
        """Enhance visibility in low-light, foggy, or canopy-covered conditions."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            enhanced = self.clahe.apply(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            # Blend 50% original + 50% enhanced for natural look
            return cv2.addWeighted(frame, 0.5, enhanced_bgr, 0.5, 0)
        except:
            return frame  # Fallback to original if preprocessing fails

    def _passes_shape_filter(self, cls: str, bbox: list) -> bool:
        """Reject detections that don't match expected animal proportions."""
        if cls not in self.shape_filters:
            return True  # No filter = accept
        x1, y1, x2, y2 = bbox
        w, h = max(1, x2-x1), max(1, y2-y1)
        filt = self.shape_filters[cls]
        
        if "min_area" in filt and (w * h) < filt["min_area"]:
            return False
        if "min_w" in filt and w < filt["min_w"]:
            return False
        if "min_h" in filt and h < filt["min_h"]:
            return False
        if "max_ar" in filt:
            ar = w / h
            if ar > filt["max_ar"] or (1/ar) > filt["max_ar"]:
                return False
        return True

    def _temporal_check(self, cls: str, bbox: list) -> bool:
        """Require consistent detection across N frames before alerting."""
        hist = self.history[cls]
        hist.append(bbox)
        required = self.consistency_required.get(cls, self.consistency_required["default"])
        return len(hist) == required

    def detect(self, frame):
        """
        Run detection with preprocessing, filtering, and temporal consistency.
        
        Returns:
            list of detections: [{"class": str, "confidence": float, "bbox": [x1,y1,x2,y2]}]
        """
        proc_frame = self._preprocess(frame)
        raw_detections = []

        # Run model(s) based on active_mode
        if self.active_mode in ["default", "cascade"]:
            raw_detections += self._run_model("default", proc_frame)
        if self.active_mode in ["custom", "cascade"]:
            raw_detections += self._run_model("custom", proc_frame)

        # Apply strict filtering + temporal consistency
        final_detections = []
        for det in raw_detections:
            cls, conf, bbox = det["class"], det["confidence"], det["bbox"]
            
            # Skip if not in target list
            if cls not in self.target_classes:
                continue
            
            # Apply class-specific confidence threshold
            threshold = self.conf_thresholds.get(cls, self.conf_thresholds["default"])
            if conf < threshold:
                continue
            
            # Apply shape/size filter
            if not self._passes_shape_filter(cls, bbox):
                continue
            
            # Apply temporal consistency check
            if not self._temporal_check(cls, bbox):
                continue

            final_detections.append(det)

        return final_detections

    def _run_model(self, model_name: str, frame: np.ndarray):
        """Run a single model and parse results."""
        if model_name not in self.models:
            return []
        
        try:
            results = self.models[model_name](
                frame, 
                verbose=False, 
                conf=0.30,  # Low threshold here; we filter strictly later
                iou=0.45, 
                device=self.device,
                max_det=100  # Limit detections per frame for speed
            )
            return self._parse_results(results, model_name)
        except Exception as e:
            print(f"⚠️ Detection error in {model_name}: {e}")
            return []

    def _parse_results(self, results, model_name: str):
        """Parse YOLO results into standardized detection format."""
        detections = []
        for r in results:
            for box in r.boxes:
                try:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    cls_name = self.class_names[model_name][cls_id].lower()
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    detections.append({
                        "class": cls_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })
                except (IndexError, ValueError, KeyError):
                    continue  # Skip malformed boxes
        return detections

    def switch_mode(self, mode: str):
        """Live-switch detection mode without restarting."""
        if mode in ["default", "custom", "cascade"]:
            self.active_mode = mode
            print(f"🔄 Switched to {mode.upper()} mode")
        else:
            print(f"⚠️ Unknown mode: {mode}")
