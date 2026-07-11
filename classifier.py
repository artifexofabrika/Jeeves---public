"""
classifier.py – Intent classifier using Phi‑3‑mini.
Returns one of: CONVERSATION, WELLNESS, LAKE_SEARCH, WEB_SEARCH,
                PERSONAL_QUESTION, OPERATING_MANUAL.
"""
import requests

LLM_URL = "http://127.0.0.1:8081/v1/chat/completions"

def classify_intent(user_msg):
    """Classify the user message into a high‑level intent category."""
    prompt = (
        "You are an intent classifier. Classify the user's message into exactly one of the following categories:\n"
        "- CONVERSATION: a casual chat, greeting, or general question that needs no special data.\n"
        "- WELLNESS: the user wants to log or retrieve health, food, medication, or exercise information.\n"
        "- LAKE_SEARCH: the user is asking a factual question that should be answered from their private knowledge lake.\n"
        "- WEB_SEARCH: the user wants information that would require an internet search.\n"
        "- PERSONAL_QUESTION: the user is asking about themselves, their personal data, or wants to know what Jeeves knows about them.\n"
        "- OPERATING_MANUAL: the user is asking how to use the Jeeves system itself.\n\n"
        "Reply with ONLY the category name, nothing else.\n\n"
        f"User message: {user_msg}\nCategory:"
    )
    try:
        resp = requests.post(
            LLM_URL,
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.0,
            },
            timeout=5
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip().upper()
            # Extract the first matching category
            for cat in ["CONVERSATION", "WELLNESS", "LAKE_SEARCH", "WEB_SEARCH", "PERSONAL_QUESTION", "OPERATING_MANUAL"]:
                if cat in raw:
                    return cat
        return "CONVERSATION"
    except Exception:
        return "CONVERSATION"
