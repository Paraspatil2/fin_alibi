from typing import List, Tuple
from alibi.core.models import Receipt, PolicyRule

def compute_line_item_partial_approvals(receipt: Receipt, rules: List[PolicyRule]) -> Tuple[float, float, List[str], List[str]]:
    """
    Feature 4: Line-item partial approvals.
    Instead of 'rejected', it calculates exactly approved vs excluded itemized breakdown
    with clause explanations (e.g., 'approved ₹3,200 of ₹4,100; ₹900 of alcohol excluded per clause 4.2').
    """
    approved_amount = 0.0
    excluded_amount = 0.0
    explanations = []
    cited_rules = []

    non_reimbursable_keywords = []
    for r in rules:
        for item in r.non_reimbursable_items:
            non_reimbursable_keywords.append((item.lower(), r.rule_id))

    if not receipt.line_items:
        # If no line items, treat whole total as approved unless general rule applies
        return receipt.total, 0.0, [], []

    for li in receipt.line_items:
        desc_lower = li.description.lower()
        matched_restriction = None
        matched_rule = None
        for keyword, r_id in non_reimbursable_keywords:
            if keyword in desc_lower:
                matched_restriction = keyword
                matched_rule = r_id
                break

        if matched_restriction:
            excluded_amount += li.total
            explanations.append(f"Excluded {li.total:,.2f} {receipt.currency} for '{li.description}' ({matched_restriction} excluded per rule {matched_rule}).")
            if matched_rule not in cited_rules:
                cited_rules.append(matched_rule)
        else:
            approved_amount += li.total

    # Include tax & round off proportionally or directly to approved
    # Simple logic: tax is approved if items are approved
    return approved_amount, excluded_amount, explanations, cited_rules
