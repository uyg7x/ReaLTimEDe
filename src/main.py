import cv2
import yaml
import sys
import os
import time
import logging

# 🔧 Setup project root so imports work regardless of execution directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.detector import WildlifeDetector
from src.roi_manager import ROIManager
from src.alert_system import AlertSystem

def load_config(path="config/settings.yaml"):
    abs_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"❌ Config not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    # 📝 Configure console logging (DEBUG level to see detection stats)
    logging.basicConfig(level=logging.DEBUG, format="%(message)s", datefmt="%H:%M:%S")
    logging.info("🌿 Wildlife Conflict Mitigation System (Dual-Model)")
    logging.info("==================================================")

    # 🔹 Load Configuration
    cfg = load_config()

    # 🔹 Initialize Core Components
    logging.info("🔧 Loading models & initializing modules...")
    detector = WildlifeDetector(
        models_config=cfg["models"],
        target_classes=cfg["target_classes"],
        device=cfg.get("device", "cpu"),
        active_mode=cfg.get("active_mode", "default")
    )
    roi = ROIManager(cfg["roi_coordinates"])
    alerts = AlertSystem(cfg.get("alert_cooldown_sec", 10))

    # 🔹 Robust Camera Initialization (Bypasses Windows DSHOW bug)
    video_src = cfg.get("video_source", "0")
    logging.info(f"📡 Connecting to source: {video_src}")

    cap = None
    backends = [cv2.CAP_MSMF, cv2.CAP_ANY, cv2.CAP_DSHOW]
    backend_names = {cv2.CAP_MSMF: "MSMF", cv2.CAP_ANY: "ANY", cv2.CAP_DSHOW: "DSHOW"}

    for backend in backends:
        try:
            src = int(video_src) if video_src.isdigit() else video_src
            cap = cv2.VideoCapture(src, backend)
            if cap.isOpened():
                # 🔑 Warm-up read (fixes first-frame lock/black screen)
                for _ in range(3):
                    cap.read()
                ret, test = cap.read()
                if ret and test is not None:
                    logging.info(f"✅ Camera opened successfully with backend: {backend_names.get(backend, 'UNKNOWN')}")
                    break
            cap.release()
            cap = None
        except Exception:
            continue

    if not cap or not cap.isOpened():
        logging.error("❌ FAILED to open camera/stream after trying all backends.")
        logging.error("💡 Fixes:")
        logging.error("   1. Close Zoom/Teams/Discord/Chrome (they lock cameras)")
        logging.error("   2. Check Windows Privacy > Camera > Allow desktop apps")
        logging.error("   3. Run 'python find_camera.py' to verify index")
        logging.error("   4. Use RTSP/mobile camera if laptop cam is blocked")
        input("Press Enter to exit...")
        sys.exit(1)

    # Optimize stream buffer
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    logging.info(f"🟢 SYSTEM ACTIVE | Mode: {detector.active_mode.upper()}")
    logging.info("⌨️ [1] Default | [2] Custom | [3] Cascade | [q/ESC] Exit")

    # 🔹 Windows-Optimized GUI Window
    window_title = "Wildlife Monitor | Dual-Model"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, 960, 640)
    cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 1)

    reconnect_delay = 3
    frame_count = 0
    fps_start = time.time()
    fps = 0.0

    try:
        while True:
            # 🔹 Auto-Reconnect Logic
            if not cap.isOpened():
                logging.warning(f"⏳ Stream lost. Reconnecting in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                src = int(video_src) if video_src.isdigit() else video_src
                cap = cv2.VideoCapture(src, cv2.CAP_ANY)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if cap.isOpened():
                    reconnect_delay = 3
                    logging.info("✅ Stream restored. Resuming detection.")
                else:
                    reconnect_delay = min(reconnect_delay * 2, 15)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            # 🔹 FPS Calculation
            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - fps_start
                fps = 30 / elapsed if elapsed > 0 else 0
                fps_start = time.time()

            # 🔹 Run Detection
            try:
                detections = detector.detect(frame)
            except Exception as e:
                logging.error(f"⚠️ Detection glitch: {e}")
                continue

            # 🔹 Draw ROI & Detections
            roi.draw(frame)
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                if roi.is_inside(det["bbox"]):
                    alerts.trigger(det["class"], det["confidence"], det["bbox"], frame)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"{det['class']}: {det['confidence']:.2f}", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

            # 🔹 Live Status Overlay
            mode_label = detector.active_mode.upper()
            status_text = f"MODE: {mode_label} | FPS: {fps:.1f} | [1]Def [2]Cus [3]Cas | Q=Exit"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 🔹 Display Frame
            cv2.imshow(window_title, frame)
            key = cv2.waitKey(1) & 0xFF

            # 🔹 Live Model Switching
            if key == ord('1'):
                detector.active_mode = "default"
                logging.info("🔄 Switched to DEFAULT model (COCO 80-class)")
            elif key == ord('2'):
                detector.active_mode = "custom"
                logging.info("🔄 Switched to CUSTOM model (Wildlife/Vehicles/Objects)")
            elif key == ord('3'):
                detector.active_mode = "cascade"
                logging.info("🔄 Switched to CASCADE mode (Fast Scan → Custom Verify)")
            elif key == ord('q') or key == 27:  # 27 = ESC
                logging.info("🛑 Stopped by user.")
                break

    except KeyboardInterrupt:
        logging.info("⛔ Stopped via Ctrl+C.")
    except Exception as e:
        logging.error(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logging.info("🔚 Cleaning up resources...")
        cap.release()
        cv2.destroyAllWindows()
        logging.info("✅ System shutdown complete. Logs & snapshots saved.")

if __name__ == "__main__":
    main()