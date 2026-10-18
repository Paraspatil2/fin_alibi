from datasets import load_dataset
 
DATASETS = [
    "katanaml/cord",
    "abdoelsayed/AMuRD",
    "Voxel51/scanned_receipts",
    "docjay131/receipts-ocr-dataset",
   
]
 
loaded_datasets = {}
 
for dataset_id in DATASETS:
    try:
        print(f"\nLoading: {dataset_id}")
 
        dataset = load_dataset(dataset_id)
        loaded_datasets[dataset_id] = dataset
 
        print(dataset)
 
        for split in dataset:
            print(f"\nSplit: {split}")
            print("Columns:", dataset[split].column_names)
            print("Number of rows:", len(dataset[split]))
 
    except Exception as e:
        print(f"Failed to load {dataset_id}: {e}")
 
print("\nSuccessfully loaded:", list(loaded_datasets.keys()))
