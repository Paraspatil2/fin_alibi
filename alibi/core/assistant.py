from typing import Dict, Any, List

def process_employee_chat(message: str, chat_history: List[Dict[str, str]]) -> str:
    """
    Feature 7: Fix-before-submit chat assistant.
    The employee sends a photo or message in chat and the bot answers in seconds:
    'Who was the client? Add the name.' or 'Please provide attendee count.'
    """
    msg_lower = message.lower()
    
    if "client" in msg_lower or "dinner" in msg_lower or "meal" in msg_lower:
        return "I see this is a client meal receipt. Who was the client? Please add the client name and attendee count before submission."
    elif "taxi" in msg_lower or "travel" in msg_lower:
        return "Noted. Please ensure your project code or trip ID is attached for transit expenses."
    elif "hotel" in msg_lower or "stay" in msg_lower:
        return "Got it. Please ensure personal minibar or laundry items are separated or excluded from the claim."
    elif "hi" in msg_lower or "hello" in msg_lower or "help" in msg_lower:
        return "Hello! I am your Alibi Pre-Submission Assistant. Upload your receipt photo and I will verify it against corporate policy in seconds."
    else:
        return f"I've analyzed your message. To ensure fast approval, please verify that the merchant, date, tax ID, and itemized breakdown are clearly visible."
