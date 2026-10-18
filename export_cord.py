import csv
import json
from pathlib import Path

ROOT = Path("cord_data/CORD")
OUTPUT = Path("cord_receipts.csv")

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "split",
            "receipt_id",
            "image_path",
            "category",
            "text",
            "group_id",
            "is_key",
        ],
    )
    writer.writeheader()

    for split in ["train", "dev", "test"]:
        json_dir = ROOT / split / "json"
        image_dir = ROOT / split / "image"

        for annotation_path in sorted(json_dir.glob("*.json")):
            with annotation_path.open(encoding="utf-8") as jf:
                data = json.load(jf)

            image_path = image_dir / f"{annotation_path.stem}.png"

            for line in data.get("valid_line", []):
                category = line.get("category", "")
                group_id = line.get("group_id", "")

                for word in line.get("words", []):
                    writer.writerow({
                        "split": split,
                        "receipt_id": annotation_path.stem,
                        "image_path": str(image_path),
                        "category": category,
                        "text": word.get("text", ""),
                        "group_id": group_id,
                        "is_key": word.get("is_key", ""),
                    })

print(f"Exported annotation rows to: {OUTPUT}")
