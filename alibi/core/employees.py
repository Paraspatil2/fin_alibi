import json
import os
from typing import List, Optional
from alibi.core.models import Employee, Receipt

def load_employees() -> List[Employee]:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "employees.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
        return [Employee(**item) for item in data]

def get_employee(employee_id: str) -> Optional[Employee]:
    emps = load_employees()
    for e in emps:
        if e.employee_id == employee_id:
            return e
    return None

def is_on_trip(receipt: Receipt, employee: Employee) -> bool:
    if receipt.trip_id is not None and receipt.trip_id.strip() != "":
        return True
    if receipt.city and employee.home_city:
        if receipt.city.strip().lower() != employee.home_city.strip().lower():
            return True
    return False
