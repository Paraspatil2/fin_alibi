import math
from typing import List, Dict, Any, Optional
from alibi.core.models import Receipt, Employee
from alibi.core.ledger import load_ledger

def calculate_distance_km(city1: str, city2: str) -> float:
    # Approximate geographic coordinates for major cities
    coords = {
        "bengaluru": (12.9716, 77.5946),
        "bangalore": (12.9716, 77.5946),
        "delhi": (28.6139, 77.2090),
        "new delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "hyderabad": (17.3850, 78.4867),
        "chennai": (13.0827, 80.2707),
        "kolkata": (22.5726, 88.3639),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "san francisco": (37.7749, -122.4194),
        "tokyo": (35.6762, 139.6503)
    }
    c1 = coords.get(city1.strip().lower())
    c2 = coords.get(city2.strip().lower())
    if not c1 or not c2:
        return 1000.0  # default fallback distance
    
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371.0  # Earth radius in km
    return c * r

def parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    if not time_str:
        return None
    try:
        parts = time_str.strip().replace("p.m.", "PM").replace("a.m.", "AM").split(":")
        hour = int(parts[0])
        minute = int(parts[1][:2])
        if "PM" in time_str.upper() and hour < 12:
            hour += 12
        if "AM" in time_str.upper() and hour == 12:
            hour = 0
        return hour * 60 + minute
    except Exception:
        return None

def check_teleport_anomaly(receipt: Receipt, employee: Employee) -> Optional[str]:
    """
    Feature 1: Teleport Check.
    Builds employee timeline from receipt cities and times.
    Flags physically impossible travel (e.g. Bengaluru hotel at 9 PM and Delhi lunch at 1 PM same day).
    """
    if not receipt.city or not receipt.date or not receipt.time:
        return None

    r_mins = parse_time_to_minutes(receipt.time)
    if r_mins is None:
        return None

    # Load all existing receipts for this employee on the same date from sample or ledger
    ledger_entries = load_ledger()
    same_day_receipts = []
    
    # Also check sample receipts file
    import json, os
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_receipts.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            sample_data = json.load(f)
            for item in sample_data:
                if item.get("employee_id") == employee.employee_id and item.get("date") == receipt.date and item.get("id") != receipt.id:
                    same_day_receipts.append(item)

    for other in same_day_receipts:
        o_city = other.get("city")
        o_time = other.get("time")
        if not o_city or not o_time:
            continue
        o_mins = parse_time_to_minutes(o_time)
        if o_mins is None:
            continue

        dist_km = calculate_distance_km(receipt.city, o_city)
        time_diff_hours = abs(r_mins - o_mins) / 60.0
        
        # Max commercial aircraft speed ~ 900 km/h + 2 hours airport buffer
        max_possible_dist = (time_diff_hours) * 850.0
        
        if dist_km > max_possible_dist and dist_km > 300:
            return f"TELEPORT_ANOMALY: Physically impossible travel detected between {o_city} at {o_time} and {receipt.city} at {receipt.time} on {receipt.date}. Distance: {dist_km:.0f} km in {time_diff_hours:.1f} hours."

    return None
