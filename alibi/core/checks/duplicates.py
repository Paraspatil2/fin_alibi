import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rapidfuzz import fuzz

from alibi.core.models import Receipt
from alibi.core.ledger import load_ledger
from alibi.core.integrity import load_audit_chain

@dataclass
class DuplicateMatch:
    is_duplicate: bool = False
    match_type: Optional[str] = None  # "EXACT_FILE", "INVOICE_NUMBER", "SEMANTIC_TRANSACTION", "RECEIPT_ID"
    original_receipt_id: Optional[str] = None
    original_employee_id: Optional[str] = None
    original_date: Optional[str] = None
    original_total: Optional[float] = None
    original_merchant: Optional[str] = None
    block_index: Optional[int] = None
    message: Optional[str] = None

    @property
    def matched_id(self) -> Optional[str]:
        return self.original_receipt_id

def get_all_historical_receipts() -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    by_sha: Dict[str, Dict[str, Any]] = {}

    chain = load_audit_chain()
    for block in chain:
        if block.get("action") == "EXPENSE_AUDITED":
            d = block.get("data", {})
            r_id = d.get("receipt_id")
            f_sha = d.get("file_sha256")
            record = {
                "id": r_id,
                "employee_id": d.get("employee_id"),
                "merchant": d.get("merchant"),
                "total": float(d.get("total", 0.0)),
                "currency": d.get("currency", "USD"),
                "file_sha256": f_sha,
                "tax_id": d.get("tax_id"),
                "bill_no": d.get("bill_no"),
                "date": d.get("date"),
                "block_index": block.get("index"),
                "source": "audit_chain"
            }
            if r_id:
                by_id[r_id] = record
            if f_sha:
                by_sha[f_sha] = record

    ledger_entries = load_ledger()
    for entry in ledger_entries:
        if entry.receipt_id in by_id:
            if not by_id[entry.receipt_id].get("date"):
                by_id[entry.receipt_id]["date"] = entry.date
            if not by_id[entry.receipt_id].get("employee_id"):
                by_id[entry.receipt_id]["employee_id"] = entry.employee_id
        else:
            by_id[entry.receipt_id] = {
                "id": entry.receipt_id,
                "employee_id": entry.employee_id,
                "merchant": getattr(entry, "merchant", "Unknown Merchant"),
                "total": entry.amount,
                "currency": entry.currency,
                "date": entry.date,
                "file_sha256": None,
                "tax_id": None,
                "bill_no": None,
                "block_index": None,
                "source": "ledger"
            }

    extracted_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "extracted")
    if os.path.exists(extracted_dir):
        try:
            for fname in os.listdir(extracted_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(extracted_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as jf:
                        c_data = json.load(jf)
                        c_id = c_data.get("id")
                        c_sha = c_data.get("file_sha256")
                        
                        target = by_id.get(c_id) or by_sha.get(c_sha)
                        if target:
                            if not target.get("date"):
                                target["date"] = c_data.get("date")
                            if not target.get("tax_id"):
                                target["tax_id"] = c_data.get("tax_id")
                            if not target.get("bill_no"):
                                target["bill_no"] = c_data.get("bill_no")
                            if not target.get("merchant") or target["merchant"] == "Unknown Merchant":
                                target["merchant"] = c_data.get("merchant")
                            if not target.get("file_sha256"):
                                target["file_sha256"] = c_sha
        except Exception:
            pass

    sample_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_receipts.json")
    if os.path.exists(sample_file):
        try:
            with open(sample_file, "r", encoding="utf-8") as sf:
                s_data = json.load(sf)
                for item in s_data:
                    s_id = item.get("id")
                    if s_id and s_id not in by_id:
                        by_id[s_id] = {
                            "id": s_id,
                            "employee_id": item.get("employee_id"),
                            "merchant": item.get("merchant"),
                            "total": float(item.get("total", 0.0)),
                            "currency": item.get("currency", "USD"),
                            "date": item.get("date"),
                            "tax_id": item.get("tax_id"),
                            "bill_no": item.get("bill_no"),
                            "file_sha256": None,
                            "block_index": None,
                            "source": "sample_receipts"
                        }
        except Exception:
            pass

    return list(by_id.values())

def check_duplicate_receipt(receipt: Receipt) -> DuplicateMatch:
    if not receipt or receipt.extraction_failed or receipt.total <= 0:
        return DuplicateMatch(is_duplicate=False)

    history = get_all_historical_receipts()

    for prev in history:
        prev_id = prev.get("id")
        prev_emp = prev.get("employee_id")
        prev_merchant = str(prev.get("merchant", ""))
        prev_total = float(prev.get("total", 0.0))
        prev_date = prev.get("date")
        prev_file_sha = prev.get("file_sha256")
        prev_tax_id = prev.get("tax_id")
        prev_bill_no = prev.get("bill_no")
        block_idx = prev.get("block_index")
        block_info = f" in Block #{block_idx}" if block_idx is not None else ""

        if receipt.file_sha256 and prev_file_sha and receipt.file_sha256 == prev_file_sha:
            msg = (
                f"DUPLICATE_FILE: Exact file hash already submitted in receipt '{prev_id}'{block_info} "
                f"by {prev_emp or 'employee'}."
            )
            return DuplicateMatch(
                is_duplicate=True,
                match_type="EXACT_FILE",
                original_receipt_id=prev_id,
                original_employee_id=prev_emp,
                original_date=prev_date,
                original_total=prev_total,
                original_merchant=prev_merchant,
                block_index=block_idx,
                message=msg
            )

        if (
            receipt.bill_no and prev_bill_no and
            receipt.tax_id and prev_tax_id and
            receipt.bill_no.strip().upper() == prev_bill_no.strip().upper() and
            receipt.tax_id.strip().upper() == prev_tax_id.strip().upper()
        ):
            msg = (
                f"DUPLICATE_INVOICE: Tax ID '{receipt.tax_id}' and Bill No '{receipt.bill_no}' "
                f"already processed in receipt '{prev_id}'{block_info}."
            )
            return DuplicateMatch(
                is_duplicate=True,
                match_type="INVOICE_NUMBER",
                original_receipt_id=prev_id,
                original_employee_id=prev_emp,
                original_date=prev_date,
                original_total=prev_total,
                original_merchant=prev_merchant,
                block_index=block_idx,
                message=msg
            )

        if receipt.id and prev_id and receipt.id == prev_id and not receipt.id.startswith("REC-NEW"):
            msg = f"DUPLICATE_RECEIPT_ID: Receipt ID '{receipt.id}' has already been processed{block_info}."
            return DuplicateMatch(
                is_duplicate=True,
                match_type="RECEIPT_ID",
                original_receipt_id=prev_id,
                original_employee_id=prev_emp,
                original_date=prev_date,
                original_total=prev_total,
                original_merchant=prev_merchant,
                block_index=block_idx,
                message=msg
            )

        if (
            receipt.total > 0 and prev_total > 0 and
            abs(receipt.total - prev_total) < 0.05 and
            receipt.date and prev_date and receipt.date == prev_date
        ):
            sim_set = fuzz.token_set_ratio(receipt.merchant.lower(), prev_merchant.lower())
            sim_part = fuzz.partial_ratio(receipt.merchant.lower(), prev_merchant.lower())
            sim = max(sim_set, sim_part)
            if sim >= 70 or (receipt.bill_no and prev_bill_no and receipt.bill_no == prev_bill_no):
                msg = (
                    f"DUPLICATE_EXPENSE: Identical transaction detected for '{receipt.merchant}' "
                    f"on {receipt.date} for {receipt.total:,.2f} {receipt.currency} (already recorded in {prev_id}{block_info})."
                )
                return DuplicateMatch(
                    is_duplicate=True,
                    match_type="SEMANTIC_TRANSACTION",
                    original_receipt_id=prev_id,
                    original_employee_id=prev_emp,
                    original_date=prev_date,
                    original_total=prev_total,
                    original_merchant=prev_merchant,
                    block_index=block_idx,
                    message=msg
                )

    return DuplicateMatch(is_duplicate=False)
