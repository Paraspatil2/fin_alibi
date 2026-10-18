from fiftyone.utils.huggingface import load_from_hub

print("Loading scanned receipts...")
dataset = load_from_hub("Voxel51/scanned_receipts", max_samples=10)
print("Loaded successfully!")
print(dataset)
