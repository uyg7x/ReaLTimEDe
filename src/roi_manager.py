import cv2
import numpy as np

class ROIManager:
    def __init__(self, points: list):
        self.roi = np.array(points, dtype=np.int32)

    def is_inside(self, bbox: list) -> bool:
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        return cv2.pointPolygonTest(self.roi, (int(cx), int(cy)), False) >= 0

    def draw(self, frame):
        cv2.polylines(frame, [self.roi], True, (0, 255, 255), 2)
        cv2.putText(frame, "CONFLICT ZONE", (self.roi[0][0]+10, self.roi[0][1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)