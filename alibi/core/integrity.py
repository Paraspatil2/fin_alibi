import hashlib
import json
import os
from typing import List, Dict, Any, Optional
from alibi.core.models import Receipt

AUDIT_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "audit_chain.json")

def compute_file_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compute_semantic_fingerprint(receipt: Receipt) -> str:
    raw = f"{receipt.tax_id}|{receipt.bill_no}|{receipt.date}|{receipt.total}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def load_audit_chain() -> List[Dict[str, Any]]:
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    with open(AUDIT_LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def find_receipt_in_chain(receipt_id: str, file_sha256: Optional[str] = None) -> Optional[Dict[str, Any]]:
    chain = load_audit_chain()
    for block in chain:
        if block.get("action") == "EXPENSE_AUDITED":
            b_data = block.get("data", {})
            if receipt_id and b_data.get("receipt_id") == receipt_id:
                return block
            if file_sha256 and b_data.get("file_sha256") == file_sha256:
                return block
    return None

def append_audit_block(action: str, data: Dict[str, Any], allow_duplicates: bool = False) -> Dict[str, Any]:
    chain = load_audit_chain()
    
    if not allow_duplicates and action == "EXPENSE_AUDITED":
        r_id = data.get("receipt_id")
        f_sha = data.get("file_sha256")
        existing = find_receipt_in_chain(r_id, f_sha)
        if existing:
            raise ValueError(f"Duplicate block rejected: Receipt '{r_id}' is already committed in Block #{existing.get('index')}")

    prev_hash = chain[-1]["current_hash"] if chain else "0" * 64
    block_data = {
        "index": len(chain),
        "prev_hash": prev_hash,
        "action": action,
        "data": data
    }
    block_string = json.dumps(block_data, sort_keys=True)
    current_hash = hashlib.sha256(block_string.encode("utf-8")).hexdigest()
    block = {**block_data, "current_hash": current_hash}
    chain.append(block)
    os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
    with open(AUDIT_LOG_FILE, "w") as f:
        json.dump(chain, f, indent=2)
    return block

def verify_chain() -> bool:
    chain = load_audit_chain()
    if not chain:
        return True
    for i, block in enumerate(chain):
        prev_hash = "0" * 64 if i == 0 else chain[i-1]["current_hash"]
        if block["prev_hash"] != prev_hash:
            return False
        check_data = {
            "index": block["index"],
            "prev_hash": block["prev_hash"],
            "action": block["action"],
            "data": block["data"]
        }
        recomputed = hashlib.sha256(json.dumps(check_data, sort_keys=True).encode("utf-8")).hexdigest()
        if recomputed != block["current_hash"]:
            return False
    return True
