from typing import List, Optional
from alibi.core.models import Receipt

def check_group_dinner_reconciliation(receipt: Receipt) -> Optional[str]:
    """
    Feature 2: Group-dinner reconciliation.
    If a group dinner is claimed in full by multiple employees or lacks attendee split,
    flags overclaim or unallocated group expenses.
    """
    desc_lower = (receipt.merchant + " " + " ".join(item.description for item in receipt.line_items)).lower()
    is_dinner = any(k in desc_lower for k in ["dinner", "restaurant", "buffet", "group", "banquet", "cafe", "bistro", "bar & grill"])
    
    if not is_dinner:
        return None

    # Check attendee count or list
    attendee_count = len(receipt.attendees) if receipt.attendees else 1
    
    # If total is large (> 3000 INR or ~ $40) and attendees is 1 or empty, flag potential group unallocated
    if receipt.total > 3000 and attendee_count <= 1:
        return f"GROUP_DINNER_OVERCLAIM: Large dining expense ({receipt.total:,.2f} {receipt.currency}) claimed by single employee without attendee split list. Suspected group meal overclaim."

    return None
