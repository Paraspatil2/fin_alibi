import os
import sys
import argparse
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from alibi.core.extraction_pipeline import extract_receipt

def main():
    parser = argparse.ArgumentParser(description="Extract receipts from a folder.")
    parser.add_argument("--folder", type=str, required=True, help="Path to folder containing receipt files.")
    parser.add_argument("--employee", type=str, default="EMP001", help="Default employee ID.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of receipts to extract.")
    args = parser.parse_args()

    if not os.path.exists(args.folder):
        print(f"Folder not found: {args.folder}")
        return


    records = []
    files = [f for f in sorted(os.listdir(args.folder)) if os.path.isfile(os.path.join(args.folder, f))]
    if args.limit:
        files = files[:args.limit]

    for filename in files:
        filepath = os.path.join(args.folder, filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".pdf", ".png", ".jpg", ".jpeg"]:
            print(f"Extracting {filename}...")
            receipt = extract_receipt(filepath, employee_id=args.employee)
            avg_conf = sum(receipt.confidence_scores.values()) / len(receipt.confidence_scores) if receipt.confidence_scores else 1.0
            records.append({
                "ID": receipt.id,
                "Merchant": receipt.merchant,
                "Date": receipt.date,
                "Total": receipt.total,
                "Currency": receipt.currency,
                "Extraction Failed": receipt.extraction_failed,
                "Avg Confidence": round(avg_conf, 2)
            })

    df = pd.DataFrame(records)
    print("\nExtraction Summary Table:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
