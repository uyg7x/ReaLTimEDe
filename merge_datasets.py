import os, shutil, yaml
from pathlib import Path

ROOT = Path.cwd()
OUTPUT = ROOT / "final_merged_dataset"
print(f"🔍 Scanning: {ROOT}")

# 1. Create clean output structure
for split in ["train", "valid"]:
    (OUTPUT / split / "images").mkdir(parents=True, exist_ok=True)
    (OUTPUT / split / "labels").mkdir(parents=True, exist_ok=True)

# 2. Find ALL subfolders that contain a data.yaml (YOLO format indicator)
dataset_folders = [d for d in ROOT.iterdir() if d.is_dir() and (d / "data.yaml").exists()]
print(f"📂 Found {len(dataset_folders)} dataset folders: {[d.name for d in dataset_folders]}")

global_classes = []
dataset_class_maps = {}

for ds in dataset_folders:
    with open(ds / "data.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    names = cfg.get("names", [])
    if isinstance(names, dict):
        names = list(names.values())
    print(f"   📋 {ds.name}: {len(names)} classes -> {names}")
    
    dataset_class_maps[ds] = {}
    for i, cls in enumerate(names):
        if cls not in global_classes:
            global_classes.append(cls)
        dataset_class_maps[ds][i] = global_classes.index(cls)

print(f"\n🌍 Global classes ({len(global_classes)}): {global_classes}")

# 3. Merge images & remap labels
img_counter = 0
for ds in dataset_folders:
    cls_map = dataset_class_maps[ds]
    
    # Handle both 'valid' and 'val' naming
    for split in ["train", "valid", "val"]:
        img_dir = ds / split / "images"
        lbl_dir = ds / split / "labels"
        
        if not img_dir.exists() or not lbl_dir.exists():
            if split != "val":  # Only warn once per folder
                print(f"   ⚠️ {ds.name}: missing {split}/images or {split}/labels")
            continue
            
        for img in img_dir.glob("*.jpg"):
            lbl = lbl_dir / f"{img.stem}.txt"
            if not lbl.exists(): continue
            
            new_name = f"{img_counter:06d}"
            shutil.copy2(img, OUTPUT / split.replace("val", "valid") / "images" / f"{new_name}.jpg")
            
            with open(lbl, "r", encoding="utf-8") as f: lines = f.readlines()
            out_lbl = OUTPUT / split.replace("val", "valid") / "labels" / f"{new_name}.txt"
            with open(out_lbl, "w", encoding="utf-8") as f:
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        old_cls = int(parts[0])
                        new_cls = cls_map.get(old_cls, old_cls)
                        f.write(f"{new_cls} {' '.join(parts[1:])}\n")
                    else:
                        f.write(line + "\n")
            img_counter += 1

# 4. Generate unified data.yaml
data_yaml = {
    "train": str((OUTPUT / "train" / "images").absolute()),
    "val": str((OUTPUT / "valid" / "images").absolute()),
    "nc": len(global_classes),
    "names": global_classes
}
with open(OUTPUT / "data.yaml", "w", encoding="utf-8") as f:
    yaml.dump(data_yaml, f, default_flow_style=False)

print(f"\n✅ SUCCESS! Merged {img_counter} images into: {OUTPUT}")
print("💡 Next step: Run the training command provided below.")
