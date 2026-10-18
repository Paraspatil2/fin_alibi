from typing import List, Dict, Any
from alibi.core.models import Receipt, Decision, PolicyRule, Employee
from alibi.core.policy import load_policy_rules
from alibi.core.fx import convert_currency
from alibi.core.checks.forensics import validate_forensics
from alibi.core.checks.behavior import validate_behavior

def evaluate_receipt(receipt: Receipt, employee: Employee) -> Decision:
    rules = load_policy_rules()
    flags = []
    flags.extend(validate_forensics(receipt))
    flags.extend(validate_behavior(receipt))

    if receipt.extraction_failed:
        return Decision(
            receipt_id=receipt.id,
            status="MANUAL_REVIEW",
            approved_amount=0.0,
            excluded_amount=receipt.total,
            cited_rules=[],
            explanations=["Receipt extraction failed. Routed to manual review."],
            flags=flags + ["EXTRACTION_FAILED"],
            metrics={}
        )

    if not receipt.date:
        return Decision(
            receipt_id=receipt.id,
            status="MANUAL_REVIEW",
            approved_amount=0.0,
            excluded_amount=receipt.total,
            cited_rules=[],
            explanations=["Missing date. Routed to manual review."],
            flags=flags + ["MISSING_DATE"],
            metrics={}
        )

    # Check confidence
    avg_conf = 1.0
    if receipt.confidence_scores:
        avg_conf = sum(receipt.confidence_scores.values()) / len(receipt.confidence_scores)
    if avg_conf < 0.75:
        flags.append(f"LOW_CONFIDENCE: Average confidence score {avg_conf:.2f} is below 0.75 threshold.")

    # Determine category rules
    cited_rules = []
    explanations = []
    approved_amount = receipt.total
    excluded_amount = 0.0

    # Inspect line items for non-reimbursable items or client rules
    forbidden_total = 0.0
    for item in receipt.line_items:
        desc_lower = item.description.lower()
        matched = False
        for rule in rules:
            for non_rev in rule.non_reimbursable_items:
                if non_rev in desc_lower and not matched:
                    forbidden_total += item.total
                    if rule.rule_id not in cited_rules:
                        cited_rules.append(rule.rule_id)
                    explanations.append(f"Excluded restricted item '{item.description}' under rule {rule.rule_id}.")
                    matched = True

    if forbidden_total > 0:
        excluded_amount += forbidden_total
        approved_amount = max(0.0, receipt.total - forbidden_total)

    # Check client name requirement for meals if applicable
    for rule in rules:
        if "Meal" in rule.category and rule.requires_client_name:
            # Check if any line item or receipt notes client
            if not receipt.client_name and any("dinner" in item.description.lower() or "lunch" in item.description.lower() for item in receipt.line_items):
                flags.append(f"MISSING_CLIENT_NAME: Rule {rule.rule_id} requires client name for client meals.")
                cited_rules.append(rule.rule_id)

    # Check daily caps converted to USD
    total_usd = convert_currency(receipt.total, receipt.currency, "USD")
    for rule in rules:
        if rule.max_daily and total_usd > rule.max_daily:
            overrun = total_usd - rule.max_daily
            if overrun / rule.max_daily > 0.20:
                flags.append(f"CAP_OVERRUN_EXCESSIVE: Amount exceeds daily cap by > 20% under {rule.rule_id}.")
            cited_rules.append(rule.rule_id)
            explanations.append(f"Amount {total_usd:.2f} USD exceeds daily cap of {rule.max_daily} USD under {rule.rule_id}.")

    status = "APPROVE"
    has_duplicate = any("DUPLICATE_" in f for f in flags)
    
    if has_duplicate:
        status = "REJECT"
        approved_amount = 0.0
        excluded_amount = receipt.total
        if "R-DUP-01" not in cited_rules:
            cited_rules.append("R-DUP-01")
        explanations.insert(0, "Claim REJECTED: Duplicate receipt submission detected. Dual-claiming previously processed expenses violates corporate policy R-DUP-01.")
    elif flags:
        # Check if serious flags trigger manual review
        serious_triggers = ["EXTRACTION_FAILED", "MISSING_DATE", "LOW_CONFIDENCE", "CAP_OVERRUN_EXCESSIVE", "MATH_MISMATCH"]
        if any(any(st in f for st in serious_triggers) for f in flags):
            status = "MANUAL_REVIEW"
        elif forbidden_total > 0:
            status = "PARTIAL_APPROVE"
        else:
            status = "MANUAL_REVIEW"
    elif forbidden_total > 0:
        status = "PARTIAL_APPROVE"

    return Decision(
        receipt_id=receipt.id,
        status=status,
        approved_amount=approved_amount,
        excluded_amount=excluded_amount,
        cited_rules=list(set(cited_rules)),
        explanations=explanations if explanations else ["All policy and forensic checks passed successfully."],
        flags=flags,
        metrics={"total_usd": total_usd, "avg_confidence": avg_conf}
    )
