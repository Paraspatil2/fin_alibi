import json
import os
from typing import Dict

def load_fx_rates() -> Dict[str, float]:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "fx_rates.json")
    if not os.path.exists(path):
        return {"USD": 1.0}
    with open(path, "r") as f:
        return json.load(f)

def convert_currency(amount: float, from_currency: str, to_currency: str = "USD") -> float:
    rates = load_fx_rates()
    fc = from_currency.upper()
    tc = to_currency.upper()
    if fc == tc:
        return amount
    rate_from = rates.get(fc, 1.0)
    rate_to = rates.get(tc, 1.0)
    # amount in USD = amount * rate_from (if rates are relative to base or USD)
    # Let's assume fx_rates.json values are multipliers to convert 1 unit of currency to USD.
    amount_in_usd = amount * rate_from
    if tc == "USD":
        return amount_in_usd
    # convert usd to tc
    return amount_in_usd / rate_to
