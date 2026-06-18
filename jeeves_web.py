import crypto_sim
import crypto_skill
import os, datetime, re, json
from flask import Flask, render_template_string, request, jsonify
import email_skill
import trading_skill
import chromadb
from chromadb.utils import embedding_functions

app = Flask(__name__)

# ---- Constants ----
LLM_URL = "http://localhost:8080/v1/chat/completions"
SYSTEM = open(os.path.expanduser('~/jeeves_persona.txt')).read().strip()
MIRROR_LOG = os.path.expanduser("~/mirror.log")

# ---- Helper Functions ----
def ask_llm(question):
    import requests
    try:
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [
                {"role":"system","content":SYSTEM},
                {"role":"user","content":question}
            ],
            "temperature":0.7, "max_tokens":300
        }, timeout=90)
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"]
        return "I am momentarily indisposed, sir."
    except Exception as e:
        return f"I apologize, sir. An error occurred: {e}"

def get_mirror_last_entry():
    try:
        with open(MIRROR_LOG, "r") as f:
            lines = f.readlines()
        if lines:
            return lines[-1].strip()
        return "The mirror is empty, sir."
    except FileNotFoundError:
        return "The mirror is empty, sir."

def get_lake_last_search(query="good service"):
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path="/mnt/lake/index")
        collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
        results = collection.query(query_texts=[query], n_results=1)
        docs = results.get('documents', [[]])[0]
        if docs:
            return docs[0][:500] + ("..." if len(docs[0]) > 500 else "")
        return "No documents found."
    except Exception as e:
        return f"Lake error: {e}"

# ---- HTML Template ----
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Personal AI Valet</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; display: flex; flex-direction: column; height: 100vh; }
        header { background: #2c2c2c; padding: 1rem; text-align: center; border-bottom: 1px solid #444; }
        header h1 { font-size: 1.5rem; color: #c0a878; }
        .main { display: flex; flex: 1; overflow: hidden; }
        .chat-area { flex: 3; display: flex; flex-direction: column; border-right: 1px solid #444; }
        .messages { flex: 1; overflow-y: auto; padding: 1rem; }
        .message { margin-bottom: 1rem; }
        .message.user { text-align: right; color: #a0c0ff; }
        .message.jeeves { text-align: left; color: #c0a878; }
        .input-area { display: flex; padding: 0.5rem; background: #2c2c2c; }
        .input-area input { flex: 1; padding: 0.5rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; }
        .input-area button { padding: 0.5rem 1rem; margin-left: 0.5rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; }
        .sidebar { flex: 1; overflow-y: auto; padding: 1rem; background: #222; }
        .sidebar h3 { color: #c0a878; margin-top: 1rem; margin-bottom: 0.5rem; }
        .sidebar .btn-group { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 1rem; }
        .sidebar .btn { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.6rem; border-radius: 3px; cursor: pointer; font-size: 0.85rem; }
        .sidebar .btn:hover { background: #4c4c4c; }
        .panel { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.8rem; margin-bottom: 1rem; white-space: pre-wrap; word-wrap: break-word; max-height: 200px; overflow-y: auto; font-size: 0.9rem; }
        .status { font-size: 0.85rem; color: #888; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <header>
        <h1>Jeeves – Your Personal AI Valet</h1>
        <div class="status" id="status">Ready</div>
    </header>
    <div class="main">
        <div class="chat-area">
            <div class="messages" id="messages">
                <div class="message jeeves">Good day, sir. How may I be of service?</div>
            </div>
            <div class="input-area">
                <input type="text" id="userInput" placeholder="Type your message or command..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        <div class="sidebar">
            <h3>Quick Commands</h3>
            <div class="btn-group">
                <button class="btn" onclick="sendCommand('/email check')">📧 Inbox</button>
                <button class="btn" onclick="sendCommand('/trade account')">💼 Account</button>
                <button class="btn" onclick="sendCommand('/trade positions')">📊 Positions</button>
                <button class="btn" onclick="sendCommand('/mirror_read')">🪞 Mirror</button>
                <button class="btn" onclick="sendCommand('/lake Toyota Way')">🌊 Lake</button>
                <button class="btn" onclick="sendCommand('/crypto-sim account')">🪙 Crypto-Sim</button>
            </div>
            <h3>Command Output</h3>
            <div class="panel" id="cmdOutput">Awaiting command...</div>
            <h3>Trading Account</h3>
            <div class="panel" id="tradingPanel">Loading...</div>
            <h3>Latest Mirror Entry</h3>
            <div class="panel" id="mirrorPanel">Loading...</div>
            <h3>Lake Preview</h3>
            <div class="panel" id="lakePanel">Loading...</div>
        </div>
    </div>

    <script>
        function addMessage(sender, text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + sender;
            msgDiv.textContent = text;
            document.getElementById('messages').appendChild(msgDiv);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }

        async function sendCommand(cmd) {
            document.getElementById('status').textContent = 'Processing...';
            const resp = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await resp.json();
            document.getElementById('cmdOutput').textContent = data.reply || 'No response';
            document.getElementById('status').textContent = 'Ready';
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;
            addMessage('user', text);
            input.value = '';
            document.getElementById('status').textContent = 'Thinking...';
            const resp = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await resp.json();
            addMessage('jeeves', data.reply);
            document.getElementById('status').textContent = 'Ready';
        }

        async function loadPanels() {
            // Trading account
            fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: '/trade account' })
            }).then(r => r.json()).then(d => {
                document.getElementById('tradingPanel').textContent = d.reply;
            });
            // Mirror
            fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: '/mirror_read' })
            }).then(r => r.json()).then(d => {
                document.getElementById('mirrorPanel').textContent = d.reply;
            });
            // Lake preview
            fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: '/lake good service' })
            }).then(r => r.json()).then(d => {
                document.getElementById('lakePanel').textContent = d.reply;
            });
        }

        window.onload = loadPanels;
    </script>
</body>
</html>
"""

# ---- Routes ----
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_msg = data.get('message', '')
    # Check if it's a command (starts with /)
    if user_msg.startswith('/'):
        reply = handle_command(user_msg)
    else:
        reply = ask_llm(user_msg)
    return jsonify({'reply': reply})

@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    cmd = data.get('command', '')
    reply = handle_command(cmd)
    return jsonify({'reply': reply})

def handle_command(user_input):
    """Same command logic as the CLI, returns a string reply."""
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return "I beg your pardon, sir?"
    cmd = parts[0].lower()
    # Mirror
    if cmd == "/mirror":
        # Cap at 3 pending entries
        try:
            with open(MIRROR_LOG, "r") as f:
                pending = f.readlines()
            if len(pending) >= 3:
                return "The Mirror is full (3 entries). Please use /mirror_apply to refine your persona or /mirror_cancel to discard the pending feedback."
        except:
            pass
        if len(parts) > 1:
            note = parts[1]
            timestamp = datetime.datetime.now().isoformat()
            with open(MIRROR_LOG, "a") as f:
                f.write(f"{timestamp} | {note}\n")
            return "Noted, sir. Your feedback has been logged in the Gentleman's Mirror."
        return "What shall I record, sir?"
    elif cmd == "/mirror_read":
        try:
            with open(MIRROR_LOG, "r") as f:
                lines = [line.strip() for line in f.readlines()[-3:] if line.strip()]
            return json.dumps(lines)
        except:
            return "[]"
    # Email
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
            return "Usage: /email send <to> <subject> | <body>"
        elif sub_cmd == "delete":
            if len(sub_parts) > 1:
                sender = sub_parts[1]
                return email_skill.delete_from_sender(sender)
            return "Whose messages shall I delete, sir?"
        return "Available email commands: check, send, delete."
    # Trading
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
        return "Available trade commands: account, positions, buy, sell, price."
    # Lake
    elif cmd == "/lake":
        if len(parts) > 1:
            query = parts[1]
            return get_lake_last_search(query)
        return "What shall I search for, sir?"
    # Crypto (placeholder)
    elif cmd == "/crypto":
        rest = parts[1] if len(parts) > 1 else ''
        sub_parts = rest.split(maxsplit=1)
        sub_cmd = sub_parts[0].lower() if sub_parts else ''
        if sub_cmd == "account":
            return crypto_skill.get_account()
        elif sub_cmd == "positions":
            return crypto_skill.get_positions()
        elif sub_cmd == "buy":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_skill.place_order(symbol.upper(), float(qty), "buy")
            except:
                return "Usage: /crypto buy <symbol> <quantity>"
        elif sub_cmd == "sell":
            args = sub_parts[1] if len(sub_parts) > 1 else ''
            try:
                symbol, qty = args.split()
                return crypto_skill.place_order(symbol.upper(), float(qty), "sell")
            except:
                return "Usage: /crypto sell <symbol> <quantity>"
        elif sub_cmd == "price":
            symbol = sub_parts[1] if len(sub_parts) > 1 else ''
            return crypto_skill.get_price(symbol.upper()) if symbol else "Specify a symbol, sir."
        else:
            return "Available crypto commands: account, positions, buy, sell, price."
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
    elif cmd == "/mirror_apply":
        try:
            with open(MIRROR_LOG, "r") as f:
                entries = f.readlines()[-5:]
            if not entries:
                return "The Mirror is empty, sir. No feedback to apply."
            feedback = "".join(entries)
            # Ask the LLM to REVISE the current system prompt, not replace it
            current_prompt = SYSTEM  # the current prompt defined earlier in the script
            prompt = f"""You are a system prompt editor. Your task is to revise an existing system prompt for a personal AI assistant named Jeeves, based on recent user feedback. The current prompt is:
"{current_prompt}"
The user has given the following feedback:
{feedback}
Please produce a revised prompt that addresses the feedback while preserving the assistant's core character: calm, erudite, polite, with occasional dry wit. The new prompt should be concise and suitable for a personal valet. Output ONLY the revised prompt text, nothing else."""
            reply = ask_llm(prompt)
            # Store the proposal for confirmation
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
            # Save the new prompt to the shared persona file
            persona_file = os.path.expanduser("~/jeeves_persona.txt")
            with open(persona_file, "w") as pf:
                pf.write(new_prompt)
            os.remove("/tmp/mirror_proposed_prompt.txt")
            # Restart services to pick up the change
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
    return None

if __name__ == "__main__":
    print("Jeeves web interface starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
