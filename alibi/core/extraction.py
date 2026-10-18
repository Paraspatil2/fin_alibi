import os
from typing import Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

PREFERRED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-pro-latest"
]

def get_gemini_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def select_gemini_model() -> str:
    configured_model = os.getenv("GEMINI_MODEL", "").strip()
    if configured_model and "2.5-flash" not in configured_model:
        return configured_model
    
    client = get_gemini_client()
    if not client:
        return "gemini-3.8-flash"
    
    try:
        available_names = [getattr(m, "name", "").replace("models/", "") for m in client.models.list()]
        for pref in PREFERRED_MODELS:
            if pref in available_names:
                return pref
        # Any flash model that is not 2.5-flash
        for name in available_names:
            if "flash" in name.lower() and "2.5-flash" not in name.lower():
                return name
    except Exception:
        pass
    
    return "gemini-3.8-flash"

def is_gemini_available() -> bool:
    client = get_gemini_client()
    if not client:
        return False
    try:
        model = select_gemini_model()
        # Light verification
        return bool(model)
    except Exception:
        return False

