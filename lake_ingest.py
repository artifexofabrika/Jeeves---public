#!/usr/bin/env python3
"""
Jeeves Knowledge Lake Ingest
- Reads files from LAKE_INBOX_DIR (default ~/lake_inbox)
- Splits text into chunks with overlap
- Embeds chunks locally (no LLM)
- Stores in ChromaDB collection 'memory_lake'
- Skips already ingested files (by SHA256 hash)
- Throttles with a configurable delay
"""

import os, sys, json, hashlib, time, datetime
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

# ---------- Configuration ----------
INBOX_DIR = os.path.expanduser(os.getenv("LAKE_INBOX_DIR", "~/lake_inbox"))
CHUNK_SIZE = 1000          # characters per chunk
CHUNK_OVERLAP = 200        # character overlap
INGEST_DELAY = float(os.getenv("LAKE_INGEST_DELAY", "0.5"))  # seconds between chunks
INGESTED_DB = os.path.expanduser("~/lake_ingested.json")
LAKE_INDEX_PATH = os.path.expanduser(os.getenv("LAKE_INDEX_PATH", "/mnt/lake/index"))
LOG_FILE = os.path.expanduser("~/lake_ingest.log")

# Ensure inbox exists
os.makedirs(INBOX_DIR, exist_ok=True)
os.makedirs(LAKE_INDEX_PATH, exist_ok=True)

# ---------- ChromaDB Setup ----------
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
client = chromadb.PersistentClient(path=LAKE_INDEX_PATH)
collection = client.get_or_create_collection(
    name="memory_lake",
    embedding_function=embedding_fn
)

# ---------- Utility Functions ----------
def log(msg):
    timestamp = datetime.datetime.now().isoformat()
    line = f"{timestamp} | {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def file_hash(filepath):
    """Return SHA256 hex digest of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load_ingested_db():
    if os.path.exists(INGESTED_DB):
        with open(INGESTED_DB, "r") as f:
            return json.load(f)
    return {}

def save_ingested_db(db):
    with open(INGESTED_DB, "w") as f:
        json.dump(db, f, indent=2)

def split_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Yield chunks of text with overlap."""
    if len(text) <= size:
        yield text
        return
    start = 0
    while start < len(text):
        end = start + size
        yield text[start:end]
        start += (size - overlap)

# ---------- Main Ingestion ----------
def main():
    import fcntl
    lock_path = os.path.expanduser("~/lake_ingest.lock")
    with open(lock_path, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Ingestion already in progress; exiting.")
            return

    log("Lake ingestion started.")
    inbox = Path(INBOX_DIR)
    files = list(inbox.rglob("*"))
    if not files:
        log("No files found in inbox.")
        return

    ingested_db = load_ingested_db()
    total_chunks = 0
    new_files = 0

    for filepath in files:
        if not filepath.is_file():
            continue
        # Only process text-like files (add more extensions as needed)
        if filepath.suffix.lower() not in [".txt", ".md", ".csv", ".json"]:
            continue

        abs_path = str(filepath.resolve())
        fhash = file_hash(abs_path)

        if abs_path in ingested_db and ingested_db[abs_path] == fhash:
            log(f"Skipping (unchanged): {filepath.name}")
            continue

        log(f"Ingesting: {filepath.name}")
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            log(f"  Error reading file: {e}")
            continue

        chunks = list(split_text(text))
        log(f"  Split into {len(chunks)} chunks.")

        for i, chunk in enumerate(chunks):
            meta = {
                "filename": filepath.name,
                "source_path": abs_path,
                "chunk_index": i,
                "ingested_at": datetime.datetime.now().isoformat(),
                "hash": fhash
            }
            # ChromaDB expects unique IDs; we use file hash + chunk index
            doc_id = f"{fhash}_{i}"
            # Avoid re-adding if already present (though full file check handles most)
            try:
                collection.add(
                    documents=[chunk],
                    metadatas=[meta],
                    ids=[doc_id]
                )
            except Exception as e:
                log(f"  Error adding chunk {i}: {e}")
                time.sleep(1)  # brief pause on error
                continue

            if total_chunks % 10 == 0 and total_chunks > 0:
                log(f"  Progress: {total_chunks} chunks embedded...")
            total_chunks += 1
            if INGEST_DELAY > 0:
                time.sleep(INGEST_DELAY)

        # Mark file as ingested
        ingested_db[abs_path] = fhash
        new_files += 1

    save_ingested_db(ingested_db)
    log(f"Ingestion complete. {new_files} new/updated files, {total_chunks} total chunks added.")
    return total_chunks

if __name__ == "__main__":
    main()
