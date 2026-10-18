import os
import json
import pytest
from alibi.core.models import Receipt
from alibi.core.repository import save_receipt_and_evaluate, get_all_receipts, get_decision, get_flags
from alibi.core.pipeline import process_month
from alibi.core.integrity import verify_chain

def test_integration_pipeline_and_demo():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_receipts.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            items = json.load(f)
            receipts = [Receipt(**item) for item in items]
            
            results = process_month(receipts)
            assert len(results) == len(receipts)
            
            for r in receipts:
                save_receipt_and_evaluate(r)
                dec, flags = results[r.id]
                assert dec is not None
                assert dec.status in ["APPROVE", "PARTIAL_APPROVE", "MANUAL_REVIEW", "REJECT"]

            assert verify_chain() is True
