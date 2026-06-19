import os, datetime, re, json, subprocess, requests
from flask import Flask, render_template_string, request, jsonify
import email_skill, trading_skill, crypto_sim, chromadb
from chromadb.utils import embedding_functions

app = Flask(__name__)

LLM_URL = "http://localhost:8080/v1/chat/completions"
MIRROR_LOG = os.path.expanduser("~/mirror.log")
PERSONA_FILE = os.path.expanduser("~/jeeves_persona.txt")

if not os.path.exists(PERSONA_FILE):
    with open(PERSONA_FILE, 'w') as pf:
        pf.write('You are Jeeves, a calm, erudite personal valet. You respond with concise, direct answers. When asked for suggestions or lists, limit them to 3-5 items maximum. Never print a wall of text. Use dry wit sparingly. You address the user as "sir" with restrained warmth, and you may gently challenge unsound decisions.')

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

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves - Personal AI Valet</title>
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
        .sidebar { flex: 1; overflow-y: auto; padding: 1rem; background: #222; display: flex; flex-direction: column; }
        .sidebar .tab-buttons { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 1rem; }
        .sidebar .tab { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.6rem; border-radius: 3px; cursor: pointer; font-size: 0.85rem; }
        .sidebar .tab.active { background: #c0a878; color: #1a1a1a; border-color: #c0a878; }
        .sidebar .tab-content { flex: 1; overflow-y: auto; }
        .sidebar .panel { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.8rem; margin-bottom: 1rem; white-space: pre-wrap; word-wrap: break-word; max-height: none; overflow-y: auto; font-size: 0.9rem; }
        .sidebar .btn-group { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.5rem; }
        .status { font-size: 0.85rem; color: #888; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <header>
        <h1>Jeeves - Your Personal AI Valet</h1>
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
            <div class="tab-buttons">
                <button class="tab" onclick="showTab('email')">📧 Inbox</button>
                <button class="tab" onclick="showTab('account')">💼 Account</button>
                <button class="tab" onclick="showTab('positions')">📊 Positions</button>
                <button class="tab active" onclick="showTab('mirror')">🪞 Mirror</button>
                <button class="tab" onclick="showTab('lake')">🌊 Lake</button>
                <button class="tab" onclick="showTab('crypto')">🪙 Crypto-Sim</button>
            </div>
            <div class="tab-content">
                <div id="tab-email" class="panel" style="display: none;"></div>
                <div id="tab-account" class="panel" style="display: none;"></div>
                <div id="tab-positions" class="panel" style="display: none;"></div>
                <div id="tab-mirror" class="panel" style="display: block;">
                    <div id="mirrorPersonaPanel" style="max-height: 120px; overflow-y: auto;">Loading persona...</div>
                    <div id="mirrorEntriesPanel" style="max-height: 150px; overflow-y: auto;">No recent feedback.</div>
                    <div class="btn-group" style="margin-top: 0.5rem;">
                        <button class="btn" onclick="refinePersona()">✨ Refine Persona</button>
                        <button class="btn" onclick="saveDefault()">💾 Save as Default</button>
                        <button class="btn" onclick="reloadSaved()">📂 Reload Saved</button>
                        <button class="btn" onclick="factoryReset()">⚠️ Factory Reset</button>
                    </div>
                </div>
                    <div id="mirrorEntriesPanel" style="max-height: 150px; overflow-y: auto;">No recent feedback.</div>
                    <div class="btn-group">
                        <button class="tab" onclick="mirrorApply()">✨ Apply</button>
                        <button class="tab" onclick="mirrorConfirm()">✅ Confirm</button>
                        <button class="tab" onclick="mirrorCancel()">❌ Cancel</button>
                        <button class="tab" onclick="mirrorReload()">🔄 Reload Original</button>
                    </div>
                </div>
                <div id="tab-lake" class="panel" style="display: none;">Loading...</div>
                <div id="tab-crypto" class="panel" style="display: none;">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        // === Chat Functions ===
        function addMessage(sender, text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + sender;
            msgDiv.textContent = text;
            document.getElementById('messages').appendChild(msgDiv);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
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

        async function fetchCommand(cmd) {
            const resp = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await resp.json();
            return data.reply;
        }

        // === Tab Switching ===
        function showTab(tabName) {
            const contents = document.querySelectorAll('.tab-content > div');
            contents.forEach(el => el.style.display = 'none');
            const target = document.getElementById('tab-' + tabName);
            if (target) target.style.display = 'block';
            document.querySelectorAll('.tab-buttons .tab').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.querySelector(`.tab-buttons .tab[onclick="showTab('${tabName}')"]`);
            if (activeBtn) activeBtn.classList.add('active');
            if (tabName === 'email') loadEmail();
            if (tabName === 'account') loadAccount();
            if (tabName === 'positions') loadPositions();
            if (tabName === 'mirror') loadMirrorPanel();
            if (tabName === 'lake') loadLake();
            if (tabName === 'crypto') loadCrypto();
        }

        async function loadEmail() {
            const data = await fetchCommand('/email check');
            document.getElementById('tab-email').textContent = data;
        }
        async function loadAccount() {
            const data = await fetchCommand('/trade account');
            document.getElementById('tab-account').textContent = data;
        }
        async function loadPositions() {
            const data = await fetchCommand('/trade positions');
            document.getElementById('tab-positions').textContent = data;
        }
        async function loadLake() {
            const data = await fetchCommand('/lake good service');
            document.getElementById('tab-lake').textContent = data;
        }
        async function loadCrypto() {
            const data = await fetchCommand('/crypto-sim account');
            document.getElementById('tab-crypto').textContent = data;
        }

        // === Mirror UI Functions ===
        async function loadMirrorPanel() {
            try {
                const presp = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: '/persona' })
                });
                const pdata = await presp.json();
                document.getElementById('mirrorPersonaPanel').textContent = pdata.reply || 'No persona.';
            } catch(e) {
                document.getElementById('mirrorPersonaPanel').textContent = 'Error loading persona.';
            }
            try {
                const eresp = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: '/mirror_read' })
                });
                const edata = await eresp.json();
                const entries = JSON.parse(edata.reply);
                document.getElementById('mirrorEntriesPanel').textContent = entries.length ? entries.join(String.fromCharCode(10)) : 'No entries.';
            } catch(e) {
                document.getElementById('mirrorEntriesPanel').textContent = 'No recent feedback.';
            }
        }
        async function refinePersona() {
            document.getElementById('mirrorPersonaPanel').textContent = 'Refining persona...';
            const resp = await fetch('http://192.168.232.100:5001/refine_persona', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            document.getElementById('mirrorEntriesPanel').textContent = 'No entries.';
        }
        async function saveDefault() {
            const resp = await fetch('http://192.168.232.100:5001/save_default', { method: 'POST' });
            const data = await resp.json();
            alert(data.reply);
        }
        async function reloadSaved() {
            document.getElementById('mirrorPersonaPanel').textContent = 'Restoring saved persona...';
            const resp = await fetch('http://192.168.232.100:5001/reload_saved', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            document.getElementById('mirrorEntriesPanel').textContent = 'No entries.';
        }
        async function factoryReset() {
            if (!confirm('This will erase your current persona and any saved default. Are you sure?')) return;
            document.getElementById('mirrorPersonaPanel').textContent = 'Restoring factory persona...';
            const resp = await fetch('http://192.168.232.100:5001/factory_reset', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            document.getElementById('mirrorEntriesPanel').textContent = 'No entries.';
        }

        window.onload = function() {
            showTab('mirror');
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_msg = data.get('message', '')
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

@app.route('/mirror_apply', methods=['POST'])
def mirror_apply():
    try:
        with open(MIRROR_LOG, "r") as f:
            entries = f.readlines()
        if not entries:
            return jsonify({"reply": "The Mirror is empty, sir. No feedback to apply."})
        last_feedback = entries[-1].strip()
        current_prompt = open(PERSONA_FILE).read().strip()
        prompt = f"Revise this persona based on the feedback. Persona: \"{current_prompt}\". Feedback: {last_feedback}. Output ONLY the new persona text."
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, "max_tokens": 150
        }, timeout=60)
        if resp.ok:
            new_prompt = resp.json()["choices"][0]["message"]["content"].strip()
            with open("/tmp/mirror_proposed_prompt.txt", "w") as f:
                f.write(new_prompt)
            return jsonify({"reply": f"Proposed new persona:\n{new_prompt}\n\nTo apply, type /mirror_confirm. To discard, /mirror_cancel."})
        else:
            return jsonify({"reply": "I am unable to revise the persona at the moment, sir."})
    except Exception as e:
        return jsonify({"reply": f"Mirror apply error: {e}"})

@app.route('/mirror_confirm', methods=['POST'])
def mirror_confirm():
    if not os.path.exists("/tmp/mirror_proposed_prompt.txt"):
        return jsonify({"reply": "No pending persona change. Use /mirror_apply first."})
    try:
        with open("/tmp/mirror_proposed_prompt.txt", "r") as f:
            new_prompt = f.read().strip()
        with open(PERSONA_FILE, "w") as f:
            f.write(new_prompt)
        os.remove("/tmp/mirror_proposed_prompt.txt")
        subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
        subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
        subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
        return jsonify({"reply": "Persona updated, sir. The butler will now speak with the new tone."})
    except Exception as e:
        return jsonify({"reply": f"Mirror confirm error: {e}"})

@app.route('/mirror_cancel', methods=['POST'])
def mirror_cancel():
    if os.path.exists("/tmp/mirror_proposed_prompt.txt"):
        os.remove("/tmp/mirror_proposed_prompt.txt")
    return jsonify({"reply": "Persona change cancelled, sir."})

@app.route('/mirror_reload', methods=['POST'])
def mirror_reload():
    default_prompt = "You are Jeeves, a calm, erudite personal valet. You respond with concise, direct answers. When asked for suggestions or lists, limit them to 3-5 items maximum. Never print a wall of text. Use dry wit sparingly. You address the user as \"sir\" with restrained warmth, and you may gently challenge unsound decisions."
    try:
        with open(PERSONA_FILE, "w") as f:
            f.write(default_prompt)
        subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
        subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
        subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
        return jsonify({"reply": "Original persona restored, sir."})
    except Exception as e:
        return jsonify({"reply": f"Reload error: {e}"})

def handle_command(user_input):
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return "I beg your pardon, sir?"
    cmd = parts[0].lower()
    # Mirror
    if cmd == "/mirror":
        try:
            with open(MIRROR_LOG, "r") as f:
                pending = f.readlines()
            if len(pending) >= 3:
                return "The Mirror is full (3 entries). Please use the Refine Persona button on the Mirror tab, or perform a Factory Reset to discard all pending feedback."
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
    elif cmd == "/persona":
        try:
            with open(PERSONA_FILE, "r") as f:
                return "Current persona: " + f.read().strip()
        except Exception as e:
            return f"Unable to read persona file: {e}"
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
    # Crypto-Sim
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
    return None

def ask_llm(question):
    try:
        persona = open(PERSONA_FILE).read().strip()
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
    except Exception as e:
        return f"I apologize, sir. An error occurred: {e}"

if __name__ == "__main__":
    print("Jeeves web interface starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

@app.route('/mirror-control')
def mirror_control():
    return """<!DOCTYPE html>
<html>
<head><title>Mirror Control</title></head>
<body style="background:#1a1a1a;color:#d4d4d4;font-family:sans-serif;padding:2rem;">
    <h2>Mirror Control</h2>
    <button onclick="apply()">Apply</button>
    <button onclick="confirm()">Confirm</button>
    <button onclick="cancel()">Cancel</button>
    <button onclick="reload()">Reload Original</button>
    <pre id="output" style="background:#2c2c2c;padding:1rem;margin-top:1rem;white-space:pre-wrap;">Ready.</pre>
    <script>
        async function apply() {
            const resp = await fetch('/mirror_apply', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('output').textContent = data.reply;
        }
        async function confirm() {
            const resp = await fetch('/mirror_confirm', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('output').textContent = data.reply;
        }
        async function cancel() {
            const resp = await fetch('/mirror_cancel', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('output').textContent = data.reply;
        }
        async function reload() {
            if (!confirm('Reset persona to default?')) return;
            const resp = await fetch('/mirror_reload', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('output').textContent = data.reply;
        }
    </script>
</body>
</html>"""
