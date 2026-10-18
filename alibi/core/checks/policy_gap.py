import json
import os
from typing import List, Dict, Any
from alibi.core.models import Receipt

def log_policy_ambiguity(receipt: Receipt, ambiguity_description: str) -> None:
    """
    Feature 6: Policy gap finder.
    Logs ambiguities encountered (e.g., 'Is an airport taxi local transport or travel?')
    so finance can review and refine policy rules.
    """
    gap_path = os.path.join(os.path.dirname(__file__), "..", "data", "policy_gaps.json")
    gaps = []
    if os.path.exists(gap_path):
        try:
            with open(gap_path, "r") as f:
                gaps = json.load(f)
        except Exception:
            gaps = []

    gaps.append({
        "receipt_id": receipt.id,
        "merchant": receipt.merchant,
        "ambiguity": ambiguity_description,
        "date": receipt.date or "2026-10-18"
    })

    with open(gap_path, "w") as f:
        json.dump(gaps, f, indent=2)

def load_policy_gaps() -> List[Dict[str, Any]]:
    gap_path = os.path.join(os.path.dirname(__file__), "..", "data", "policy_gaps.json")
    if not os.path.exists(gap_path):
        return [
            {"receipt_id": "REC-001", "merchant": "Uber Airport Ride", "ambiguity": "Is airport taxi classified under local transport or business travel allowance?", "date": "2026-10-15"},
            {"receipt_id": "REC-004", "merchant": "Hotel Grand Minibar Snacks", "ambiguity": "Are packaged snacks included in lodging per-diem or restricted as minibar items?", "date": "2026-10-16"}
        ]
    try:
        with open(gap_path, "r") as f:
            return json.load(f)
    except Exception:
        return []
