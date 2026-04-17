import cv2, os, random
from pathlib import Path

IMG_DIR = "wildlife_dataset/train/images"
OUT_DIR = "wildlife_dataset/train/images_aug"
os.makedirs(OUT_DIR, exist_ok=True)

def augment(img_path, copies=5):
    img = cv2.imread(img_path)
    if img is None: return
    for i in range(copies):
        aug = img.copy()
        # 1. Flip
        if random.random() > 0.5: aug = cv2.flip(aug, 1)
        # 2. Brightness/Contrast
        alpha = random.uniform(0.7, 1.3)
        beta = random.randint(-20, 20)
        aug = cv2.convertScaleAbs(aug, alpha=alpha, beta=beta)
        # 3. Blur (motion/distance simulation)
        if random.random() > 0.6:
            aug = cv2.GaussianBlur(aug, (3,3), 0)
        # 4. Noise
        if random.random() > 0.7:
            noise = np.random.normal(0, 15, aug.shape).astype(np.uint8)
            aug = cv2.add(aug, noise)
        # Save
        name = Path(img_path).stem + f"_aug{i}" + Path(img_path).suffix
        cv2.imwrite(os.path.join(OUT_DIR, name), aug)

print("🔄 Augmenting images...")
for img in Path(IMG_DIR).glob("*.jpg"):
    augment(str(img), copies=6)
print(f"✅ Done! Saved to {OUT_DIR}/")
print("💡 Now copy these into your original train/images/ folder and retrain.")