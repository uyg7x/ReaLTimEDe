# Wildlife Conflict Mitigation System  OR  USe  Unknown Object Detection

A dual-model YOLO-based wildlife detection and alert system designed to prevent human-wildlife conflicts by detecting animals in restricted areas and triggering real-time alerts.

## 🌟 Features

- **Dual-Model Detection**: Switch between COCO pretrained model and custom wildlife model
- **Multi-Species Detection**: Supports cheetah, crocodile, giraffe, rhino, elephant, bear, tiger, leopard, and more
- **ROI-Based Alerting**: Configurable Region of Interest (ROI) for targeted monitoring
- **Temporal Consistency**: Advanced filtering to reduce false positives
- **Real-Time Alerts**: Visual and logging-based alert system with cooldown
- **Camera Auto-Reconnect**: Robust stream recovery on connection loss
- **Multi-Backend Support**: Works with MSMF, DSHOW, and ANY OpenCV backends

## 📋 Requirements

- Python 3.8+
- Windows 10/11 (optimized for Windows)
- OpenCV-compatible camera or RTSP stream
- 4GB+ RAM recommended

## 🚀 Installation

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd RTWAD
```

2. **Create virtual environment**:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Download pretrained models**:
```bash
# YOLOv8 nano (COCO)
# Download: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
# Save as: yolov8n.pt in project root

# Custom wildlife model (optional)
# Train your own or download from Hugging Face Hub
```

5. **Configure settings**:
```bash
# Copy config/settings.yaml.example to config/settings.yaml
# Edit video_source, roi_coordinates, and other settings
```

## 🎯 Usage

> **⚠️ IMPORTANT: For Accurate Detection**
> 
> **This system uses pretrained YOLOv8 models. For production use with accurate wildlife detection:**
> 
> - **🎓 Train a custom model** on your specific wildlife species and environment
> - **📊 Use high-quality, diverse training data** (different lighting, angles, distances)
> - **🔄 Fine-tune the model** with local wildlife images for best results
> - **⚙️ Adjust confidence thresholds** in `src/detector.py` based on your use case
> 
> **The default COCO model may not accurately detect all wildlife species. Custom training is highly recommended for production deployments.**

### Basic Detection

```bash
python src/main.py
```

### Find Available Cameras

```bash
python find_camera.py
```

### Keyboard Controls

- **[1]**: Switch to DEFAULT model (COCO 80-class)
- **[2]**: Switch to CUSTOM model (Wildlife-specific)
- **[3]**: Switch to CASCADE mode (Fast scan → Custom verify)
- **[Q]** or **[ESC]**: Exit
- **[Ctrl+C]**: Stop gracefully

## 📁 Project Structure

```
RTWAD/
├── src/
│   ├── main.py              # Main application entry point
│   ├── detector.py          # Wildlife detection logic with filtering
│   ├── roi_manager.py       # Region of Interest management
│   └── alert_system.py      # Alert triggering and cooldown
├── config/
│   └── settings.yaml        # Configuration file
├── wildlife_dataset/        # Training dataset (not included)
├── final_dataset/           # Merged dataset (not included)
├── runs/                    # Training results (not included)
├── models/                  # Custom model weights (not included)
├── find_camera.py           # Camera discovery utility
├── augment_train.py         # Image augmentation script
└── merge_datasets.py        # Dataset merging utility
```

## ⚙️ Configuration

Edit `config/settings.yaml`:

```yaml
models:
  default: "yolov8n.pt"
  custom: "runs/detect/wildlife_multi_v5/weights/best.pt"

active_mode: "custom"

target_classes:
  - cheetah
  - crocodile
  - giraffe
  - rhino
  - elephant
  - bear
  - tiger
  - dog
  - bird
  - person

video_source: "0"  # Camera index or RTSP URL
device: "cpu"       # cpu or cuda

roi_coordinates:
  - [100, 100]
  - [500, 100]
  - [500, 400]
  - [100, 400]

alert_cooldown_sec: 10
```

## 🔧 Detection Pipeline

The system applies multiple filtering stages:

1. **Confidence Threshold**: Class-specific minimum confidence (0.55-0.80)
2. **Size Filter**: Minimum dimensions and aspect ratio validation
3. **Temporal Consistency**: Spatial matching across 3 frames
4. **NMS**: Duplicate detection removal

## 📊 Detection Statistics

When running in DEBUG mode, the console shows:
```
Detection stats: 15 raw → 3 final | conf:8 size:2 consistency:2
```

This indicates:
- 15 raw detections from YOLO
- 3 final detections after filtering
- 8 filtered by confidence
- 2 filtered by size
- 2 filtered by temporal consistency

## 🛠️ Troubleshooting

### Camera Not Opening

1. Close other apps using the camera (Zoom, Teams, Discord)
2. Check Windows Privacy Settings > Camera > Allow desktop apps
3. Run `python find_camera.py` to verify camera index
4. Try RTSP stream or mobile camera app

### False Detections

- Increase confidence thresholds in `src/detector.py`
- Adjust size filters for specific species
- Tune temporal consistency parameters

### Model Not Loading

- Ensure `.pt` files are in project root
- Check paths in `config/settings.yaml`
- Verify model files are not corrupted

## 🧪 Training Custom Model

1. **Prepare dataset** in YOLO format
2. **Merge datasets** (optional):
```bash
python merge_datasets.py
```

3. **Augment images**:
```bash
python augment_train.py
```

4. **Train model**:
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='final_dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='wildlife_custom'
)
```

## 📝 License

This project is provided as-is for educational and research purposes.

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with** ❤️ **using Ultralytics YOLOv8**
# ReaLTimEDe
