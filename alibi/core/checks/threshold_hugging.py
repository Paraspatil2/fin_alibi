from typing import Optional
from alibi.core.models import Receipt, Employee
from alibi.core.fx import convert_currency

def check_threshold_hugging(receipt: Receipt, employee: Employee) -> Optional[str]:
    """
    Feature 3: Threshold-hugging radar.
    Counts claims sitting just under auto-approval limits (e.g. 90% - 99% of daily cap)
    and flags patterns of intentional threshold hugging.
    """
    # Daily cap for meals is $100 (~8300 INR), lodging is $250 (~20750 INR), transport is $150 (~12450 INR)
    limit_usd = 100.0
    cat_lower = receipt.merchant.lower()
    if "hotel" in cat_lower or "inn" in cat_lower or "stay" in cat_lower:
        limit_usd = 250.0
    elif "taxi" in cat_lower or "uber" in cat_lower or "flight" in cat_lower or "train" in cat_lower:
        limit_usd = 150.0

    total_usd = convert_currency(receipt.total, receipt.currency, "USD")
    ratio = total_usd / limit_usd

    if 0.90 <= ratio < 1.00:
        return f"THRESHOLD_HUGGING: Claim total ({total_usd:.2f} USD) sits at {ratio*100:.1f}% of the policy threshold ({limit_usd} USD), indicating deliberate sub-limit optimization."

    return None
