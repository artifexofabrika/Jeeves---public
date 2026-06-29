import crypto_sim
import requests, os, datetime, sys, io, re
import chromadb
from chromadb.utils import embedding_functions
import trading_advisor
import mirror_engine
import config
import web_search

# Force UTF-8
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LLM_URL = config.LLM_URL
SYSTEM = open(config.PERSONA_FILE).read().strip()
MIRROR_LOG = config.MIRROR_LOG

def log_mirror(note):
    timestamp = datetime.datetime.now().isoformat()
    with open(MIRROR_LOG, "a") as f:
        f.write(f"{timestamp} | {note}\n")

def handle_lake_search(query):
    # Try lake first
    lake_reply = None
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path="/mnt/lake/index")
        collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get('documents', [[]])[0]
        if docs:
            lake_reply = "🌊 Lake Results:\n"
            for i, doc in enumerate(docs, 1):
                lake_reply += f"{i}. {doc[:300]}...\n\n" if len(doc) > 300 else f"{i}. {doc}\n\n"
            return lake_reply
    except:
        pass
    # Lake empty – try web if enabled
    if os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true":
        web_results = web_search.search(query, 3)
        if web_results:
            reply = "📡 Web Results (nothing found in your private lake):\n"
            for i, r in enumerate(web_results, 1):
                reply += f"{i}. {r['title']}\n{r['snippet']}\n\n"
            return reply
        else:
            return "No relevant documents found in the Lake, sir, and the web search returned no results."
    return "No relevant documents found in the Lake, sir."

def handle_command(user_input):
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return None
    cmd = parts[0].lower()
    # Mirror commands
    if cmd == "/mirror":
        try:
            with open(MIRROR_LOG, "r") as f:
                pending = f.readlines()
            if len(pending) >= 3:
                return "The Mirror is full (3 entries). Please use the Refine Persona button on the Mirror tab, or perform a Factory Reset to discard all pending feedback."
        except:
            pending = []
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
    elif cmd == "/mirror_apply":
        try:
            with open(MIRROR_LOG, "r") as f:
                entries = f.readlines()[-5:]
            if not entries:
                return "The Mirror is empty, sir. No feedback to apply."
            feedback = "".join(entries)
            current_prompt = SYSTEM
            prompt = f"""You are a system prompt editor. Your task is to revise an existing system prompt for a personal AI assistant named Jeeves, based on recent user feedback. The current prompt is:
"{current_prompt}"
The user has given the following feedback:
{feedback}
Please produce a revised prompt that addresses the feedback while preserving the assistant's core character: calm, erudite, polite, with occasional dry wit. The new prompt should be concise and suitable for a personal valet. Output ONLY the revised prompt text, nothing else."""
            reply = ask_llm(prompt)
            with open("/tmp/mirror_proposed_prompt.txt", "w") as f:
                f.write(reply)
            return (f"Proposed new persona:\n{reply}\n\n"
                    "To apply this change, type /mirror_confirm. To discard, type /mirror_cancel.")
        except Exception as e:
            return f"Mirror apply error: {e}"
    elif cmd == "/mirror_confirm":
        if not os.path.exists("/tmp/mirror_proposed_prompt.txt"):
            return "No pending persona change. Use /mirror_apply first."
        try:
            with open("/tmp/mirror_proposed_prompt.txt", "r") as f:
                new_prompt = f.read().strip()
            persona_file = config.PERSONA_FILE
            with open(persona_file, "w") as pf:
                pf.write(new_prompt)
            os.remove("/tmp/mirror_proposed_prompt.txt")
            import subprocess
            subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
            subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
            subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
            return "Persona updated, sir. The butler will now speak with the new tone."
        except Exception as e:
            return f"Mirror confirm error: {e}"
    elif cmd == "/mirror_cancel":
        if os.path.exists("/tmp/mirror_proposed_prompt.txt"):
            os.remove("/tmp/mirror_proposed_prompt.txt")
        return "Persona change cancelled, sir."
    elif cmd == "/crypto-sim":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "account":
            return crypto_sim.get_account()
        elif sub_cmd == "positions":
            return crypto_sim.get_positions()
        elif sub_cmd == "buy":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_sim.place_order(symbol.upper(), float(qty), "buy")
            except:
                return "Usage: /crypto-sim buy <symbol> <quantity>"
        elif sub_cmd == "sell":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_sim.place_order(symbol.upper(), float(qty), "sell")
            except:
                return "Usage: /crypto-sim sell <symbol> <quantity>"
        elif sub_cmd == "price":
            symbol = sub_parts[1] if len(sub_parts) > 1 else ''
            return crypto_sim.get_price(symbol.upper()) if symbol else "Specify a symbol, sir."
        else:
            return "Available crypto-sim commands: account, positions, buy, sell, price."
    elif cmd == "/crypto-strat":
        try:
            with open(os.path.expanduser("~/crypto_strategy_feedback.log"), "r") as f:
                pending = f.readlines()
            if len(pending) >= 3:
                return "The Crypto Strategy Mirror is full (3 entries). Please refine or discard."
        except:
            pass
        if len(parts) > 1:
            note = parts[1]
            timestamp = datetime.datetime.now().isoformat()
            with open(os.path.expanduser("~/crypto_strategy_feedback.log"), "a") as f:
                f.write(f"{timestamp} | {note}\n")
            return "Noted, sir. Your feedback has been logged in the Crypto Strategy Mirror."
        return "What feedback do you have for the crypto strategy?"
    elif cmd == "/crypto-strat_read":
        try:
            with open(os.path.expanduser("~/crypto_strategy_feedback.log"), "r") as f:
                lines = [line.strip() for line in f.readlines()[-3:] if line.strip()]
            return json.dumps(lines)
        except:
            return "[]"
    elif cmd == "/crypto-strat_summary":
        try:
            with open(config.CRYPTO_STRATEGY_FILE, "r") as f:
                return f.read().strip()
        except:
            return "No strategy file found."
    elif cmd == "/crypto-strat_apply":
        try:
            fb_path = os.path.expanduser("~/crypto_strategy_feedback.log")
            strat_path = config.CRYPTO_STRATEGY_FILE
            with open(fb_path, "r") as f:
                entries = f.readlines()
            if not entries:
                return "No feedback to apply."
            all_fb = "\n".join([e.strip().split(" | ",1)[-1] for e in entries if " | " in e])
            current = open(strat_path).read().strip()
            prompt = f"Revise this crypto trading strategy based on the feedback. Current strategy:\n{current}\n\nFeedback:\n{all_fb}\n\nOutput ONLY the revised strategy text, no commentary."
            resp = requests.post(LLM_URL, json={
                "model": "llama",
                "messages": [{"role":"user","content":prompt}],
                "temperature":0.7,"max_tokens":400
            }, timeout=60)
            if resp.ok:
                new_strat = resp.json()["choices"][0]["message"]["content"].strip()
                with open(strat_path, "w") as f:
                    f.write(new_strat)
                with open(fb_path, "w") as f:
                    f.write("")
                return f"Strategy refined, sir. New strategy saved."
            else:
                return "I am unable to refine the strategy at the moment."
        except Exception as e:
            return f"Error: {e}"
    elif cmd == "/crypto-strat_save":
        try:
            import shutil
            shutil.copy(config.CRYPTO_STRATEGY_FILE, os.path.expanduser("~/crypto_sim_strategy_default.txt"))
            return "Current strategy saved as your personal baseline."
        except Exception as e:
            return f"Error saving baseline: {e}"
    elif cmd == "/crypto-strat_reload":
        try:
            def_path = os.path.expanduser("~/crypto_sim_strategy_default.txt")
            if os.path.exists(def_path):
                import shutil
                shutil.copy(def_path, config.CRYPTO_STRATEGY_FILE)
                return "Your saved baseline has been restored."
            else:
                return "No saved baseline found."
        except Exception as e:
            return f"Error reloading baseline: {e}"
    elif cmd == "/crypto-strat_factory_reset":
        factory = """I am a cautious crypto trader. My goal is to preserve capital and achieve steady small gains.
Rules:
- Trade only BTC/USD, ETH/USD, USDT/USD, LTC/USD, XRP/USD.
- Buy when the price is at least 3% below its 20‑day moving average (simulated by recent price actions).
- Sell if a position gains 5% or more, or if it falls 2% from entry.
- Never risk more than 2% of the portfolio on a single trade.
- Maximum 3 open positions.
- Maximum 5 trades per day.
- Paper trade only until the system demonstrates a positive return over 30 days."""
        try:
            with open(config.CRYPTO_STRATEGY_FILE, "w") as f:
                f.write(factory)
            def_path = os.path.expanduser("~/crypto_sim_strategy_default.txt")
            if os.path.exists(def_path):
                os.remove(def_path)
            return "Factory strategy restored. Any saved baseline has been removed."
        except Exception as e:
            return f"Error: {e}"
    # Email commands (stubbed)
    elif cmd == "/email":
        return "Email module not yet available, sir."
    # Lake command
    elif cmd == "/lake":
        if len(parts) > 1:
            query = parts[1]
            return handle_lake_search(query)
        else:
            return "What shall I search for, sir? e.g., /lake Stoic philosophy"
    elif cmd == "/trade-halt":
        with open(os.path.expanduser("~/trading_kill_switch"), "w") as f:
            f.write("halted")
        return "Trading advisor halted, sir."
    elif cmd == "/trade-resume":
        kill_path = os.path.expanduser("~/trading_kill_switch")
        if os.path.exists(kill_path):
            os.remove(kill_path)
        return "Trading advisor resumed, sir."

    elif cmd == "/trade-mirror":
        if len(parts) > 1:
            note = parts[1]
            mirror_engine.log_feedback(config.TRADING_MIRROR_LOG, note)
            return "Trading feedback logged, sir."
        return "What feedback shall I record for the trading strategy?"
    elif cmd == "/trade-mirror_read":
        entries = mirror_engine.read_feedback(config.TRADING_MIRROR_LOG, n=3)
        if entries:
            return "Recent trading feedback:\n" + "\n".join(entries)
        return "No trading feedback, sir."

    elif cmd == "/trade":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "account":
            return trading_advisor.get_account()
        elif sub_cmd == "positions":
            return trading_advisor.get_positions()
        elif sub_cmd == "buy":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return trading_advisor.place_order(symbol.upper(), int(qty), "buy")
            except:
                return "Usage: /trade buy <symbol> <quantity>"
        elif sub_cmd == "sell":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return trading_advisor.place_order(symbol.upper(), int(qty), "sell")
            except:
                return "Usage: /trade sell <symbol> <quantity>"
        elif sub_cmd == "price":
            symbol = sub_parts[1] if len(sub_parts) > 1 else ''
            return trading_advisor.get_market_price(symbol.upper()) if symbol else "Specify a symbol, sir."
        else:
            return "Available trade commands: account, positions, buy, sell, price."
    elif cmd == "/crypto-halt":
        with open(os.path.expanduser("~/crypto_sim_kill_switch"), "w") as f:
            f.write("halted")
        return "Crypto advisor halted, sir."
    elif cmd == "/crypto-resume":
        kill_path = os.path.expanduser("~/crypto_sim_kill_switch")
        if os.path.exists(kill_path):
            os.remove(kill_path)
        return "Crypto advisor resumed, sir."

    elif cmd == "/crypto-halt":
        with open(os.path.expanduser("~/crypto_sim_kill_switch"), "w") as f:
            f.write("halted")
        return "Crypto advisor halted, sir."
    elif cmd == "/crypto-resume":
        kill_path = os.path.expanduser("~/crypto_sim_kill_switch")
        if os.path.exists(kill_path):
            os.remove(kill_path)
        return "Crypto advisor resumed, sir."

    elif cmd == "/crypto":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "account":
            return crypto_sim.get_account()
        elif sub_cmd == "positions":
            return crypto_sim.get_positions()
        elif sub_cmd == "buy":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_sim.place_order(symbol.upper(), float(qty), "buy")
            except:
                return "Usage: /crypto buy <symbol> <quantity>"
        elif sub_cmd == "sell":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_sim.place_order(symbol.upper(), float(qty), "sell")
            except:
                return "Usage: /crypto sell <symbol> <quantity>"
        elif sub_cmd == "price":
            symbol = sub_parts[1] if len(sub_parts) > 1 else ''
            return crypto_sim.get_price(symbol.upper()) if symbol else "Specify a symbol, sir."
        else:
            return "Available crypto commands: account, positions, buy, sell, price."
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
