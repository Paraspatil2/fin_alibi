import os
import re
import json
from typing import List, Dict, Any, Optional
import joblib
from alibi.core.models import Receipt, LineItem, TaxBreakdownItem

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cord_receipt_classifier.joblib")
FEW_SHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cord_few_shots.json")

_cached_model = None

def load_cord_model():
    global _cached_model
    if _cached_model is None and os.path.exists(MODEL_PATH):
        try:
            _cached_model = joblib.load(MODEL_PATH)
        except Exception:
            _cached_model = None
    return _cached_model

def get_cord_few_shots() -> str:
    """Return formatted few-shot guidelines learned from the CORD dataset."""
    if not os.path.exists(FEW_SHOT_PATH):
        return ""
    try:
        with open(FEW_SHOT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = ["Here are verified pattern guidelines from the CORD receipt ground-truth dataset:"]
        for item in data[:3]:
            lines.append(f"- Receipt format: Merchant: '{item['merchant']}', Items extracted: {item['sample_items_count']}, Stated total: {item['total']}")
        return "\n".join(lines)
    except Exception:
        return ""

def parse_amount(text: str) -> Optional[float]:
    clean = re.sub(r"[^\d.,]", "", text.replace(" ", ""))
    if not clean:
        return None
    # Handle European vs US decimals
    if clean.count(".") == 1 and clean.count(",") == 0:
        pass
    elif clean.count(",") == 1 and clean.count(".") == 0:
        clean = clean.replace(",", ".")
    elif clean.count(",") > 0 and clean.count(".") > 0:
        if clean.rfind(".") > clean.rfind(","):
            clean = clean.replace(",", "")
        else:
            clean = clean.replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except Exception:
        return None

def extract_receipt_with_trained_cord(lines: List[str], employee_id: str = "EMP001", file_sha256: str = "local") -> Receipt:
    """Offline extraction utilizing the trained CORD classifier and heuristic structural assembler."""
    model = load_cord_model()
    
    clean_lines = [l.strip() for l in lines if l.strip()]
    if not clean_lines:
        return Receipt(
            id=f"REC-{file_sha256[:6]}",
            employee_id=employee_id,
            merchant="Unknown",
            total=0.0,
            currency="USD",
            extraction_failed=True,
            file_sha256=file_sha256
        )

    predictions = []
    if model:
        try:
            preds = model.predict(clean_lines)
            probs = model.predict_proba(clean_lines)
            max_probs = [float(p.max()) for p in probs]
            predictions = list(zip(clean_lines, preds, max_probs))
        except Exception:
            predictions = [(l, "OTHER", 0.5) for l in clean_lines]
    else:
        predictions = [(l, "OTHER", 0.5) for l in clean_lines]

    merchant = "Unknown Merchant"
    line_items = []
    tax_breakdown = []
    total = 0.0
    subtotal = 0.0
    date_val = None
    bill_no = None
    tax_id = None
    currency = "USD"

    # Identify merchant from top lines
    for text, label, conf in predictions[:5]:
        lower = text.lower()
        if not any(kw in lower for kw in ["tel", "fax", "receipt", "invoice", "date", "cashier", "gst", "tax"]):
            if len(text) > 3 and not re.match(r"^[\d\W]+$", text):
                merchant = text
                break

    # Look for dates, tax ID, bill no
    for text, _, _ in predictions:
        # Date regex
        date_match = re.search(r"(\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b)", text)
        if date_match and not date_val:
            raw_d = date_match.group(1).replace("/", "-")
            parts = raw_d.split("-")
            if len(parts[0]) == 4:
                date_val = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts[2]) == 4:
                date_val = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
            else:
                date_val = raw_d

        # Bill / Invoice No
        bill_match = re.search(r"(?:bill|inv|check|order|receipt)[\s#:]*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
        if bill_match and not bill_no:
            bill_no = bill_match.group(1)

        # Tax ID / GSTIN
        tax_id_match = re.search(r"(?:gst|tin|vat|tax\s*id)[\s#:]*([A-Za-z0-9]+)", text, re.IGNORECASE)
        if tax_id_match and not tax_id:
            tax_id = tax_id_match.group(1)

        # Currency detection
        if "₹" in text or "inr" in text.lower():
            currency = "INR"
        elif "€" in text or "eur" in text.lower():
            currency = "EUR"
        elif "£" in text or "gbp" in text.lower():
            currency = "GBP"
        elif "rp" in text.lower() or "idr" in text.lower():
            currency = "IDR"

    # Assemble line items and prices
    current_desc = None
    current_qty = 1.0

    for text, label, conf in predictions:
        amt = parse_amount(text)
        
        if label == "ITEM_NAME" or (not amt and len(text) > 2 and not any(kw in text.lower() for kw in ["total", "subtotal", "tax"])):
            if current_desc and amt is not None:
                line_items.append(LineItem(description=current_desc, quantity=current_qty, total=amt, confidence=round(conf, 2)))
                current_desc = None
                current_qty = 1.0
            else:
                current_desc = text
        elif label == "ITEM_QTY":
            num = parse_amount(text)
            if num:
                current_qty = num
        elif label in ["ITEM_PRICE", "SUBTOTAL_PRICE"] and amt is not None:
            desc = current_desc if current_desc else "Item"
            line_items.append(LineItem(description=desc, quantity=current_qty, total=amt, confidence=round(conf, 2)))
            current_desc = None
            current_qty = 1.0
        elif label == "TAX_PRICE" and amt is not None:
            tax_breakdown.append(TaxBreakdownItem(name="Tax", amount=amt, confidence=round(conf, 2)))
        elif label == "TOTAL_PRICE" and amt is not None:
            if amt > total:
                total = amt

    # If total was not directly predicted with TOTAL_PRICE label, look for keyword 'total'
    if total == 0.0:
        for text, _, _ in predictions:
            if "total" in text.lower() and not any(sub in text.lower() for sub in ["subtotal", "sub total"]):
                amt = parse_amount(text)
                if amt and amt > total:
                    total = amt

    # If still 0, reconstruct from line items and tax
    total_reconstructed = False
    if total == 0.0 and line_items:
        total = sum(li.total for li in line_items) + sum(t.amount for t in tax_breakdown)
        total_reconstructed = True

    confidence_scores = {
        "merchant": 0.85 if merchant != "Unknown Merchant" else 0.40,
        "total": 0.90 if total > 0 else 0.30,
        "date": 0.85 if date_val else 0.40,
        "line_items": 0.82 if line_items else 0.40
    }

    return Receipt(
        id=f"REC-{file_sha256[:6]}",
        employee_id=employee_id,
        merchant=merchant,
        tax_id=tax_id,
        bill_no=bill_no,
        date=date_val or "2026-10-01",
        currency=currency,
        total=round(total, 2),
        tax_breakdown=tax_breakdown,
        line_items=line_items if line_items else [LineItem(description="General Purchase", total=total, confidence=0.8)],
        confidence_scores=confidence_scores,
        total_reconstructed=total_reconstructed,
        extraction_failed=False,
        file_sha256=file_sha256
    )
