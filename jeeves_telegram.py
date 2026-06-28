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

def process_message(text):
    if not text:
        return "I didn't catch that, sir."
    try:
        from jeeves_chat import handle_command
        return handle_command(text)
    except ImportError as e:
        return f"Command handling not available: {e}"

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
