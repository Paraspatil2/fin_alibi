import json
import os
from typing import List
from alibi.core.models import PolicyRule

def load_policy_rules() -> List[PolicyRule]:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "policy_rules.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
        return [PolicyRule(**item) for item in data]
