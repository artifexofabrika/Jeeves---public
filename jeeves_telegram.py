#!/usr/bin/env python3
import requests
import json
import time
import os
import sys
import config

BOT_TOKEN = config.BOT_TOKEN
CHAT_ID = config.CHAT_ID
LLM_URL = config.LLM_URL

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=data, timeout=10)
        if r.status_code == 200:
            print(f"Sent: {text[:50]}...")
        else:
            print(f"Send error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Send error: {e}")

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=35)
        if r.status_code == 200:
            return r.json().get("result", [])
        else:
            print(f"Update error: {r.status_code}")
            return []
    except Exception as e:
        print(f"Update error: {e}")
        return []

def ask_jeeves(question):
    """Fallback to the LLM for non-command messages."""
    import config as cfg
    persona_file = cfg.PERSONA_FILE
    try:
        with open(persona_file, 'r') as f:
            persona = f.read().strip()
    except:
        persona = "You are a helpful AI assistant."
    resp = requests.post(LLM_URL, json={
        "model": "llama",
        "messages": [
            {"role":"system","content":persona},
            {"role":"user","content":question}
        ],
        "temperature":0.7, "max_tokens":300
    }, timeout=90)
    if resp.ok:
        return resp.json()["choices"][0]["message"]["content"]
    return "I am momentarily indisposed, sir."

def process_message(text):
    if not text:
        return "I didn't catch that, sir."
    # Try command handler first
    try:
        from jeeves_chat import handle_command
        cmd_result = handle_command(text)
        if cmd_result is not None:
            return cmd_result
    except ImportError as e:
        print(f"Command handling import error: {e}")
    # Fallback to LLM
    return ask_jeeves(text)

def main():
    print("Telegram bridge starting...")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")
                    print(f"Received: {text}")
                    if text and chat_id == CHAT_ID:
                        if text.strip().lower() == '/halt':
                            import os as _os
                            halt_file = _os.path.expanduser("~/coinbase_halt.signal")
                            with open(halt_file, "w") as hf:
                                hf.write("halt")
                            send_message("🛑 Halting Coinbase advisor. No further trades will execute.")
                            continue

                        # Intercept /approve for the Coinbase advisor
                        if text.lower().startswith('/approve'):
                            import os as _os
                            parts = text.split()
                            if len(parts) > 1:
                                approved_ids = []
                                for part in parts[1:]:
                                    # strip any punctuation, just in case
                                    aid = part.strip(',;:')
                                    signal_file = _os.path.expanduser(f"~/coinbase_approve_{aid}.signal")
                                    with open(signal_file, "w") as sf:
                                        sf.write("approved")
                                    approved_ids.append(aid)
                                send_message(f"Approval signals sent for trades: {', '.join(approved_ids)}.")
                            else:
                                send_message("Please include the approval ID, e.g., /approve abc123 def456")
                            continue
                        response = process_message(text)
                        send_message(response)
                    elif text:
                        send_message("You are not authorized to use this bot.")
            time.sleep(1)
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
