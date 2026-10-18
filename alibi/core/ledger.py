import json
import os
from typing import List, Dict, Any, Optional
from alibi.core.models import LedgerEntry

LEDGER_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "ledger_db.json")

def load_ledger() -> List[LedgerEntry]:
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE, "r") as f:
        try:
            data = json.load(f)
            seen_ids = set()
            unique_entries = []
            for item in data:
                entry = LedgerEntry(**item)
                if entry.receipt_id not in seen_ids:
                    seen_ids.add(entry.receipt_id)
                    unique_entries.append(entry)
            return unique_entries
        except Exception:
            return []

def save_ledger(entries: List[LedgerEntry]):
    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
    seen_ids = set()
    unique_entries = []
    for e in entries:
        if e.receipt_id not in seen_ids:
            seen_ids.add(e.receipt_id)
            unique_entries.append(e)
            
    with open(LEDGER_FILE, "w") as f:
        json.dump([e.dict() if hasattr(e, "dict") else e.model_dump() for e in unique_entries], f, indent=2)

def add_ledger_entry(entry: LedgerEntry) -> bool:
    """
    Appends a new ledger entry. Returns False if entry already exists (prevents duplicates).
    """
    entries = load_ledger()
    for existing in entries:
        if existing.receipt_id == entry.receipt_id:
            return False
    entries.append(entry)
    save_ledger(entries)
    return True

def recompute(employee_id: str, date_str: str) -> Dict[str, Any]:
    entries = load_ledger()
    month_prefix = date_str[:7]
    emp_entries = [e for e in entries if e.employee_id == employee_id and e.date.startswith(month_prefix)]
    totals_by_category = {}
    for e in emp_entries:
        totals_by_category[e.category] = totals_by_category.get(e.category, 0.0) + e.base_amount
    return {
        "employee_id": employee_id,
        "month": month_prefix,
        "totals_by_category": totals_by_category,
        "entry_count": len(emp_entries)
    }
