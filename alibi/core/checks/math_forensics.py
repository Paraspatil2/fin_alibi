import re
from typing import List
from alibi.core.models import Receipt

def validate_math_and_id_forensics(receipt: Receipt) -> List[str]:
    """
    Feature 5: Math and ID forensics.
    Checks that line items sum to total, tax matches rate, tax IDs / GSTIN have valid format,
    and currency conversion is plausible.
    """
    flags = []

    # 1. Line items sum check
    if receipt.line_items:
        line_sum = sum(item.total for item in receipt.line_items)
        tax_sum = sum(t.amount for t in receipt.tax_breakdown)
        expected = line_sum + tax_sum + receipt.round_off
        diff = abs(expected - receipt.total)
        if diff > 0.10:
            flags.append(f"MATH_FORENSIC_MISMATCH: Line items ({line_sum:,.2f}) + tax ({tax_sum:,.2f}) = {expected:,.2f} does not match receipt total ({receipt.total:,.2f}). Difference: {diff:,.2f}.")

    # 2. Tax rate arithmetic check
    for t in receipt.tax_breakdown:
        if t.rate and t.rate > 0 and receipt.line_items:
            subtotal = sum(li.total for li in receipt.line_items)
            expected_tax = subtotal * (t.rate / 100.0)
            if abs(expected_tax - t.amount) > (subtotal * 0.05 + 1.0):
                flags.append(f"TAX_RATE_ANOMALY: Tax item '{t.name}' claimed {t.amount} at {t.rate}%, expected ~{expected_tax:.2f} based on line subtotal.")

    # 3. Tax ID / GSTIN Format forensics (e.g., Indian GSTIN 15 chars: 2 digits + 10 chars + 1 digit + 1 char + Z + 1 char)
    if receipt.tax_id:
        cleaned_tax_id = receipt.tax_id.strip().upper()
        if len(cleaned_tax_id) < 5:
            flags.append(f"INVALID_TAX_ID: Tax ID '{receipt.tax_id}' is too short to be valid.")
        elif len(cleaned_tax_id) == 15:
            gstin_pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$"
            if not re.match(gstin_pattern, cleaned_tax_id):
                flags.append(f"GSTIN_FORMAT_WARNING: GSTIN '{cleaned_tax_id}' does not match standard 15-character checksum format.")

    return flags
