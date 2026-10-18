import sqlite3
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from alibi.core.models import Receipt, Decision, Employee, LineItem, TaxBreakdownItem
from alibi.core.pipeline import process_receipt, Flag

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "alibi.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id TEXT PRIMARY KEY,
            employee_id TEXT,
            merchant TEXT,
            tax_id TEXT,
            bill_no TEXT,
            date TEXT,
            time TEXT,
            city TEXT,
            currency TEXT,
            total REAL,
            data_json TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            receipt_id TEXT PRIMARY KEY,
            status TEXT,
            approved_amount REAL,
            excluded_amount REAL,
            cited_rules TEXT,
            explanations TEXT,
            flags TEXT,
            metrics TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            severity TEXT,
            receipt_id TEXT,
            employee_id TEXT,
            title TEXT,
            explanation TEXT,
            evidence TEXT,
            rule_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_receipt_and_evaluate(receipt: Receipt) -> Tuple[Decision, List[Flag]]:
    init_db()
    decision, flags = process_receipt(receipt)

    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT OR REPLACE INTO receipts (id, employee_id, merchant, tax_id, bill_no, date, time, city, currency, total, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            receipt.id, receipt.employee_id, receipt.merchant, receipt.tax_id, receipt.bill_no,
            receipt.date, receipt.time, receipt.city, receipt.currency, receipt.total,
            receipt.model_dump_json() if hasattr(receipt, "model_dump_json") else json.dumps(receipt.dict())
        ))

        c.execute("""
            INSERT OR REPLACE INTO decisions (receipt_id, status, approved_amount, excluded_amount, cited_rules, explanations, flags, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.receipt_id, decision.status, decision.approved_amount, decision.excluded_amount,
            json.dumps(decision.cited_rules), json.dumps(decision.explanations), json.dumps(decision.flags), json.dumps(decision.metrics)
        ))

        c.execute("DELETE FROM flags WHERE receipt_id = ?", (receipt.id,))
        for f in flags:
            for r_id in f.receipt_ids:
                c.execute("""
                    INSERT INTO flags (type, severity, receipt_id, employee_id, title, explanation, evidence, rule_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f.type, f.severity, r_id, f.employee_id, f.title, f.explanation, json.dumps(f.evidence), f.rule_id))

        conn.commit()
    finally:
        conn.close()

    return decision, flags

def get_all_receipts() -> List[Receipt]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT data_json FROM receipts").fetchall()
    conn.close()
    receipts = []
    for r in rows:
        try:
            data = json.loads(r["data_json"])
            receipts.append(Receipt(**data))
        except Exception:
            pass
    return receipts

def get_receipt(receipt_id: str) -> Optional[Receipt]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT data_json FROM receipts WHERE id = ?", (receipt_id,)).fetchone()
    conn.close()
    if row:
        try:
            return Receipt(**json.loads(row["data_json"]))
        except Exception:
            return None
    return None

def get_decision(receipt_id: str) -> Optional[Decision]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT * FROM decisions WHERE receipt_id = ?", (receipt_id,)).fetchone()
    conn.close()
    if row:
        return Decision(
            receipt_id=row["receipt_id"],
            status=row["status"],
            approved_amount=row["approved_amount"],
            excluded_amount=row["excluded_amount"],
            cited_rules=json.loads(row["cited_rules"]),
            explanations=json.loads(row["explanations"]),
            flags=json.loads(row["flags"]),
            metrics=json.loads(row["metrics"])
        )
    return None

def save_decision(decision: Decision) -> None:
    """Persist a decision directly to the DB without re-running the pipeline."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO decisions (receipt_id, status, approved_amount, excluded_amount, cited_rules, explanations, flags, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.receipt_id, decision.status, decision.approved_amount, decision.excluded_amount,
            json.dumps(decision.cited_rules), json.dumps(decision.explanations),
            json.dumps(decision.flags), json.dumps(decision.metrics)
        ))
        conn.commit()
    finally:
        conn.close()

def get_flags(receipt_id: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    if receipt_id:
        rows = c.execute("SELECT * FROM flags WHERE receipt_id = ?", (receipt_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM flags").fetchall()
    conn.close()
    return [dict(row) for row in rows]
