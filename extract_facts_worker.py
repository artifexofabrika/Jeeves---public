"""
extract_facts_worker.py – Background worker that extracts personal facts
from recent chat summaries and updates the personal graph.
Runs independently via systemd timer every 15 seconds.
"""
import os
import json
import datetime
import requests
import chromadb
import re

LLM_URL = "http://127.0.0.1:8081/v1/chat/completions"
LAST_RUN_FILE = os.path.expanduser("~/last_extraction.txt")
LAKE_PATH = "/mnt/lake/index"
COLLECTION = "memory_lake"

def get_last_run():
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, "r") as f:
            return f.read().strip()
    # Default: 15 seconds ago
    return (datetime.datetime.now() - datetime.timedelta(seconds=15)).isoformat()

def set_last_run(ts):
    with open(LAST_RUN_FILE, "w") as f:
        f.write(ts)

def extract_facts_from_summaries():
    since = get_last_run()
    now = datetime.datetime.now().isoformat()

    client = chromadb.PersistentClient(path=LAKE_PATH)
    col = client.get_collection(COLLECTION)

    # Fetch chat summaries stored since the last run
    results = col.get(where={"source": "chat_summary"})
    if not results or not results["documents"]:
        set_last_run(now)
        return

    new_summaries = []
    for i, meta in enumerate(results["metadatas"]):
        if meta.get("date", "") >= since and not meta.get("extracted", False):
            new_summaries.append((results["ids"][i], results["documents"][i]))

    for chunk_id, summary in new_summaries:
        try:
            # Ask Phi‑3‑mini to extract facts
            prompt = (
                "You are a personal fact extractor. Given a sentence summarizing a conversation, "
                "extract any new personal facts about the user. Output them as a single JSON object "
                "where each key is a short label (e.g., 'name', 'project', 'location', 'preference') "
                "and each value is the fact. Only include facts explicitly stated. "
                "If no new facts, output an empty JSON object: {}\n\n"
                f"Sentence: {summary}\nFacts (JSON):"
            )
            resp = requests.post(
                LLM_URL,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.0,
                },
                timeout=10
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    facts = json.loads(match.group(0))
                    import personal_graph
                    for key, value in facts.items():
                        personal_graph.update_field(f"custom_facts.{key}", str(value))
            # Mark as extracted
            col.update(ids=[chunk_id], metadatas=[{"source": "chat_summary", "date": since, "extracted": True}])
        except Exception:
            pass

    set_last_run(now)

if __name__ == "__main__":
    extract_facts_from_summaries()
