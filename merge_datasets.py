import os, shutil, yaml
from pathlib import Path

ROOT = r"T:\RTWAD\wildlife_dataset"
OUTPUT = r"T:\RTWAD\final_dataset"

# 1. Create clean structure
for p in ["train/images", "train/labels", "valid/images", "valid/labels"]:
    os.makedirs(os.path.join(OUTPUT, p), exist_ok=True)

# 2. Map subfolders to their class names
# (Adjust if your exports contain multiple classes)
DATASET_MAP = {
    "cheetah.v2i.yolov8": ["cheetah"],
    "Crocodile.v4i.yolov8": ["crocodile"],
    "giraffe.v3i.yolov8": ["giraffe"],
    "Rhino.v2i.yolov8": ["rhino"]
}

# Build global class list & ID map
all_classes = []
for classes in DATASET_MAP.values():
    all_classes.extend(classes)
class_to_id = {name: i for i, name in enumerate(all_classes)}

img_counter = 0

def merge_split(folder, split):
    global img_counter
    src = Path(ROOT) / folder / split
    if not src.exists(): return
    img_src = src / "images"
    lbl_src = src / "labels"
    if not img_src.exists() or not lbl_src.exists(): return

    for img in img_src.glob("*.jpg"):
        lbl = lbl_src / f"{img.stem}.txt"
        if not lbl.exists(): continue

        new_name = f"{img_counter:06d}"
        shutil.copy2(img, f"{OUTPUT}/{split}/images/{new_name}.jpg")

        # 🔑 Remap class indices to global IDs
        with open(lbl, "r") as f: lines = f.readlines()
        with open(f"{OUTPUT}/{split}/labels/{new_name}.txt", "w") as f:
            for line in lines:
                parts = line.strip().split()
                if len(parts) == 5:
                    old_cls = int(parts[0])
                    global_cls = DATASET_MAP[folder][old_cls]
                    f.write(f"{class_to_id[global_cls]} {' '.join(parts[1:])}\n")
                else:
                    f.write(line + "\n")
        img_counter += 1

# 3. Run merge
print("🔄 Merging datasets...")
for folder in DATASET_MAP:
    merge_split(folder, "train")
    merge_split(folder, "valid")

# 4. Generate YOLO-ready data.yaml
with open(f"{OUTPUT}/data.yaml", "w") as f:
    yaml.dump({
        "train": rf"{OUTPUT}\train\images",
        "val": rf"{OUTPUT}\valid\images",
        "nc": len(all_classes),
        "names": all_classes
    }, f)

print(f"✅ Done! Merged {img_counter} images.")
print(f"📋 Classes: {all_classes}")
print(f"📁 Ready dataset: {OUTPUT}")