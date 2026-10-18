import os
import json
from alibi.core.models import Receipt
from alibi.core.repository import save_receipt_and_evaluate

def seed_demo_data():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "alibi", "data", "sample_receipts.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            data = json.load(f)
            for item in data:
                r = Receipt(**item)
                save_receipt_and_evaluate(r)
    print("Demo data seeded successfully into SQLite repository.")

if __name__ == "__main__":
    seed_demo_data()
