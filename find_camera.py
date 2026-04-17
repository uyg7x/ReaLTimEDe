import cv2

print("🔍 Scanning for available cameras...")
working_cameras = []

for i in range(6):  # Checks indices 0 to 5
    # Force DirectShow backend (most reliable on Windows)
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            working_cameras.append(i)
            print(f"✅ Camera found at index: {i}")
        cap.release()

if not working_cameras:
    print("❌ No physical cameras detected.")
    print("💡 Fix: Check Windows Camera Privacy Settings (Step 2)")
else:
    print(f"\n🎯 Use this in settings.yaml: video_source: \"{working_cameras[0]}\"")