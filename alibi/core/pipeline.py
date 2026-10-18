from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from alibi.core.models import Receipt, Employee, Decision
from alibi.core.employees import get_employee
from alibi.core.policy import load_policy_rules
from alibi.core.fx import convert_currency
from alibi.core.integrity import append_audit_block, verify_chain
from alibi.core.checks.duplicates import check_duplicate_receipt
from alibi.core.checks.teleport import check_teleport_anomaly
from alibi.core.checks.group_dinner import check_group_dinner_reconciliation
from alibi.core.checks.threshold_hugging import check_threshold_hugging
from alibi.core.checks.partial_approval import compute_line_item_partial_approvals
from alibi.core.checks.math_forensics import validate_math_and_id_forensics
from alibi.core.checks.behavior import validate_behavior

class Flag(BaseModel):
    type: str  # duplicate, teleport, threshold, group_meal, forensics, behavior, extraction, policy
    severity: str  # info, warn, critical
    receipt_ids: List[str] = Field(default_factory=list)
    employee_id: str
    title: str
    explanation: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    rule_id: Optional[str] = None

def process_receipt(receipt: Receipt, context: Optional[Dict[str, Any]] = None) -> Tuple[Decision, List[Flag]]:
    context = context or {}
    flags: List[Flag] = []
    employee = get_employee(receipt.employee_id)
    if not employee:
        employee = Employee(employee_id=receipt.employee_id, name="Unknown Employee", home_city="Unknown", grade="L2")

    avg_conf = 1.0
    if receipt.confidence_scores:
        avg_conf = sum(receipt.confidence_scores.values()) / len(receipt.confidence_scores)
    
    if receipt.extraction_failed:
        flags.append(Flag(
            type="extraction", severity="critical", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Extraction Failed",
            explanation="OCR extraction failed to parse mandatory document fields.",
            evidence={"confidence": avg_conf}
        ))
    elif avg_conf < 0.75:
        flags.append(Flag(
            type="extraction", severity="warn", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Low Confidence Fields",
            explanation=f"Average confidence score {avg_conf:.2f} is below 0.75 threshold.",
            evidence={"confidence": avg_conf}
        ))

    dup = check_duplicate_receipt(receipt)
    if dup.is_duplicate and dup.message:
        flags.append(Flag(
            type="duplicate", severity="critical", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Duplicate Receipt Detected",
            explanation=dup.message, evidence={"matched_id": getattr(dup, "original_receipt_id", None)}
        ))

    math_flags = validate_math_and_id_forensics(receipt)
    for mf in math_flags:
        severity = "critical" if "MATH_FORENSIC_MISMATCH" in mf else "warn"
        flags.append(Flag(
            type="forensics", severity=severity, receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Forensic Anomaly",
            explanation=mf, evidence={}
        ))

    beh_flags = validate_behavior(receipt)
    for bf in beh_flags:
        flags.append(Flag(
            type="behavior", severity="warn", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Behavioral Flag",
            explanation=bf, evidence={}
        ))

    rules = load_policy_rules()
    approved_amount, excluded_amount, exps, cited_rules = compute_line_item_partial_approvals(receipt, rules)

    total_usd = convert_currency(receipt.total, receipt.currency, "USD")
    cap_exceeded = False
    for rule in rules:
        if rule.max_daily and total_usd > rule.max_daily:
            overrun = total_usd - rule.max_daily
            overrun_ratio = overrun / rule.max_daily
            severity = "critical" if overrun_ratio > 0.20 else "warn"
            if overrun_ratio > 0.20:
                cap_exceeded = True
            cited_rules.append(rule.rule_id)
            exps.append(f"Amount {total_usd:.2f} USD exceeds daily cap of {rule.max_daily} USD under {rule.rule_id}.")
            flags.append(Flag(
                type="policy", severity=severity, receipt_ids=[receipt.id],
                employee_id=receipt.employee_id, title="Cap Overrun",
                explanation=f"Claim exceeds daily cap under {rule.rule_id} by {overrun_ratio*100:.1f}%.",
                evidence={"total_usd": total_usd, "cap": rule.max_daily}, rule_id=rule.rule_id
            ))

    tp_msg = check_teleport_anomaly(receipt, employee)
    if tp_msg:
        flags.append(Flag(
            type="teleport", severity="critical", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Teleportation Anomaly",
            explanation=tp_msg, evidence={}
        ))

    gm_msg = check_group_dinner_reconciliation(receipt)
    if gm_msg:
        flags.append(Flag(
            type="group_meal", severity="critical", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Group Meal Overclaim",
            explanation=gm_msg, evidence={}
        ))

    th_msg = check_threshold_hugging(receipt, employee)
    if th_msg:
        flags.append(Flag(
            type="threshold", severity="warn", receipt_ids=[receipt.id],
            employee_id=receipt.employee_id, title="Threshold-Hugging Pattern",
            explanation=th_msg, evidence={}
        ))

    has_critical = any(f.severity == "critical" for f in flags)
    has_duplicate = any(f.type == "duplicate" for f in flags)

    status = "APPROVE"
    if has_duplicate:
        status = "REJECT"
        approved_amount = 0.0
        excluded_amount = receipt.total
    elif has_critical:
        status = "MANUAL_REVIEW"
    elif excluded_amount > 0:
        status = "PARTIAL_APPROVE"
    elif flags:
        status = "MANUAL_REVIEW"

    decision = Decision(
        receipt_id=receipt.id,
        status=status,
        approved_amount=approved_amount,
        excluded_amount=excluded_amount,
        cited_rules=list(set(cited_rules)),
        explanations=exps if exps else ["All policy and forensic checks passed successfully."],
        flags=[f.title + ": " + f.explanation for f in flags],
        metrics={"total_usd": total_usd, "avg_confidence": avg_conf}
    )

    try:
        append_audit_block(
            action="RECEIPT_PROCESSED",
            data={
                "receipt_id": receipt.id,
                "employee_id": receipt.employee_id,
                "merchant": receipt.merchant,
                "total": receipt.total,
                "currency": receipt.currency,
                "status": status,
                "approved_amount": approved_amount,
                "flags_count": len(flags)
            }
        )
    except Exception:
        pass

    return decision, flags

def process_month(receipts: List[Receipt], context: Optional[Dict[str, Any]] = None) -> Dict[str, Tuple[Decision, List[Flag]]]:
    results = {}
    for r in receipts:
        dec, flags = process_receipt(r, context)
        results[r.id] = (dec, flags)
    return results
