import os, json, csv, io, uuid, datetime as _dt, re, requests
from flask import Blueprint, render_template_string, request, jsonify
import chromadb
from chromadb.utils import embedding_functions

dashboard_bp = Blueprint('dashboard_bp', __name__)

# ------------------------------------------------------------
# API Key Storage
# ------------------------------------------------------------
API_KEYS_FILE = os.path.expanduser("~/api_keys.json")

def load_api_keys():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE) as f:
            return json.load(f)
    return []

def save_api_keys(keys):
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

@dashboard_bp.route("/add_api_key", methods=["POST"])
def add_api_key():
    data = request.get_json()
    label = data.get("label", "").strip()
    key = data.get("key", "").strip()
    secret = data.get("secret", "").strip()
    passphrase = data.get("passphrase", "").strip()
    module = data.get("module", "").strip()
    if not label or not key or not secret:
        return jsonify({"status":"error","message":"Label, Key, and Secret are required."}), 400
    keys = load_api_keys()
    keys = [k for k in keys if not (k["label"] == label and k["module"] == module)]
    keys.append({"label":label,"key":key,"secret":secret,"passphrase":passphrase,"module":module})
    save_api_keys(keys)
    return jsonify({"status":"ok","message":f"API key '{label}' saved for {module}."})

# ------------------------------------------------------------
# Wellness Upload API
# ------------------------------------------------------------
@dashboard_bp.route("/wellness_upload_api", methods=["POST"])
def wellness_upload_api():
    if 'file' not in request.files:
        return jsonify({"status":"error","message":"No file provided."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status":"error","message":"No file selected."}), 400
    try:
        raw = file.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"status":"error","message":"File must be UTF-8."}), 400
    rows = []
    if file.filename.lower().endswith('.json'):
        try:
            data = json.loads(raw)
            if isinstance(data, list): rows = data
            elif isinstance(data, dict): rows = [data]
        except json.JSONDecodeError:
            return jsonify({"status":"error","message":"Invalid JSON."}), 400
    else:
        try:
            reader = csv.DictReader(io.StringIO(raw))
            rows = list(reader)
        except csv.Error:
            return jsonify({"status":"error","message":"Invalid CSV."}), 400
    if not rows:
        return jsonify({"status":"error","message":"No data rows found."}), 400
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    collection = client.get_or_create_collection(name="wellness_data", embedding_function=ef)
    count = 0
    for row in rows:
        parts = []
        for k,v in row.items():
            try:
                parts.append(f"{k}: {float(v)}")
            except (ValueError, TypeError):
                pass
        if not parts: continue
        doc = " | ".join(parts)
        meta = {"source":"upload","filename":file.filename}
        collection.add(documents=[doc], metadatas=[meta], ids=[str(uuid.uuid4())])
        count += 1
    return jsonify({"status":"ok","message":f"Ingested {count} records."})

# ------------------------------------------------------------
# Dashboard HTML
# ------------------------------------------------------------


# --- Trading endpoints (Stocks) ---
@dashboard_bp.route("/trading_summary")
def trading_summary():
    import config
    try:
        with open(config.TRADING_STRATEGY_FILE) as f:
            return f.read().strip()
    except:
        return "No stock strategy found."

@dashboard_bp.route("/account_summary")
def account_summary():
    import trading_advisor
    account = trading_advisor.get_account()
    positions = trading_advisor.get_positions()
    if not account:
        return "Alpaca account not accessible."
    lines = [f"Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}",
             f"Cash: ${float(account.get('cash', 0)):,.2f}"]
    if positions:
        lines.append("\nHoldings:")
        for p in positions:
            symbol = p.get("symbol", "?")
            qty = p.get("qty", "0")
            mkt_val = float(p.get("market_value", 0))
            unreal_pl = float(p.get("unrealized_pl", 0))
            lines.append(f"  {symbol}: {qty} shares | Value ${mkt_val:,.2f} | Unrealized P/L ${unreal_pl:+,.2f}")
    else:
        lines.append("\nNo current positions.")
    return "\n".join(lines)

@dashboard_bp.route("/trading_refine", methods=["POST"])
def trading_refine():
    import mirror_engine, config
    from flask import jsonify
    llm = config.LLM_URL
    active = mirror_engine.trading_active_path()
    log = mirror_engine.trading_log_path()
    instruction = "You are a trading strategy editor. Revise the current strategy based on user feedback."
    proposed, error = mirror_engine.apply_feedback(log, active, llm, system_instruction=instruction, max_tokens=400, temperature=0.7)
    if error:
        return jsonify({"reply": f"Refinement failed: {error}"})
    if not proposed or not proposed.strip():
        return jsonify({"reply": "Refinement failed: empty response."})
    mirror_engine.confirm_apply(proposed, active, log)
    return jsonify({"reply": proposed})

@dashboard_bp.route("/trading_save", methods=["POST"])
def trading_save():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@dashboard_bp.route("/trading_reload", methods=["POST"])
def trading_reload():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@dashboard_bp.route("/trading_reset", methods=["POST"])
def trading_reset():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    factory = mirror_engine.trading_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})

# --- Crypto endpoints ---
@dashboard_bp.route("/crypto_summary")
def crypto_summary():
    import config
    try:
        with open(config.CRYPTO_STRATEGY_FILE) as f:
            return f.read().strip()
    except:
        return "No crypto strategy found."

@dashboard_bp.route("/crypto_account_summary")
def crypto_account_summary():
    """Return a detailed paper account summary: equity, positions, and last trade."""
    import crypto_sim
    account = crypto_sim.get_account()
    positions = crypto_sim.get_positions()
    data = crypto_sim._load()
    last_trade = "No trades yet."
    if data.get("trades"):
        t = data["trades"][-1]
        last_trade = f"{t['timestamp'][:19]}: {t['side'].upper()} {t['qty']} {t['symbol']} @ ${t['price']}"
    return account + "\n\n" + positions + "\n\nLast trade: " + last_trade

@dashboard_bp.route("/crypto_refine", methods=["POST"])
def crypto_refine():
    import mirror_engine, config
    from flask import jsonify
    llm = config.LLM_URL
    active = mirror_engine.crypto_active_path()
    log = mirror_engine.crypto_log_path()
    instruction = "You are a crypto trading strategy editor. Revise the current strategy based on user feedback."
    proposed, error = mirror_engine.apply_feedback(log, active, llm, system_instruction=instruction, max_tokens=400, temperature=0.7)
    if error:
        return jsonify({"reply": f"Refinement failed: {error}"})
    if not proposed or not proposed.strip():
        return jsonify({"reply": "Refinement failed: empty response."})
    mirror_engine.confirm_apply(proposed, active, log)
    return jsonify({"reply": proposed})

@dashboard_bp.route("/crypto_save", methods=["POST"])
def crypto_save():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@dashboard_bp.route("/crypto_reload", methods=["POST"])
def crypto_reload():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@dashboard_bp.route("/crypto_reset", methods=["POST"])
def crypto_reset():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    factory = mirror_engine.crypto_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})


@dashboard_bp.route("/live_crypto_account")
def live_crypto_account():
    """Return live Coinbase balances if keys are configured."""
    try:
        from coinbase.rest import RESTClient
        import config
        client = RESTClient(
            api_key=config.COINBASE_API_KEY,
            api_secret=config.COINBASE_API_SECRET
        )
        accounts = client.get_accounts()
        balances = {}
        for acct in accounts['accounts']:
            amt = float(acct['available_balance']['value'])
            if amt > 0:
                balances[acct['currency']] = amt
        if not balances:
            return "No Coinbase balances found."
        lines = []
        for currency, amount in balances.items():
            lines.append(f"{currency}: {amount}")
        return "\n".join(lines)
    except Exception as e:
        return f"Coinbase live account unavailable: {e}"

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Dashboard</title>
    <link rel="icon" type="image/png" href="/favicon.png">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 45%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 45%; display: flex; flex-direction: column; background: #1e1e1e; }
        .tab-buttons { display: flex; flex-wrap: wrap; gap: 0.2rem; padding: 0.3rem 0.6rem; background: #2c2c2c; }
        .tab { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.5rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; text-decoration: none; }
        .tab.active { background: #c0a878; color: #1a1a1a; border-color: #c0a878; }
        .tab-content { flex: 1; overflow-y: auto; padding: 0.6rem; }
        .bottom-bar { height: 10%; display: flex; align-items: center; gap: 0.4rem; padding: 0 0.6rem; background: #2c2c2c; }
        .bottom-bar button { padding: 0.35rem 0.7rem; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .panel { margin-bottom: 0.8rem; }
        .section { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.6rem; margin-bottom: 0.6rem; }
        .section h2 { font-size: 1.0rem; color: #c0a878; margin-bottom: 0.4rem; }
        input, textarea { width: 100%; padding: 0.4rem; margin-bottom: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; font-family: inherit; }
        .btn { padding: 0.35rem 0.7rem; background: #c0a878; border: none; border-radius: 3px; color: #1a1a1a; font-weight: bold; cursor: pointer; font-size: 0.85rem; margin-right: 0.3rem; }
        .status { font-size: 0.8rem; color: #888; margin-left: 0.5rem; }
        .drop-zone { border: 2px dashed #555; border-radius: 6px; padding: 1rem; text-align: center; color: #888; cursor: pointer; transition: 0.2s; margin-bottom: 0.5rem; }
        .drop-zone:hover { border-color: #c0a878; }
        .message { margin-bottom: 0.4rem; }
        .message.user { text-align: right; color: #a0c0ff; }
        .message.jeeves { text-align: left; color: #c0a878; }
    </style>
</head>
<body>
<div class="top-bar">
    <div class="chat-messages" id="messages"><div class="message jeeves">Good day, sir. How may I assist?</div></div>
    <div class="chat-input">
        <input type="text" id="userInput" placeholder="Speak to your valet..." onkeypress="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()">Send</button>
        <button id="micButton" onclick="toggleMic()" style="background:#3c3c3c;border:1px solid #555;color:#fff;border-radius:4px;cursor:pointer;">🎤</button>
    </div>
</div>

<div class="middle-area">
    <div class="tab-buttons">
        <button class="tab active" data-tab="persona" onclick="showTab('persona')">👤 Persona</button>
        <button class="tab" data-tab="wellness" onclick="showTab('wellness')">💚 Wellness</button>
        <button class="tab" data-tab="datalake" onclick="showTab('datalake')">🌊 Data Lake</button>
        <button class="tab" data-tab="stocks" onclick="showTab('stocks')">📈 Stocks</button>
        <button class="tab" data-tab="crypto" onclick="showTab('crypto')">🪙 Crypto</button>
        <button class="tab" data-tab="email" onclick="showTab('email')">📧 Email</button>
        <button class="tab" data-tab="settings" onclick="showTab('settings')">⚙️ Settings</button>
    </div>
    <div class="tab-content">
        <!-- Persona -->
        <div id="tab-persona" class="panel" style="display:block;">
            <div class="section">
                <h2>Current Persona</h2>
                <div id="personaSummary" style="white-space:pre-wrap;min-height:3rem;">Loading...</div>
            </div>
            <div class="section">
                <h2>Mirror Feedback</h2>
                <input type="text" id="personaFeedback" placeholder="Feedback for the Mirror...">
                <button class="btn" onclick="submitFeedback()">✨ Refine</button>
            </div>
        </div>

        <!-- Wellness -->
        <div id="tab-wellness" class="panel" style="display:none;">
            <div class="section">
                <h2>Quick Log</h2>
                <input type="text" id="wellnessLogInput" placeholder="e.g., add to wellness I had 4 eggs">
                <button class="btn" onclick="logWellness()">📝 Log</button>
            </div>
            <div class="section">
                <h2>Upload Fitness Data</h2>
                <div class="drop-zone" id="wellnessDropZone"
                     onclick="document.getElementById('wellnessFileInput').click()"
                     ondragover="event.preventDefault(); this.style.borderColor='#c0a878';"
                     ondragleave="event.preventDefault(); this.style.borderColor='#555';"
                     ondrop="event.preventDefault(); this.style.borderColor='#555'; handleWellnessDrop(event);">
                    <div>📁 Drop CSV/JSON or click</div>
                    <input type="file" id="wellnessFileInput" style="display:none;" accept=".csv,.json" onchange="handleWellnessFiles(this.files)" multiple>
                </div>
                <span class="status" id="wellnessUploadStatus"></span>
            </div>
        </div>

        <!-- Data Lake -->
        <div id="tab-datalake" class="panel" style="display:none;">
            <div class="section">
                <h2>Lake Search</h2>
                <input type="text" id="lakeQuery" placeholder="Search your knowledge lake...">
                <button class="btn" onclick="searchLake()">🔍 Search</button>
                <div id="lakeResults" style="margin-top:0.5rem; white-space:pre-wrap;"></div>
            </div>
        </div>

        <!-- Stocks -->
        <div id="tab-stocks" class="panel" style="display:none;">
            <div class="section">
                <h2>Stock Strategy</h2>
                <div id="stockStrategy" style="white-space:pre-wrap;min-height:3rem;">Loading...</div>
                <input type="text" id="stockFeedback" placeholder="Strategy feedback...">
                <button class="btn" onclick="refineStocks()">✨ Refine</button>
            </div>
            <div class="section">
                <h2>Alpaca Account</h2>
                <div id="stockAccount" style="white-space:pre-wrap;">Loading...</div>
            </div>
        </div>

        <!-- Crypto -->
        <div id="tab-crypto" class="panel" style="display:none;">
            <div class="section">
                <h2>Crypto Strategy</h2>
                <div id="cryptoStrategy" style="white-space:pre-wrap;min-height:3rem;">Loading...</div>
                <input type="text" id="cryptoFeedback" placeholder="Strategy feedback...">
                <button class="btn" onclick="refineCrypto()">✨ Refine</button>
            </div>
            <div class="section">
                <h2>Coinbase Account</h2>
                <div style="margin-bottom:0.5rem;"><strong>Live Coinbase:</strong></div><div id="cryptoAccount" style="white-space:pre-wrap;">Loading...</div><div style="margin-top:0.5rem;"><strong>Paper Sim:</strong></div><div id="cryptoPaperAccount" style="white-space:pre-wrap;">Loading...</div>
            </div>
        </div>

        <!-- Email -->
        <div id="tab-email" class="panel" style="display:none;">
            <div class="section">
                <h2>Email (Coming Soon)</h2>
                <div style="color:#888;">Read, summarise, and draft emails with your approval.</div>
            </div>
        </div>

        <!-- Settings -->
        <div id="tab-settings" class="panel" style="display:none;">
            <div class="section">
                <h2>📈 Stocks API Key</h2>
                <input type="text" id="apiLabel_Stocks" placeholder="Label (e.g., Alpaca)">
                <input type="password" id="apiKey_Stocks" placeholder="API Key">
                <input type="password" id="apiSecret_Stocks" placeholder="API Secret">
                <input type="text" id="apiPassphrase_Stocks" placeholder="Passphrase (optional)">
                <button class="btn" onclick="saveApiKey('Stocks')">Save Key</button>
                <span class="status" id="apiStatus_Stocks"></span>
            </div>
            <div class="section">
                <h2>🪙 Crypto API Key</h2>
                <input type="text" id="apiLabel_Crypto" placeholder="Label (e.g., Coinbase)">
                <input type="password" id="apiKey_Crypto" placeholder="API Key">
                <input type="password" id="apiSecret_Crypto" placeholder="API Secret">
                <input type="text" id="apiPassphrase_Crypto" placeholder="Passphrase (optional)">
                <button class="btn" onclick="saveApiKey('Crypto')">Save Key</button>
                <span class="status" id="apiStatus_Crypto"></span>
            </div>
            <div class="section">
                <h2>💚 Wellness API Key</h2>
                <input type="text" id="apiLabel_Wellness" placeholder="Label (e.g., Strava)">
                <input type="password" id="apiKey_Wellness" placeholder="API Key">
                <input type="password" id="apiSecret_Wellness" placeholder="API Secret">
                <input type="text" id="apiPassphrase_Wellness" placeholder="Passphrase (optional)">
                <button class="btn" onclick="saveApiKey('Wellness')">Save Key</button>
                <span class="status" id="apiStatus_Wellness"></span>
            </div>
            <div class="section">
                <h2>📧 Email API Key</h2>
                <input type="text" id="apiLabel_Email" placeholder="Label (e.g., Gmail)">
                <input type="password" id="apiKey_Email" placeholder="API Key">
                <input type="password" id="apiSecret_Email" placeholder="API Secret">
                <input type="text" id="apiPassphrase_Email" placeholder="Passphrase (optional)">
                <button class="btn" onclick="saveApiKey('Email')">Save Key</button>
                <span class="status" id="apiStatus_Email"></span>
            </div>
        </div>
    </div>
</div>

<div class="bottom-bar" id="bottomBar">
    <!-- dynamically filled -->
</div>

<script>
// ---- Chat ----
async function sendMessage() {
    const input = document.getElementById('userInput');
    const text = input.value.trim();
    if (!text) return;
    addMessage('user', text);
    input.value = '';
    const resp = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text}) });
    const data = await resp.json();
    addMessage('jeeves', data.reply);
}
function addMessage(sender, text) {
    const msg = document.createElement('div');
    msg.className = 'message ' + sender;
    msg.textContent = text;
    document.getElementById('messages').appendChild(msg);
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
}

// ---- Microphone ----
let mediaRecorder, audioChunks = [];
async function toggleMic() {
    const btn = document.getElementById('micButton');
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        btn.textContent = '🎤'; btn.style.background = '#3c3c3c';
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mime = MediaRecorder.isTypeSupported('audio/webm; codecs=opus') ? 'audio/webm; codecs=opus' : 'audio/webm';
            mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
            audioChunks = [];
            mediaRecorder.addEventListener('dataavailable', e => audioChunks.push(e.data));
            mediaRecorder.addEventListener('stop', async () => {
                const blob = new Blob(audioChunks, { type: mime });
                const form = new FormData(); form.append('audio', blob, 'rec.webm');
                btn.textContent = '⏳'; btn.style.background = '#888';
                const resp = await fetch('/transcribe', { method:'POST', body:form });
                const data = await resp.json();
                if (data.text) document.getElementById('userInput').value = data.text;
                else alert('Transcription failed: ' + (data.error||''));
                btn.textContent = '🎤'; btn.style.background = '#3c3c3c';
            });
            mediaRecorder.start();
            btn.textContent = '⏹️'; btn.style.background = '#c0a878';
        } catch(e) { alert('Microphone access denied.'); }
    }
}

// ---- Tabs ----
function showTab(name) {
    document.querySelectorAll('.tab-content > div').forEach(el => el.style.display = 'none');
    const target = document.getElementById('tab-' + name);
    if (target) target.style.display = 'block';
    document.querySelectorAll('.tab-buttons .tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === name) btn.classList.add('active');
    });
    if (name === 'persona') { loadPersona(); updateBottomBar('persona'); }
    else if (name === 'stocks') { loadStocks(); updateBottomBar('stocks'); }
    else if (name === 'crypto') { loadCrypto(); updateBottomBar('crypto'); }
    else updateBottomBar(name);
}
function updateBottomBar(tab) {
    const bar = document.getElementById('bottomBar');
    const bars = {
        persona: `<button class="btn" onclick="savePersona()">💾 Save</button><button class="btn" onclick="reloadPersona()">📂 Reload</button><button class="btn" onclick="resetPersona()">⚠️ Reset</button><button class="btn" onclick="loadPersona()">↻ Refresh</button>`,
        stocks: `<button class="btn" onclick="saveStocks()">💾 Save</button><button class="btn" onclick="reloadStocks()">📂 Reload</button><button class="btn" onclick="resetStocks()">⚠️ Reset</button>`,
        crypto: `<button class="btn" onclick="saveCrypto()">💾 Save</button><button class="btn" onclick="reloadCrypto()">📂 Reload</button><button class="btn" onclick="resetCrypto()">⚠️ Reset</button>`,
    };
    bar.innerHTML = bars[tab] || '';
}

// ---- Persona ----
async function loadPersona() {
    document.getElementById('personaSummary').textContent = await fetchCommand('/persona') || 'No persona.';
}
async function submitFeedback() {
    const input = document.getElementById('personaFeedback');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    await fetchCommand('/mirror ' + text);
    const resp = await fetch('/refine_persona', { method:'POST' });
    const data = await resp.json();
    document.getElementById('personaSummary').textContent = data.reply;
    setTimeout(loadPersona, 2000);
}
async function savePersona() { alert((await (await fetch('/save_default',{method:'POST'})).json()).reply); }
async function reloadPersona() {
    const resp = await fetch('/reload_saved',{method:'POST'});
    const data = await resp.json();
    document.getElementById('personaSummary').textContent = data.reply;
    setTimeout(loadPersona, 2000);
}
async function resetPersona() {
    if (!confirm('Restore factory persona?')) return;
    const resp = await fetch('/factory_reset',{method:'POST'});
    const data = await resp.json();
    document.getElementById('personaSummary').textContent = data.reply;
    setTimeout(loadPersona, 2000);
}

// ---- Wellness ----
async function logWellness() {
    const input = document.getElementById('wellnessLogInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    const resp = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:'add to wellness '+text}) });
    const data = await resp.json();
    alert(data.reply);
}
function handleWellnessDrop(event) { handleWellnessFiles(event.dataTransfer.files); }
async function handleWellnessFiles(files) {
    const status = document.getElementById('wellnessUploadStatus');
    status.textContent = 'Uploading...';
    for (const file of files) {
        const form = new FormData(); form.append('file', file);
        const resp = await fetch('/wellness_upload_api', { method:'POST', body:form });
        const data = await resp.json();
        status.textContent = data.message;
    }
}

// ---- Data Lake ----
async function searchLake() {
    const q = document.getElementById('lakeQuery').value.trim();
    if (!q) return;
    document.getElementById('lakeResults').textContent = await fetchCommand('/lake ' + q);
}

// ---- Stocks ----
async function loadStocks() {
    document.getElementById('stockStrategy').textContent = await (await fetch('/trading_summary')).text() || 'No strategy.';
    document.getElementById('stockAccount').textContent = await (await fetch('/account_summary')).text() || 'Account unavailable.';
}
async function refineStocks() {
    const input = document.getElementById('stockFeedback');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    await fetchCommand('/trade-mirror ' + text);
    document.getElementById('stockStrategy').textContent = 'Refining...';
    const resp = await fetch('/trading_refine', { method:'POST' });
    const data = await resp.json();
    document.getElementById('stockStrategy').textContent = data.reply;
}
async function saveStocks() { alert((await (await fetch('/trading_save',{method:'POST'})).json()).reply); }
async function reloadStocks() {
    const resp = await fetch('/trading_reload',{method:'POST'});
    const data = await resp.json();
    document.getElementById('stockStrategy').textContent = data.reply;
}
async function resetStocks() {
    if (!confirm('Restore factory stock strategy?')) return;
    const resp = await fetch('/trading_reset',{method:'POST'});
    const data = await resp.json();
    document.getElementById('stockStrategy').textContent = data.reply;
}

// ---- Crypto ----
async function loadCrypto() {
    document.getElementById('cryptoStrategy').textContent = await (await fetch('/crypto_summary')).text() || 'No strategy.';
    document.getElementById('cryptoAccount').textContent = await (await fetch('/live_crypto_account')).text() || 'Account unavailable.';
    document.getElementById('cryptoPaperAccount').textContent = await (await fetch('/crypto_account_summary')).text() || 'Account unavailable.';
}
async function refineCrypto() {
    const input = document.getElementById('cryptoFeedback');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    await fetchCommand('/crypto-strat ' + text);
    document.getElementById('cryptoStrategy').textContent = 'Refining...';
    const resp = await fetch('/crypto_refine', { method:'POST' });
    const data = await resp.json();
    document.getElementById('cryptoStrategy').textContent = data.reply;
}
async function saveCrypto() { alert((await (await fetch('/crypto_save',{method:'POST'})).json()).reply); }
async function reloadCrypto() {
    const resp = await fetch('/crypto_reload',{method:'POST'});
    const data = await resp.json();
    document.getElementById('cryptoStrategy').textContent = data.reply;
}
async function resetCrypto() {
    if (!confirm('Restore factory crypto strategy?')) return;
    const resp = await fetch('/crypto_reset',{method:'POST'});
    const data = await resp.json();
    document.getElementById('cryptoStrategy').textContent = data.reply;
}

// ---- API Keys (Settings) ----
async function saveApiKey(module) {
    const label = document.getElementById('apiLabel_'+module).value.trim();
    const key   = document.getElementById('apiKey_'+module).value.trim();
    const secret = document.getElementById('apiSecret_'+module).value.trim();
    const pass   = document.getElementById('apiPassphrase_'+module).value.trim();
    if (!label || !key || !secret) { alert('Label, Key, and Secret are required.'); return; }
    const status = document.getElementById('apiStatus_'+module);
    status.textContent = 'Saving...';
    const resp = await fetch('/add_api_key', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({label,key,secret,passphrase:pass,module}) });
    const data = await resp.json();
    status.textContent = data.message;
}

// ---- Helpers ----
async function fetchCommand(cmd) {
    const resp = await fetch('/command', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:cmd}) });
    const data = await resp.json();
    return data.reply;
}

window.onload = function() { showTab('persona'); };
</script>
</body>
</html>"""

@dashboard_bp.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_HTML)
