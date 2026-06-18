import requests, os, datetime, sys, io, re
import email_skill
import trading_skill
import chromadb
from chromadb.utils import embedding_functions

# Force UTF-8
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LLM_URL = "http://localhost:8080/v1/chat/completions"
SYSTEM = "You are Jeeves, a calm, erudite, and unfailingly polite personal AI assistant. You respond with concise, helpful answers, occasionally employing dry wit. You never use slang or corporate jargon, and you always address the user as 'sir' with restrained warmth."
MIRROR_LOG = os.path.expanduser("~/mirror.log")

def log_mirror(note):
    timestamp = datetime.datetime.now().isoformat()
    with open(MIRROR_LOG, "a") as f:
        f.write(f"{timestamp} | {note}\n")

def handle_lake_search(query):
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path="/mnt/lake/index")
        collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get('documents', [[]])[0]
        if not docs:
            return "No relevant documents found in the Lake, sir."
        reply = "🌊 Lake Results:\n"
        for i, doc in enumerate(docs, 1):
            reply += f"{i}. {doc[:300]}...\n\n" if len(doc) > 300 else f"{i}. {doc}\n\n"
        return reply
    except Exception as e:
        return f"Lake search error: {e}"

def handle_command(user_input):
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return None
    cmd = parts[0].lower()
    # Mirror commands
    if cmd == "/mirror":
        if len(parts) > 1:
            note = parts[1]
            log_mirror(note)
            return "Noted, sir. Your feedback has been logged in the Gentleman's Mirror."
        else:
            return "What shall I record, sir? Use /mirror <your note>."
    elif cmd == "/mirror_read":
        try:
            with open(MIRROR_LOG, "r") as f:
                lines = f.readlines()[-5:]
            if lines:
                return "Recent mirror entries:\n" + "".join(lines)
            else:
                return "The mirror is empty, sir."
        except FileNotFoundError:
            return "The mirror is empty, sir."
    # Email commands
    elif cmd == "/email":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "check":
            return email_skill.check_email()
        elif sub_cmd == "send":
            rest_body = sub_parts[1] if len(sub_parts) > 1 else ''
            match = re.match(r'^(\S+)\s+([^|]+)\s*\|\s*(.*)', rest_body)
            if match:
                to_addr, subject, body = match.groups()
                return email_skill.send_email(to_addr, subject, body)
            else:
                return "Usage: /email send <to> <subject> | <body>"
        elif sub_cmd == "draft":
            return "Drafting is not yet wired to the LLM, sir. I will note the request."
        else:
            return "Available email commands: check, send, draft."
    # Lake command
    elif cmd == "/lake":
        if len(parts) > 1:
            query = parts[1]
            return handle_lake_search(query)
        else:
            return "What shall I search for, sir? e.g., /lake Stoic philosophy"
    elif cmd == "/trade":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "account":
            return trading_skill.get_account()
        elif sub_cmd == "positions":
            return trading_skill.get_positions()
        elif sub_cmd == "buy":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return trading_skill.place_order(symbol.upper(), int(qty), "buy")
            except:
                return "Usage: /trade buy <symbol> <quantity>"
        elif sub_cmd == "sell":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return trading_skill.place_order(symbol.upper(), int(qty), "sell")
            except:
                return "Usage: /trade sell <symbol> <quantity>"
        elif sub_cmd == "price":
            symbol = sub_parts[1] if len(sub_parts) > 1 else ''
            return trading_skill.get_market_price(symbol.upper()) if symbol else "Specify a symbol, sir."
        else:
            return "Available trade commands: account, positions, buy, sell, price."
    return None

def ask_jeeves(question):
    resp = requests.post(LLM_URL, json={
        "model": "llama",
        "messages": [
            {"role":"system","content":SYSTEM},
            {"role":"user","content":question}
        ],
        "temperature":0.7, "max_tokens":300
    }, timeout=60)
    if resp.ok:
        return resp.json()["choices"][0]["message"]["content"]
    return "I am momentarily indisposed, sir."

print("Jeeves at your service. Type /help for commands, or just speak.")
while True:
    try:
        user = input("\nYou > ")
    except (EOFError, KeyboardInterrupt):
        print()
        break
    if user.lower() in ("quit", "exit", "q"):
        break
    if not user.strip():
        continue
    cmd_response = handle_command(user)
    if cmd_response:
        print(f"Jeeves > {cmd_response}")
        continue
    reply = ask_jeeves(user)
    print(f"Jeeves > {reply}")
