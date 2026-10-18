from typing import List
from alibi.core.models import Receipt
from alibi.core.checks.duplicates import check_duplicate_receipt

def validate_forensics(receipt: Receipt) -> List[str]:
    flags = []
    
    # 1. Duplicate receipt check across ledger, audit chain, and submitted database
    dup = check_duplicate_receipt(receipt)
    if dup.is_duplicate and dup.message:
        flags.append(dup.message)

    # 2. Line item sum check
    if receipt.line_items:
        line_sum = sum(item.total for item in receipt.line_items)
        tax_sum = sum(t.amount for t in receipt.tax_breakdown)
        expected = line_sum + tax_sum + receipt.round_off
        if abs(expected - receipt.total) > 0.05:
            flags.append(f"MATH_MISMATCH: Line items sum ({line_sum:.2f}) + tax ({tax_sum:.2f}) + round_off ({receipt.round_off:.2f}) = {expected:.2f}, but total is {receipt.total:.2f}")
    
    # 3. Tax ID format check
    if receipt.tax_id and len(receipt.tax_id.strip()) < 5:
        flags.append("SUSPICIOUS_TAX_ID: Tax ID is unusually short.")

    # 4. Missing date flag
    if not receipt.date:
        flags.append("MISSING_DATE: Receipt lacks date, requires manual review.")

    return flags
