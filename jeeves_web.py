import os, datetime, re, json, subprocess, requests
from flask import Flask, render_template_string, request, jsonify, send_file
import crypto_sim, trading_advisor, config, lake_utils, web_search
import chromadb
from chromadb.utils import embedding_functions

app = Flask(__name__)

LLM_URL = config.LLM_URL
MIRROR_LOG = config.MIRROR_LOG
PERSONA_FILE = config.PERSONA_FILE

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
    <link rel="icon" type="image/png" href="/favicon.png">
    <link rel="icon" type="image/png" href="data:image/png;base64,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">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 25%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 50%; display: flex; flex-direction: column; border-bottom: 1px solid #444; }
        .middle-area .tab-buttons { display: flex; flex-wrap: wrap; gap: 0.2rem; padding: 0.3rem 0.6rem; background: #2c2c2c; }
        .middle-area .tab { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.5rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
        .middle-area .tab.active { background: #c0a878; color: #1a1a1a; border-color: #c0a878; }
        .middle-area .tab-content { flex: 1; overflow-y: auto; padding: 0.6rem; }
        .bottom-bar { height: 25%; display: flex; flex-direction: column; background: #1e1e1e; padding: 0.6rem; gap: 0.4rem; }
        .bottom-bar .btn-row { display: flex; flex-wrap: wrap; gap: 0.3rem; }
        .bottom-bar .btn { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.6rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .bottom-bar .btn:hover { background: #4c4c4c; }
        .bottom-bar .status-panel { flex: 1; display: flex; flex-direction: column; gap: 0.3rem; overflow-y: auto; }
        .panel { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.6rem; margin-bottom: 0.5rem; white-space: pre-wrap; word-wrap: break-word; font-size: 0.85rem; }
        .message { margin-bottom: 0.4rem; font-size: 0.9rem; }
        .message.user { text-align: right; color: #a0c0ff; }
        .message.jeeves { text-align: left; color: #c0a878; }
        .status { font-size: 0.8rem; color: #888; }
    </style>
</head>
<body>
    <!-- Top 25%: Chat -->
    <div class="top-bar">
        <div class="chat-messages" id="messages">
            <div class="message jeeves">Good day, sir.</div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Speak to your valet..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <!-- Middle 50%: Active Skill Panel -->
    <div class="middle-area">
        <div class="tab-buttons">
            <button class="tab active" data-tab="mirror" onclick="showTab('mirror')">🪞 Mirror</button>
            <button class="tab" data-tab="cryptostrat" onclick="showTab('cryptostrat')">📈 Trading Strat</button>
            <button class="tab" data-tab="account" onclick="showTab('account')">💼 Account</button>
            <button class="tab" data-tab="email" onclick="showTab('email')">📧 Inbox</button>
            <button class="tab" data-tab="lake" onclick="showTab('lake')">🌊 Lake</button>
        </div>
        <div class="tab-content">
            <div id="tab-mirror" class="panel" style="display: block;">
                <div id="mirrorPersonaPanel" style="max-height: 100%; overflow-y: auto;">Loading persona...</div>
                <div id="mirrorEntriesPanel" style="max-height: 120px; overflow-y: auto;">No entries.</div>
                <div style="margin-top: 0.4rem; display: flex; gap: 0.3rem;">
                    <button class="btn" onclick="refinePersona()">✨ Refine</button>
                    <button class="btn" onclick="saveDefault()">💾 Save</button>
                    <button class="btn" onclick="reloadSaved()">📂 Reload</button>
                    <button class="btn" onclick="factoryReset()">⚠️ Reset</button>
                </div>
            </div>
            <div id="tab-cryptostrat" class="panel" style="display: none;">
                <div id="cryptoVaultDisplay" style="margin-bottom: 0.4rem;">Loading vault...</div>
                <div id="cryptoStratSummary" style="max-height: 100%; overflow-y: auto;">Loading strategy...</div>
                <div id="cryptoStratFeedback" style="max-height: 120px; overflow-y: auto;">No feedback.</div>
                <div style="margin-top: 0.4rem; display: flex; gap: 0.3rem;">
                    <button class="btn" onclick="refineCryptoStrat()">✨ Refine</button>
                    <button class="btn" onclick="saveCryptoStrat()">💾 Save</button>
                    <button class="btn" onclick="reloadCryptoStrat()">📂 Reload</button>
                    <button class="btn" onclick="factoryResetCryptoStrat()">⚠️ Reset</button>
                </div>
            </div>
            <div id="tab-account" class="panel" style="display: none;">Loading...</div>
            <div id="tab-email" class="panel" style="display: none;">Loading...</div>
            <div id="tab-lake" class="panel" style="display: none;">Loading...</div>
        </div>
    </div>

    <!-- Bottom 25%: Command Palette -->
    <div class="bottom-bar">
        <div class="btn-row">
            <button class="btn" onclick="sendCommand('/trade account')">💼 Portfolio</button>
            <button class="btn" onclick="sendCommand('/trade positions')">📊 Positions</button>
            <button class="btn" onclick="sendCommand('/email check')">📧 Inbox</button>
            <button class="btn" onclick="sendCommand('/crypto-sim account')">🪙 Crypto-Sim</button>
            <button class="btn" onclick="sendCommand('/lake good service')">🌊 Lake Search</button>
            <button class="btn" onclick="sendCommand('/persona')">👤 Persona</button>
        </div>
        <div class="status-panel">
            <div id="vaultStatus" class="status">Vault: --</div>
            <div id="cmdOutput" class="status" style="flex:1; overflow-y:auto;"></div>
        </div>
    </div>

    <script>
        // === Chat ===
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
            const resp = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
            const data = await resp.json();
            addMessage('jeeves', data.reply);
            if (text.startsWith('/mirror')) loadMirrorPanel();
        }
        async function fetchCommand(cmd) {
            const resp = await fetch('/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: cmd }) });
            const data = await resp.json();
            return data.reply;
        }
        async function sendCommand(cmd) {
            const reply = await fetchCommand(cmd);
            document.getElementById('cmdOutput').textContent = reply;
        }

        // === Tabs ===
        function showTab(tabName) {
            document.querySelectorAll('.tab-content > div').forEach(el => el.style.display = 'none');
            const target = document.getElementById('tab-' + tabName);
            if (target) target.style.display = 'block';
            document.querySelectorAll('.tab-buttons .tab').forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('data-tab') === tabName) btn.classList.add('active');
            });
            if (tabName === 'email') loadEmail();
            if (tabName === 'account') loadAccount();
            if (tabName === 'mirror') loadMirrorPanel();
            if (tabName === 'lake') loadLake();
            if (tabName === 'cryptostrat') loadCryptoStrat();
        }

        async function loadEmail() { document.getElementById('tab-email').textContent = await fetchCommand('/email check'); }
        async function loadAccount() {            const resp = await fetch('/account_summary');            const text = await resp.text();            document.getElementById('tab-account').textContent = text;        }
        async function loadLake() { document.getElementById('tab-lake').textContent = await fetchCommand('/lake good service'); }

        // === Mirror ===
        async function loadMirrorPanel() {
            document.getElementById('mirrorPersonaPanel').textContent = await fetchCommand('/persona') || 'No persona.';
            const raw = await fetchCommand('/mirror_read');
            try {
                const entries = JSON.parse(raw);
                document.getElementById('mirrorEntriesPanel').textContent = entries.length ? entries.join('\\n') : 'No entries.';
            } catch(e) { document.getElementById('mirrorEntriesPanel').textContent = raw || 'No entries.'; }
        }
        async function refinePersona() {
            document.getElementById('mirrorPersonaPanel').textContent = 'Refining...';
            const resp = await fetch('/refine_persona', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            setTimeout(loadMirrorPanel, 3000);
        }
        async function saveDefault() {
            const resp = await fetch('/save_default', { method: 'POST' });
            const data = await resp.json();
            alert(data.reply);
        }
        async function reloadSaved() {
            const resp = await fetch('/reload_saved', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            setTimeout(loadMirrorPanel, 3000);
        }
        async function factoryReset() {
            if (!confirm('Erase persona and saved default?')) return;
            const resp = await fetch('/factory_reset', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('mirrorPersonaPanel').textContent = data.reply;
            setTimeout(loadMirrorPanel, 3000);
        }

        // === Crypto Strat ===
        async function loadCryptoStrat() {
            document.getElementById('cryptoStratSummary').textContent = await fetchCommand('/crypto-strat_summary') || 'No strategy.';
            document.getElementById('cryptoStratFeedback').textContent = await fetchCommand('/crypto-strat_read') || 'No feedback.';
            const vault = await fetchCommand('/crypto-vault');
            document.getElementById('cryptoVaultDisplay').textContent = vault || 'Vault: --';
            document.getElementById('vaultStatus').textContent = vault || 'Vault: --';
        }
        async function refineCryptoStrat() {
            document.getElementById('cryptoStratSummary').textContent = 'Refining...';
            const resp = await fetch('/trading_refine', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('cryptoStratSummary').textContent = data.reply;
            loadCryptoStrat();
        }
        async function saveCryptoStrat() {
            const resp = await fetch('/trading_save', { method: 'POST' });
            const data = await resp.json();
            alert(data.reply);
        }
        async function reloadCryptoStrat() {
            const resp = await fetch('/trading_reload', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('cryptoStratSummary').textContent = data.reply;
            loadCryptoStrat();
        }
        async function factoryResetCryptoStrat() {
            if (!confirm('Restore factory strategy?')) return;
            const resp = await fetch('/trading_reset', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('cryptoStratSummary').textContent = data.reply;
            loadCryptoStrat();
        }

        window.onload = function() {
            showTab('mirror');
            loadCryptoStrat();
            // Auto-refresh the active tab every 60 seconds
            setInterval(function() {
                const activeTab = document.querySelector('.tab-buttons .tab.active');
                if (activeTab) {
                    const tabName = activeTab.getAttribute('data-tab');
                    if (tabName === 'mirror') loadMirrorPanel();
                    else if (tabName === 'cryptostrat') loadCryptoStrat();
                    else if (tabName === 'account') loadAccount();
                    else if (tabName === 'email') loadEmail();
                    else if (tabName === 'lake') loadLake();
                }
            }, 10000);
        };
    </script>
<script src="/static/trading.js"></script>
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
    # Conversation memory management commands
    if user_msg.strip().lower() == "/forget":
        lake_utils.clear_conversation_memory()
        return jsonify({'reply': "Conversation memory cleared, sir. A fresh start."})
    if user_msg.strip().lower() == "/memory-save":
        msg = lake_utils.save_conversation_baseline()
        return jsonify({'reply': msg})
    if user_msg.strip().lower() == "/memory-restore":
        msg = lake_utils.restore_conversation_baseline()
        return jsonify({'reply': msg})
    if user_msg.strip().lower() == "/memory-status":
        msg = lake_utils.memory_status()
        return jsonify({'reply': msg})
    if user_msg.startswith('/'):
        reply = handle_command(user_msg)
    else:
        # --- Retrieve past conversation context ---
        memory_context = ""
        try:
            past = lake_utils.retrieve_conversation_context(user_msg, n=3)
            if past:
                memory_context = "Previous conversation highlights:\n" + "\n".join(past)
        except:
            pass

        # --- Lake and web search as before ---
        lake_context = ""
        try:
            snippets, best_score = lake_utils.query_lake(user_msg, n=3)
            if snippets and best_score < 0.6:
                lake_context = "🌊 Private knowledge lake results:\n" + "\n".join(snippets)
        except:
            pass
        if not lake_context and config.WEB_SEARCH_ENABLED:
            web_results = web_search.search(user_msg, max_results=3, daily_limit=50)
            if web_results:
                lake_context = "📡 Web results (nothing in your private lake):\n"
                for r in web_results:
                    lake_context += f"- {r['title']}: {r['snippet']}\n"

        # --- Combine all context ---
        all_context = ""
        if memory_context:
            all_context += memory_context + "\n\n"
        if lake_context:
            all_context += lake_context + "\n\n"
        if all_context:
            user_msg = f"Using the following information, answer the user's question. If the information is not relevant, say so.\n\n{all_context}User question: {user_msg}"
    with open(os.path.expanduser("~/chat_prompt.log"), "a") as pf:
        pf.write(f"{datetime.datetime.now().isoformat()} PROMPT: {user_msg}\
\
")
        reply = ask_llm(user_msg)

        # --- Summarise this exchange and store it ---
        try:
            summary_prompt = f"Summarise the following exchange in one concise sentence, capturing the key topic.\nUser: {user_msg}\nAssistant: {reply}"
            summary = ask_llm(summary_prompt)
            if summary and len(summary) > 10:
                lake_utils.store_conversation_summary(summary)
        except:
            pass

    return jsonify({'reply': reply})

@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    cmd = data.get('command', '')
    reply = handle_command(cmd)
    return jsonify({'reply': reply})

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
                persona_text = f.read().strip().replace('\n', ' ')
            return "Current persona: " + persona_text
        except Exception as e:
            return f"Unable to read persona file: {e}"
    # Email (stubbed)
    elif cmd == "/email":
        return "Email module not yet available, sir."
    # Trading (via trading_advisor)
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

    elif cmd == "/crypto-strat_summary":
        try:
            core = open(os.path.expanduser("~/crypto_sim_strategy_core.txt")).read().strip()
            changes = open(os.path.expanduser("~/crypto_strategy_changelog.txt")).read().strip()
            if changes:
                return core + "\n\n--- Change Log ---\n" + changes
            return core
        except:
            return "No strategy file found."

    elif cmd == "/crypto-strat_read":
        try:
            with open(os.path.expanduser("~/crypto_strategy_feedback.log"), "r") as f:
                lines = [line.strip() for line in f.readlines()[-3:] if line.strip()]
            if lines:
                return "\n".join(lines)
            return "No feedback."
        except:
            return "No feedback."

    elif cmd == "/crypto-vault":
        try:
            with open(os.path.expanduser("~/crypto_sim_vault.json"), "r") as f:
                vault = json.load(f)
            return f"Core Capital: ${vault['core_capital']:.2f}, Secured Vault: ${vault['secured_vault']:.2f}"
        except:
            return "Vault data unavailable."
    elif cmd == "/crypto-strat_apply":
        try:
            fb_path = os.path.expanduser("~/crypto_strategy_feedback.log")
            core_path = os.path.expanduser("~/crypto_sim_strategy_core.txt")
            change_path = os.path.expanduser("~/crypto_strategy_changelog.txt")
            strat_path = os.path.expanduser("~/crypto_sim_strategy.txt")
            with open(fb_path, "r") as f:
                entries = f.readlines()
            if not entries:
                return "No feedback to apply."
            all_fb = "\n".join([e.strip().split(" | ",1)[-1] for e in entries if " | " in e])
            core = open(core_path).read().strip()
            changes = open(change_path).read().strip()
            prompt = f"You are a strategy editor. The locked core strategy is:\n\n{core}\n\nThe current change log is:\n\n{changes}\n\nThe user has given this feedback:\n\n{all_fb}\n\nProduce a revised change log (one or two lines) that incorporates the feedback. Do NOT modify the core strategy. The change log should contain ONLY specific modifications, such as 'be 20% more aggressive on ETH' or 'widen stop-loss to 6%'. Output ONLY the revised change log text."
            resp = requests.post(LLM_URL, json={
                "model": "llama",
                "messages": [{"role":"user","content":prompt}],
                "temperature":0.7,"max_tokens":200
            }, timeout=60)
            if resp.ok:
                new_changes = resp.json()["choices"][0]["message"]["content"].strip()
                with open(change_path, "w") as f:
                    f.write(new_changes)
                # Rebuild the strategy file
                final = core + "\n\n" + new_changes if new_changes else core
                with open(strat_path, "w") as f:
                    f.write(final.strip())
                with open(fb_path, "w") as f:
                    f.write("")
                return f"Strategy refined, sir. Change log now: {new_changes}"
            else:
                return "I am unable to refine the strategy at the moment."
        except Exception as e:
            return f"Error: {e}"

    elif cmd == "/crypto-strat_summary":
        try:
            core = open(os.path.expanduser("~/crypto_sim_strategy_core.txt")).read().strip()
            changes = open(os.path.expanduser("~/crypto_strategy_changelog.txt")).read().strip()
            if changes:
                return core + "\n\n--- Change Log ---\n" + changes
            return core
        except:
            return "No strategy file found."

    elif cmd == "/crypto-strat_read":
        try:
            with open(os.path.expanduser("~/crypto_strategy_feedback.log"), "r") as f:
                lines = [line.strip() for line in f.readlines()[-3:] if line.strip()]
            if lines:
                return "\n".join(lines)
            return "No feedback."
        except:
            return "No feedback."
    return None

def ask_llm(question):
    try:
        persona = open(PERSONA_FILE).read().strip().replace('{AI_NAME}', config.AI_NAME)
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

# Mirror refinement routes (stubbed for now)
@app.route('/refine_persona', methods=['POST'])
def refine_persona():
    """Generate a persona revision and apply it immediately, clearing feedback."""
    import mirror_engine
    llm = config.LLM_URL
    active = mirror_engine.persona_active_path()
    log = mirror_engine.persona_log_path()
    instruction = "You are a system prompt editor. Revise the current persona text based on user feedback."
    proposed, error = mirror_engine.apply_feedback(log, active, llm, system_instruction=instruction, max_tokens=300, temperature=0.7)
    if error:
        return jsonify({"reply": f"Refinement failed: {error}"})
    # Apply immediately and clear the feedback log
    msg = mirror_engine.confirm_apply(proposed, active, log)
    return jsonify({"reply": proposed})

@app.route('/save_default', methods=['POST'])
def save_default():
    """Save the current active persona as a personal baseline."""
    import mirror_engine
    active = mirror_engine.persona_active_path()
    saved = mirror_engine.persona_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@app.route('/reload_saved', methods=['POST'])
def reload_saved():
    """Restore the personal baseline persona."""
    import mirror_engine
    active = mirror_engine.persona_active_path()
    saved = mirror_engine.persona_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@app.route('/factory_reset', methods=['POST'])
def factory_reset():
    """Restore the factory default persona (and overwrite saved baseline)."""
    import mirror_engine
    active = mirror_engine.persona_active_path()
    saved = mirror_engine.persona_saved_path()
    factory = mirror_engine.persona_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})


@app.route('/trading_refine', methods=['POST'])
def trading_refine():
    import mirror_engine
    llm = config.LLM_URL
    active = mirror_engine.trading_active_path()
    log = mirror_engine.trading_log_path()
    instruction = "You are a trading strategy editor. Revise the current strategy based on user feedback."
    proposed, error = mirror_engine.apply_feedback(log, active, llm, system_instruction=instruction, max_tokens=400, temperature=0.7)
    if error:
        return jsonify({"reply": f"Refinement failed: {error}"})
    mirror_engine.confirm_apply(proposed, active, log)
    return jsonify({"reply": proposed})

@app.route('/trading_save', methods=['POST'])
def trading_save():
    import mirror_engine
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@app.route('/trading_reload', methods=['POST'])
def trading_reload():
    import mirror_engine
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@app.route('/trading_reset', methods=['POST'])
def trading_reset():
    import mirror_engine
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    factory = mirror_engine.trading_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})

@app.route("/account_summary")
def account_summary():
    import trading_advisor
    account = trading_advisor.get_account()
    positions = trading_advisor.get_positions()
    if not account:
        return "Alpaca account not accessible."
    lines = []
    lines.append(f"Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
    lines.append(f"Cash: ${float(account.get('cash', 0)):,.2f}")
    if positions:
        lines.append("\nHoldings:")
        for p in positions:
            symbol = p.get('symbol', "?")
            qty = p.get('qty', "0")
            mkt_val = float(p.get('market_value', 0))
            unreal_pl = float(p.get('unrealized_pl', 0))
            lines.append(f"  {symbol}: {qty} shares | Value ${mkt_val:,.2f} | Unrealized P/L ${unreal_pl:+,.2f}")
    else:
        lines.append("\nNo current positions.")
    return "\n".join(lines)

@app.route('/landing')
def landing():
    return send_file(os.path.expanduser('~/landing.html'))

@app.route('/favicon.png')
def favicon():
    return send_file(os.path.expanduser('~/favicon.png'), mimetype='image/png')

from trading_blueprint import trading_bp
app.register_blueprint(trading_bp)
if __name__ == "__main__":
    print(f"{config.AI_NAME} web interface starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
