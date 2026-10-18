import pytest
import os
from alibi.core.models import Receipt, LineItem, TaxBreakdownItem
from alibi.core.employees import get_employee, is_on_trip
from alibi.core.fx import convert_currency
from alibi.core.decision import evaluate_receipt
from alibi.core.integrity import verify_chain, append_audit_block
from alibi.core.extraction_pipeline import extract_receipt

def test_employee_lookup():
    emp = get_employee("EMP001")
    assert emp is not None
    assert emp.name == "Alice Smith"
    assert emp.home_city == "New York"

def test_is_on_trip():
    emp = get_employee("EMP001")
    receipt_local = Receipt(id="R1", employee_id="EMP001", merchant="Cafe", city="New York", total=20.0)
    receipt_trip = Receipt(id="R2", employee_id="EMP001", merchant="Cafe", city="Boston", total=45.0)
    assert not is_on_trip(receipt_local, emp)
    assert is_on_trip(receipt_trip, emp)

def test_fx_conversion():
    usd = convert_currency(100, "USD", "USD")
    assert usd == 100.0
    eur_to_usd = convert_currency(100, "EUR", "USD")
    assert pytest.approx(eur_to_usd, 0.01) == 110.0

def test_decision_engine_approve():
    emp = get_employee("EMP001")
    r = Receipt(
        id="REC-TEST",
        employee_id="EMP001",
        merchant="Client Restaurant",
        date="2026-10-01",
        total=50.0,
        currency="USD",
        line_items=[LineItem(description="Dinner", total=50.0)],
        client_name="Client Corp",
        confidence_scores={"total": 0.95, "date": 0.95}
    )
    decision = evaluate_receipt(r, emp)
    assert decision.status in ["APPROVE", "PARTIAL_APPROVE"]

def test_decision_engine_forbidden_item():
    emp = get_employee("EMP001")
    r = Receipt(
        id="REC-TEST-2",
        employee_id="EMP001",
        merchant="Hotel",
        date="2026-10-01",
        total=100.0,
        currency="USD",
        line_items=[
            LineItem(description="Room", total=80.0),
            LineItem(description="minibar beer", total=20.0)
        ],
        confidence_scores={"total": 0.95}
    )
    decision = evaluate_receipt(r, emp)
    assert decision.status == "PARTIAL_APPROVE"
    assert decision.excluded_amount == 20.0
    assert decision.approved_amount == 80.0

def test_audit_chain():
    append_audit_block("TEST_ACTION", {"test": True})
    assert verify_chain() is True

def test_extraction_mock():
    mock_data = {
        "id": "REC-MOCK-1",
        "employee_id": "EMP001",
        "merchant": "Mock Cafe",
        "date": "2026-10-05",
        "total": 42.50,
        "currency": "USD",
        "line_items": [{"description": "Coffee and Sandwich", "total": 42.50}],
        "confidence_scores": {"total": 0.98, "date": 0.99}
    }
    dummy_path = "alibi/data/dummy_receipt.png"
    with open(dummy_path, "wb") as f:
        f.write(b"fake image bytes")
    
    receipt = extract_receipt(dummy_path, employee_id="EMP001", mock_response=mock_data)
    assert receipt.id == "REC-MOCK-1"
    assert receipt.merchant == "Mock Cafe"
    assert receipt.total == 42.50
    assert receipt.extraction_failed is False
    
    if os.path.exists(dummy_path):
        os.remove(dummy_path)

def test_gemini_model_selection():
    from alibi.core.extraction import select_gemini_model
    model = select_gemini_model()
    assert "2.5-flash" not in model, "Deprecated gemini-2.5-flash should not be selected"
    assert "flash" in model.lower() or "pro" in model.lower()

def test_cord_offline_model():
    from alibi.core.cord_model import extract_receipt_with_trained_cord
    lines = [
        "CAFE BISTRO",
        "123 Main Street",
        "Date: 2026-10-15",
        "Coffee 4.50",
        "Croissant 5.50",
        "Tax: 1.00",
        "Total: 11.00"
    ]
    receipt = extract_receipt_with_trained_cord(lines, employee_id="EMP001", file_sha256="test12345")
    assert receipt.merchant == "CAFE BISTRO"
    assert receipt.total == 11.0
    assert receipt.extraction_failed is False
    assert len(receipt.line_items) >= 1

def test_user_receipt_extraction():
    user_img = os.path.join(os.path.dirname(__file__), "..", "data", "shared image.jpeg")
    if os.path.exists(user_img):
        receipt = extract_receipt(user_img, employee_id="EMP001")
        assert receipt.extraction_failed is False
        assert "BLABBER" in receipt.merchant.upper()
        assert receipt.total == 1855.0
        assert receipt.currency == "INR"
        assert len(receipt.line_items) == 3
        # Verify math
        items_sum = sum(li.total for li in receipt.line_items)
        taxes_sum = sum(t.amount for t in receipt.tax_breakdown)
        assert abs((items_sum + taxes_sum + receipt.round_off) - receipt.total) < 0.05

def test_duplicate_receipt_rejection():
    from alibi.core.decision import evaluate_receipt
    from alibi.core.employees import get_employee
    
    emp = get_employee("EMP001")
    # Exact duplicate submission
    dup_receipt = Receipt(
        id="REC-DUP-TEST",
        employee_id="EMP001",
        merchant="La Pino'z",
        date="2024-10-18",
        total=529.0,
        currency="INR",
        file_sha256="76fe5c81b50fdbdafa83051ab5e0d98a8e498051b8f364e07689bed77152f66e"
    )
    decision = evaluate_receipt(dup_receipt, emp)
    assert decision.status == "REJECT"
    assert decision.approved_amount == 0.0
    assert decision.excluded_amount == 529.0
    assert any("DUPLICATE_" in f for f in decision.flags)
    assert "R-DUP-01" in decision.cited_rules

def test_duplicate_ledger_entry():
    from alibi.core.ledger import add_ledger_entry
    from alibi.core.models import LedgerEntry
    # Try adding duplicate entry with same receipt_id
    entry1 = LedgerEntry(
        employee_id="EMP001",
        date="2026-10-18",
        receipt_id="REC-UNIQUE-001",
        category="Meals",
        amount=50.0,
        currency="USD",
        base_amount=50.0,
        status="APPROVE"
    )
    first_added = add_ledger_entry(entry1)
    second_added = add_ledger_entry(entry1)
    assert first_added is True or first_added is False  # depending on whether it existed
    assert second_added is False, "Second entry with identical receipt_id must be rejected"

def test_duplicate_audit_block():
    from alibi.core.integrity import append_audit_block
    try:
        # Should raise ValueError if duplicate receipt_id committed
        append_audit_block(
            action="EXPENSE_AUDITED",
            data={"receipt_id": "REC-76fe5c", "total": 529.0}
        )
        assert False, "Should have raised ValueError for duplicate block"
    except ValueError as e:
        assert "Duplicate block rejected" in str(e)


