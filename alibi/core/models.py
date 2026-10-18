from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: float
    category: Optional[str] = None
    confidence: Optional[float] = None

class TaxBreakdownItem(BaseModel):
    name: str
    rate: Optional[float] = None
    amount: float
    confidence: Optional[float] = None

class Receipt(BaseModel):
    id: str
    employee_id: str
    merchant: str
    tax_id: Optional[str] = None
    bill_no: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    time: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    currency: str = "USD"
    total: float
    tax_breakdown: List[TaxBreakdownItem] = Field(default_factory=list)
    round_off: float = 0.0
    payment_method: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    attendees: List[str] = Field(default_factory=list)
    client_name: Optional[str] = None
    notes: Optional[str] = None
    trip_id: Optional[str] = None
    channel: Optional[str] = None
    submitted_at: Optional[str] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    total_reconstructed: bool = False
    extraction_failed: bool = False
    file_sha256: Optional[str] = None

class Employee(BaseModel):
    employee_id: str
    name: str
    home_city: str
    grade: str

class PolicyRule(BaseModel):
    rule_id: str
    category: str
    max_daily: Optional[float] = None
    max_per_item: Optional[float] = None
    allowed_grades: List[str] = Field(default_factory=list)
    non_reimbursable_items: List[str] = Field(default_factory=list)
    requires_client_name: bool = False
    requires_attendee_count: bool = False
    description: str

class Decision(BaseModel):
    receipt_id: str
    status: str  # APPROVE, PARTIAL_APPROVE, REJECT, MANUAL_REVIEW
    approved_amount: float
    excluded_amount: float
    cited_rules: List[str] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

class LedgerEntry(BaseModel):
    employee_id: str
    date: str
    receipt_id: str
    category: str
    amount: float
    currency: str
    base_amount: float  # in standard currency e.g. USD
    status: str
