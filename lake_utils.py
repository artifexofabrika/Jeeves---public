import re, chromadb
from chromadb.utils import embedding_functions

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "you", "your", "i",
    "my", "me", "we", "us", "our", "he", "she", "it", "they", "them",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "how", "when", "where", "why", "not", "no", "just", "very", "too"
}

def _make_ef():
    import os
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser('~/Beeker-mk1/.env'))
    hf_token = os.getenv("HF_TOKEN")
    kwargs = {"model_name": "all-MiniLM-L6-v2"}
    if hf_token:
        kwargs["hf_api_key"] = hf_token
    return embedding_functions.SentenceTransformerEmbeddingFunction(**kwargs)

def _keyword_overlap(query, document):
    query_words = {w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query) if w.lower() not in STOPWORDS}
    if not query_words:
        return 0.0
    doc_lower = document.lower()
    found = sum(1 for w in query_words if w in doc_lower)
    return found / len(query_words)

def _exact_term_search(term, collection, n=5):
    """Search the entire collection for documents containing the exact term (case‑insensitive)."""
    try:
        all_data = collection.get()
        docs = all_data.get('documents', [])
        matched = []
        term_lower = term.lower()
        for doc in docs:
            if re.search(r'\b' + re.escape(term_lower) + r'\b', doc.lower()):
                matched.append(doc)
                if len(matched) >= n:
                    break
        return matched
    except Exception:
        return []

def query_lake(query, n=3, semantic_weight=0.5, threshold=0.6):
    ef = _make_ef()
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)

    # Semantic search
    results = collection.query(query_texts=[query], n_results=max(10, n))
    docs = results.get('documents', [[]])[0]
    distances = results.get('distances', [[1.0]])[0]

    # Always collect exact‑match terms for technical/code‑like words
    config_triggers = {'env', 'file', 'name', 'config', 'key', 'token', 'address', 'form', 'change', 'api', 'guide', 'persona', 'strategy', 'alpaca', 'brave', 'search', 'lake', 'ingest'}
    code_terms = [w.lower() for w in re.findall(r'[a-zA-Z0-9_.]+', query) if '_' in w or '.' in w or w.isupper() or w.lower() in config_triggers]
    exact_docs = set()
    for t in code_terms:
        for d in _exact_term_search(t, collection, n=n):
            exact_docs.add(d)

    scored = []
    # Domain-specific terms that receive an exact-match boost
    DOMAIN_TERMS = [
        "treasury wine estates", "twe", "continuous improvement", "kaizen", "lean manufacturing",
        "bitcoin", "etf", "btc", "eth", "cryptocurrency", "blockchain",
        "alpaca", "paper trading", "strategy", "portfolio", "dividend", "options",
        "revenue", "profit", "loss", "balance sheet", "income statement", "cash flow"
    ]
    domain_boost = 0.0
    lower_query = query.lower()
    for term in DOMAIN_TERMS:
        if term in lower_query:
            domain_boost = 0.15  # substantial boost for domain terms
            break

    # Score semantic results
    for doc, dist in zip(docs, distances):
        kw = _keyword_overlap(query, doc)
        combined = semantic_weight * dist + (1.0 - semantic_weight) * (1.0 - kw) - domain_boost
        scored.append((combined, doc))

    # Add exact matches with a very good score (0.0 = best)
    for doc in exact_docs:
        kw = _keyword_overlap(query, doc)
        combined = semantic_weight * 0.1 + (1.0 - semantic_weight) * (1.0 - kw) - domain_boost  # strongly prefer exact matches
        scored.append((combined, doc))

    scored.sort(key=lambda x: x[0])
    best_score = scored[0][0] if scored else 1.0

    # Filter by threshold
    filtered = [doc for score, doc in scored if score < threshold]
    if not filtered and exact_docs:
        # if nothing passes threshold but we have exact matches, return them anyway
        filtered = list(exact_docs)[:n]
        best_score = 0.1
    return filtered[:n], best_score if filtered else 1.0

# ──────────────────────────────────────────────
# Conversation Memory Baseline (unchanged)
# ──────────────────────────────────────────────
MEMORY_COLLECTION = "conversation_memory"
BASELINE_COLLECTION = "conversation_memory_baseline"

def _memory_ef():
    return _make_ef()

def _memory_collection():
    ef = _memory_ef()
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    return client.get_or_create_collection(name=MEMORY_COLLECTION, embedding_function=ef)

def store_conversation_summary(summary):
    import datetime, uuid
    collection = _memory_collection()
    collection.add(
        documents=[summary],
        metadatas=[{"timestamp": datetime.datetime.now().isoformat()}],
        ids=[str(uuid.uuid4())]
    )

def retrieve_conversation_context(query, n=3):
    collection = _memory_collection()
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=n)
    return results.get('documents', [[]])[0]

def clear_conversation_memory():
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    try:
        client.delete_collection(name=MEMORY_COLLECTION)
    except:
        pass

def save_conversation_baseline():
    ef = _memory_ef()
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    try:
        client.delete_collection(name=BASELINE_COLLECTION)
    except:
        pass
    mem = client.get_collection(name=MEMORY_COLLECTION)
    if mem.count() == 0:
        return "No conversation memory to save, sir."
    baseline = client.create_collection(name=BASELINE_COLLECTION, embedding_function=ef)
    all_docs = mem.get()
    if all_docs['ids']:
        baseline.add(
            documents=all_docs['documents'],
            metadatas=all_docs['metadatas'],
            ids=all_docs['ids']
        )
    return f"Conversation baseline saved ({mem.count()} entries)."

def restore_conversation_baseline():
    ef = _memory_ef()
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    try:
        baseline = client.get_collection(name=BASELINE_COLLECTION)
    except:
        return "No saved baseline exists, sir."
    clear_conversation_memory()
    mem = client.get_or_create_collection(
        name=MEMORY_COLLECTION,
        embedding_function=ef
    )
    all_docs = baseline.get()
    if all_docs['ids']:
        mem.add(
            documents=all_docs['documents'],
            metadatas=all_docs['metadatas'],
            ids=all_docs['ids']
        )
    return f"Conversation baseline restored ({len(all_docs['ids'])} entries)."

def memory_status():
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    try:
        mem = client.get_collection(name=MEMORY_COLLECTION)
        count = mem.count()
    except:
        count = 0
    try:
        client.get_collection(name=BASELINE_COLLECTION)
        baseline_exists = True
    except:
        baseline_exists = False
    return f"Memory entries: {count}. Baseline: {'saved' if baseline_exists else 'none'}."

def store_wellness_entry(text):
    """Store a small text entry (e.g. meal, medication) directly into the memory lake."""
    import datetime, uuid
    ef = _make_ef()
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
    # For short wellness notes, store as a single chunk
    chunk = text.strip()
    if not chunk:
        return
    meta = {
        "filename": "wellness_log.txt",
        "source_path": "wellness_log",
        "chunk_index": 0,
        "ingested_at": datetime.datetime.now().isoformat(),
        "hash": str(uuid.uuid4())
    }
    doc_id = f"wellness_{uuid.uuid4()}"
    collection.add(documents=[chunk], metadatas=[meta], ids=[doc_id])
