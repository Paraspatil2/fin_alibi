import json
from pathlib import Path

ROOT = Path("cord_data/CORD")

total_images = 0
total_json = 0
matched = 0
missing_json = []
missing_images = []

for split in ["train", "dev", "test"]:
    image_dir = ROOT / split / "image"
    json_dir = ROOT / split / "json"

    images = list(image_dir.glob("*.png"))
    annotations = list(json_dir.glob("*.json"))

    total_images += len(images)
    total_json += len(annotations)

    print(f"\n{split.upper()}")
    print(f"Images: {len(images)}")
    print(f"JSON annotations: {len(annotations)}")

    for image_path in images:
        json_path = json_dir / f"{image_path.stem}.json"

        if json_path.exists():
            matched += 1
        else:
            missing_json.append(str(image_path))

    for json_path in annotations:
        image_path = image_dir / f"{json_path.stem}.png"

        if not image_path.exists():
            missing_images.append(str(json_path))

print("\n--- SUMMARY ---")
print("Total images:", total_images)
print("Total JSON files:", total_json)
print("Matched image/annotation pairs:", matched)
print("Images missing annotations:", len(missing_json))
print("Annotations missing images:", len(missing_images))

# Display one example annotation
example_files = list((ROOT / "train" / "json").glob("*.json"))

if example_files:
    with example_files[0].open(encoding="utf-8") as f:
        data = json.load(f)

    print("\nExample annotation file:", example_files[0])
    print("Top-level JSON keys:", list(data.keys()))
    print(json.dumps(data, indent=2)[:2000])
