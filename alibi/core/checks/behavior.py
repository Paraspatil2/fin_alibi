from typing import List
from alibi.core.models import Receipt

def validate_behavior(receipt: Receipt) -> List[str]:
    flags = []
    # Check weekend / late night without notes
    if receipt.time:
        try:
            hour = int(receipt.time.split(":")[0])
            if hour >= 23 or hour <= 4:
                if not receipt.notes or len(receipt.notes.strip()) < 5:
                    flags.append("LATE_NIGHT_EXPENSE: Expense occurred between 11 PM and 4 AM without explanatory notes.")
        except Exception:
            pass

    # Check non-reimbursable personal items in line items
    forbidden = ["alcohol", "minibar", "movies", "personal care", "fines", "laundry"]
    for item in receipt.line_items:
        desc_lower = item.description.lower()
        for f in forbidden:
            if f in desc_lower:
                flags.append(f"FORBIDDEN_ITEM: Found restricted item '{f}' in line item '{item.description}'")

    return flags
