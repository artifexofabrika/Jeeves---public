import os, tempfile, whisper
from flask import Blueprint, render_template_string, request, jsonify

dashboard_bp = Blueprint('dashboard_bp', __name__)

# ------------------------------------------------------------
# Whisper model loaded once at module level (lazy)
# ------------------------------------------------------------
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        import time
        start = time.time()
        whisper_model = whisper.load_model("base.en")
        print(f"Whisper model loaded in {time.time()-start:.1f}s", flush=True)
    return whisper_model

# ------------------------------------------------------------
# Transcription endpoint
# ------------------------------------------------------------
@dashboard_bp.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        audio_file.save(tmp)
        tmp_path = tmp.name
    try:
        model = get_whisper_model()
        result = model.transcribe(tmp_path)
        text = result['text'].strip()
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(tmp_path)

# ------------------------------------------------------------
# The complete dashboard HTML / CSS / JavaScript
# ------------------------------------------------------------

# --- Trading Module Routes (self‑contained) ---
@dashboard_bp.route('/trading_summary')
def trading_summary():
    import config
    try:
        with open(config.TRADING_STRATEGY_FILE) as f:
            return f.read().strip()
    except:
        return "No stock strategy file found."

@dashboard_bp.route('/trading_feedback')
def trading_feedback():
    import mirror_engine, config, json
    entries = mirror_engine.read_feedback(config.TRADING_MIRROR_LOG, n=3)
    return json.dumps(entries)

@dashboard_bp.route('/trading_refine', methods=['POST'])
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

@dashboard_bp.route('/trading_save', methods=['POST'])
def trading_save():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@dashboard_bp.route('/trading_reload', methods=['POST'])
def trading_reload():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@dashboard_bp.route('/trading_reset', methods=['POST'])
def trading_reset():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    factory = mirror_engine.trading_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})

# --- Crypto Strategy Routes ---
@dashboard_bp.route('/crypto_summary')
def crypto_summary():
    import config
    try:
        with open(config.CRYPTO_STRATEGY_FILE) as f:
            return f.read().strip()
    except:
        return "No crypto strategy file found."

@dashboard_bp.route('/crypto_feedback')
def crypto_feedback():
    import mirror_engine, config, json
    entries = mirror_engine.read_feedback(config.CRYPTO_MIRROR_LOG, n=3)
    return json.dumps(entries)

@dashboard_bp.route('/crypto_refine', methods=['POST'])
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

@dashboard_bp.route('/crypto_save', methods=['POST'])
def crypto_save():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@dashboard_bp.route('/crypto_reload', methods=['POST'])
def crypto_reload():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@dashboard_bp.route('/crypto_reset', methods=['POST'])
def crypto_reset():
    import mirror_engine
    from flask import jsonify
    active = mirror_engine.crypto_active_path()
    saved = mirror_engine.crypto_saved_path()
    factory = mirror_engine.crypto_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})

# --- Account Summary ---
@dashboard_bp.route('/account_summary')
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
            symbol = p.get("symbol", "?")
            qty = p.get("qty", "0")
            mkt_val = float(p.get("market_value", 0))
            unreal_pl = float(p.get("unrealized_pl", 0))
            lines.append(f"  {symbol}: {qty} shares | Value ${mkt_val:,.2f} | Unrealized P/L ${unreal_pl:+,.2f}")
    else:
        lines.append("\nNo current positions.")
    return "\n".join(lines)



@dashboard_bp.route('/crypto_account_summary')
def crypto_account_summary():
    import crypto_sim
    return crypto_sim.get_account()


@dashboard_bp.route('/log-wellness', methods=['POST'])
def log_wellness():
    import lake_utils
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'status': 'error', 'reply': 'No message provided.'}), 400
    # Prepend timestamp
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    full_entry = f"{timestamp}: {message}"
    lake_utils.store_wellness_entry(full_entry)
    return jsonify({'status': 'ok', 'reply': f"Logged: {message}"})



# --- Recent Trades ---
@dashboard_bp.route("/recent_trades")
def recent_trades():
    """Return the last 10 paper trades from Alpaca and CoinGecko simulators."""
    trades = []
    # Alpaca trades
    try:
        import trading_advisor
        # Alpaca does not keep a local trade log; we fetch order history from the API
        orders = trading_advisor.get_orders() if hasattr(trading_advisor, 'get_orders') else []
        for o in orders[-5:]:
            trades.append(f"[ALPACA] {o.get('side','?').upper()} {o.get('qty','?')} {o.get('symbol','?')} @ ${o.get('filled_avg_price','?')} ({o.get('status','?')})")
    except Exception as e:
        trades.append(f"Alpaca unavailable: {e}")
    # Crypto simulated trades
    try:
        import crypto_sim, json
        data = crypto_sim._load()
        for t in data.get("trades", [])[-5:]:
            trades.append(f"[CRYPTO] {t.get('side','?').upper()} {t.get('qty','?')} {t.get('symbol','?')} @ ${t.get('price','?')} ({t.get('timestamp','?')})")
    except Exception as e:
        trades.append(f"Crypto sim unavailable: {e}")
    return "\n".join(trades) if trades else "No recent trades."

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Dashboard</title>
    <link rel='icon' type='image/png' href='/favicon.png'>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 45%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 45%; display: flex; flex-direction: column; background: #1e1e1e; }
        .middle-area .tab-buttons { display: flex; flex-wrap: wrap; gap: 0.2rem; padding: 0.3rem 0.6rem; background: #2c2c2c; }
        .middle-area .tab { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.5rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
        .middle-area .tab.active { background: #c0a878; color: #1a1a1a; border-color: #c0a878; }
        .middle-area .tab-content { flex: 1; overflow-y: auto; padding: 0.6rem; }
        .bottom-bar { height: 10%; display: flex; align-items: center; gap: 0.4rem; padding: 0 0.6rem; background: #2c2c2c; }
        .bottom-bar button { padding: 0.35rem 0.7rem; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .bottom-bar button:hover { background: #4c4c4c; }
        .panel { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.6rem; margin-bottom: 0.5rem; white-space: pre-wrap; word-wrap: break-word; font-size: 0.85rem; }
        .message { margin-bottom: 0.4rem; font-size: 0.9rem; }
        .message.user { text-align: right; color: #a0c0ff; }
        .message.jeeves { text-align: left; color: #c0a878; }
    </style>
</head>
<body>
    <!-- Top: Chat -->
    <div class="top-bar">
        <div class="chat-messages" id="messages">
            <div class="message jeeves">Good day, sir. How may I assist?</div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Speak to your valet..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
            <button id="micButton" onclick="toggleMic()" style="background:#3c3c3c;border:1px solid #555;color:#fff;border-radius:4px;cursor:pointer;">🎤</button>
        </div>
    </div>

    <!-- Middle: Modules -->
    <div class="middle-area">
        <div class="tab-buttons">
            <button class="tab active" data-tab="persona" onclick="showTab('persona')">👤 Persona</button>
            <button class="tab" data-tab="wellness" onclick="showTab('wellness')">💚 Wellness</button>
            <button class="tab" data-tab="datalake" onclick="showTab('datalake')">🌊 Data Lake</button>
            <button class="tab" data-tab="trading" onclick="showTab('trading')">📈 Trading</button>
            <button class="tab" data-tab="email" onclick="showTab('email')">📧 Email</button>
        </div>
        <div class="tab-content">
            <div id="tab-persona" class="panel" style="display:block;">
                <div style="font-size:1.1rem;color:#c0a878;margin-bottom:0.5rem;">Current Persona</div>
                <div id="personaSummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;min-height:3rem;overflow-y:auto;white-space:pre-wrap;">Loading...</div>
                <div style="margin-top:0.8rem;display:flex;gap:0.4rem;">
                    <input type="text" id="personaFeedbackInput" placeholder="Add feedback for the Mirror..." style="flex:1;padding:0.4rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;font-size:0.85rem;" onkeypress="if(event.key==='Enter') submitFeedback()">
                    <button class="btn" onclick="submitFeedback()" style="flex-shrink:0;padding:0.4rem 0.8rem;background:#c0a878;border:none;border-radius:4px;color:#1a1a1a;font-weight:bold;">✨ Refine</button>
                </div>
            </div>
            <div id="tab-wellness" class="panel" style="display:none;">
                <div style="display:flex;gap:0.4rem;align-items:center;">
                    <input type="text" id="wellnessInput" placeholder="e.g., had 4 eggs and 2 tbsp coconut oil..." style="flex:1;padding:0.4rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;font-size:0.85rem;" onkeypress="if(event.key==='Enter') logWellness()">
                    <button class="btn" onclick="logWellness()" style="padding:0.4rem 0.8rem;background:#c0a878;border:none;border-radius:4px;color:#1a1a1a;font-weight:bold;">📝 Log</button>
                </div>
                <div id="wellnessStatus" style="margin-top:0.5rem;font-size:0.85rem;color:#888;"></div>
            </div>
            <div id="tab-datalake" class="panel" style="display:none;">
                <div style="margin-bottom:1rem;">
                    <div style="font-size:1.1rem;color:#c0a878;">Lake Search</div>
                    <input type="text" id="lakeQuery" placeholder="Search your knowledge lake..." style="width:100%;padding:0.5rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;margin-bottom:0.4rem;" onkeypress="if(event.key==='Enter') searchLake()">
                    <button onclick="searchLake()" style="padding:0.35rem 0.7rem;background:#c0a878;border:none;border-radius:3px;color:#1a1a1a;font-weight:bold;">🔍 Search</button>
                </div>
                <div id="lakeSearchResults" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;min-height:3rem;">Results will appear here.</div>
            </div>
            <div id="tab-trading" class="panel" style="display:none;padding:0.4rem;white-space:normal;margin-bottom:0;">
                <!-- Sub-tab buttons -->
                <div style="display:flex;gap:0.3rem;margin-bottom:0.4rem;">
                    <button class="tab active" data-subtab="stocks" onclick="showSubTab('stocks')">📈 Stocks</button>
                    <button class="tab" data-subtab="crypto" onclick="showSubTab('crypto')">🪙 Crypto</button>
                </div>
                <!-- Recent Trades box (always visible) -->
                <div style="margin-bottom:0.6rem; border:1px solid #444; border-radius:4px; padding:0.6rem;">
                    <div style="font-size:1.0rem;color:#c0a878;margin-bottom:0.3rem;">Recent Trades</div>
                    <div id="recentTrades" style="background:#1e1e1e;padding:0.4rem;border-radius:4px;min-height:2rem;max-height:100px;overflow-y:auto;white-space:pre-wrap;font-size:0.85rem;">Loading...</div>
<!-- Lake Search for Trading -->
                <div style="margin-bottom:0.6rem; border:1px solid #444; border-radius:4px; padding:0.6rem;">
                    <div style="font-size:1.0rem;color:#c0a878;margin-bottom:0.3rem;">Search Lake for Trading Ideas</div>
                    <input type="text" id="lakeSearchInput" placeholder="e.g., AAPL analysis or Bitcoin outlook..." style="width:100%;padding:0.4rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;font-size:0.85rem;margin-bottom:0.4rem;" onkeypress="if(event.key==='Enter') searchLakeForTrading()">
                    <button onclick="searchLakeForTrading()" style="padding:0.35rem 0.7rem;background:#c0a878;border:none;border-radius:3px;color:#1a1a1a;font-weight:bold;">Search Lake</button>
                    <div id="lakeSearchResults" style="background:#1e1e1e;padding:0.4rem;border-radius:4px;min-height:2rem;max-height:150px;overflow-y:auto;white-space:pre-wrap;font-size:0.85rem;margin-top:0.4rem;"></div>
                </div>

                </div>
                <!-- Stocks sub-panel -->
                <div id="subtrading-stocks" style="display:block;">
                    <div id="stockStrategySummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;min-height:3rem;max-height:300px;overflow-y:auto;white-space:pre-wrap;">Loading...</div>
                    <div style="margin-top:0.6rem;display:flex;gap:0.4rem;">
                        <input type="text" id="stockFeedbackInput" placeholder="Add feedback for stock strategy..." style="flex:1;padding:0.4rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;font-size:0.85rem;" onkeypress="if(event.key==='Enter') refineStocks()">
                        <button class="btn" onclick="refineStocks()" style="flex-shrink:0;">✨ Refine</button>
                    </div>
                    <div style="margin-top:0.6rem; border:1px solid #444; border-radius:4px; padding:0.6rem;">
                        <div style="font-size:1.0rem;color:#c0a878;margin-bottom:0.3rem;">Alpaca Paper Account</div>
                        <div id="stockAccountSummary" style="background:#1e1e1e;padding:0.4rem;border-radius:4px;min-height:2rem;white-space:pre-wrap;">Loading...</div>
                    </div>
                </div>
                <!-- Crypto sub-panel -->
                <div id="subtrading-crypto" style="display:none;">
                    <div id="cryptoStrategySummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;min-height:3rem;max-height:300px;overflow-y:auto;white-space:pre-wrap;">Loading...</div>
                    <div style="margin-top:0.6rem;display:flex;gap:0.4rem;">
                        <input type="text" id="cryptoFeedbackInput" placeholder="Add feedback for crypto strategy..." style="flex:1;padding:0.4rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;font-size:0.85rem;" onkeypress="if(event.key==='Enter') refineCrypto()">
                        <button class="btn" onclick="refineCrypto()" style="flex-shrink:0;">✨ Refine</button>
                    </div>
                    <div style="margin-top:0.6rem; border:1px solid #444; border-radius:4px; padding:0.6rem;">
                        <div style="font-size:1.0rem;color:#c0a878;margin-bottom:0.3rem;">CoinGecko Paper Account</div>
                        <div id="cryptoAccountSummary" style="background:#1e1e1e;padding:0.4rem;border-radius:4px;min-height:2rem;white-space:pre-wrap;">Loading...</div>
                    </div>
                </div>
            </div>
            <div id="tab-email" class="panel" style="display:none;">
                <div style="text-align:center;padding:2rem;color:#888;">
                    <div style="font-size:2rem;">📧</div>
                    <div>Email integration is under development.</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bottom: Context Actions -->
    <div class="bottom-bar" id="bottomBar">
        <!-- dynamically filled -->
    </div>

    <script>
        // ==================== Chat ====================
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

        // ==================== Microphone ====================
        let mediaRecorder;
        let audioChunks = [];
        async function toggleMic() {
            const btn = document.getElementById('micButton');
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                btn.textContent = '🎤';
                btn.style.background = '#3c3c3c';
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    // Request a MIME type that Chrome supports and that our server can handle
                    const mimeType = MediaRecorder.isTypeSupported('audio/webm; codecs=opus') ? 'audio/webm; codecs=opus' : 'audio/webm';
                    mediaRecorder = new MediaRecorder(stream, { mimeType });
                    audioChunks = [];
                    mediaRecorder.addEventListener('dataavailable', e => audioChunks.push(e.data));
                    mediaRecorder.addEventListener('stop', async () => {
                        // Create blob with the actual MIME type used
                        const blob = new Blob(audioChunks, { type: mimeType });
                        const form = new FormData();
                        // Use .webm extension since that's what Chrome produces
                        form.append('audio', blob, 'recording.webm');
                        btn.textContent = '⏳';
                        btn.style.background = '#888';
                        try {
                            const resp = await fetch('/transcribe', { method:'POST', body:form });
                            const data = await resp.json();
                            if (data.text) {
                                document.getElementById('userInput').value = data.text;
                            } else {
                                alert('Transcription failed: ' + (data.error || 'unknown error'));
                            }
                        } catch(e) {
                            alert('Network error: ' + e.message);
                        }
                        btn.textContent = '🎤';
                        btn.style.background = '#3c3c3c';
                    });
                    mediaRecorder.start();
                    btn.textContent = '⏹️';
                    btn.style.background = '#c0a878';
                } catch(e) {
                    alert('Microphone access denied or not available: ' + e.message);
                }
            }
        }

        // ==================== Tabs ====================
        function showTab(name) {
            document.querySelectorAll('.tab-content > div').forEach(el => el.style.display = 'none');
            const target = document.getElementById('tab-' + name);
            if (target) target.style.display = 'block';
            document.querySelectorAll('.tab-buttons .tab').forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('data-tab') === name) btn.classList.add('active');
            });
            if (name === 'persona') { loadPersonaModule(); updateBottomBar('persona'); }
            else if (name === 'trading') { loadTradingModule(); updateBottomBar('trading'); }
            else if (name === 'datalake') { updateBottomBar('datalake'); }
            else updateBottomBar(name);
        }
        function updateBottomBar(tab) {
            const bar = document.getElementById('bottomBar');
            const bars = {
                persona: `<button onclick="saveMemory()">💾 Save Persona</button><button onclick="restoreMemory()">📂 Restore</button><button onclick="resetPersona()">⚠️ Reset</button><button onclick="loadPersonaModule()">↻ Refresh</button>`,
                wellness: '',
                datalake: `<button onclick="searchLake()">🔍 Search Lake</button>`,
                trading: `<button onclick="saveCurrentStrategy()">💾 Save</button><button onclick="reloadCurrentStrategy()">📂 Reload</button><button onclick="resetCurrentStrategy()">⚠️ Reset</button>`,
                email: ''
            };
            bar.innerHTML = bars[tab] || '';
        }

        // ==================== Persona ====================
        async function loadPersonaModule() {
            const resp = await fetchCommand('/persona');
            document.getElementById('personaSummary').textContent = resp || 'No persona.';
        }
        async function submitFeedback() {
            const input = document.getElementById('personaFeedbackInput');
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            await fetchCommand('/mirror ' + text);
            const resp = await fetch('/refine_persona', { method:'POST' });
            const data = await resp.json();
            document.getElementById('personaSummary').textContent = data.reply;
            setTimeout(loadPersonaModule, 2000);
        }
        async function saveMemory() {
            const resp = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:'/memory-save'}) });
            const data = await resp.json();
            alert(data.reply);
        }
        async function restoreMemory() {
            const resp = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:'/memory-restore'}) });
            const data = await resp.json();
            alert(data.reply);
            loadPersonaModule();
        }
        async function resetPersona() {
            if (!confirm('Restore factory persona?')) return;
            const resp = await fetch('/factory_reset', { method:'POST' });
            const data = await resp.json();
            alert(data.reply);
            loadPersonaModule();
        }

        // ==================== Trading ====================
        async function loadTradingModule() {
            loadRecentTrades();
            document.getElementById('stockStrategySummary').textContent = await fetchCommand('/crypto-strat_summary') || 'No stock strategy.';
            document.getElementById('cryptoStrategySummary').textContent = await fetchCommand('/crypto-strat_summary') || 'No crypto strategy.';
        }

        // ==================== Lake ====================
        async function searchLake() {
            const q = document.getElementById('lakeQuery').value.trim();
            if (!q) return;
            document.getElementById('lakeSearchResults').textContent = await fetchCommand('/lake ' + q);
        }

        // ==================== Helpers ====================
        async function fetchCommand(cmd) {
            const resp = await fetch('/command', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:cmd}) });
            const data = await resp.json();
            return data.reply;
        }
        async function sendCommand(cmd) {
            const reply = await fetchCommand(cmd);
            document.getElementById('userInput').value = reply;  // just place in input for now
        }

        window.onload = function() { showTab('persona'); };
    
        // --- Sub-tab switching ---
        let currentSubTab = 'stocks';
        function showSubTab(name) {
            currentSubTab = name;
            document.getElementById('subtrading-stocks').style.display = (name === 'stocks') ? 'block' : 'none';
            document.getElementById('subtrading-crypto').style.display = (name === 'crypto') ? 'block' : 'none';
            document.querySelectorAll('.tab[data-subtab]').forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('data-subtab') === name) btn.classList.add('active');
            });
        }
        // --- Refine with feedback from input ---
        async function refineStocks() {
            const input = document.getElementById('stockFeedbackInput');
            const text = input.value.trim();
            if (!text) { alert('Please enter feedback for the stock strategy.'); return; }
            input.value = '';
            await fetchCommand('/trade-mirror ' + text);
            document.getElementById('stockStrategySummary').textContent = 'Refining...';
            const resp = await fetch('/trading_refine', { method:'POST' });
            const data = await resp.json();
            document.getElementById('stockStrategySummary').textContent = data.reply;
        }
        async function refineCrypto() {
            const input = document.getElementById('cryptoFeedbackInput');
            const text = input.value.trim();
            if (!text) { alert('Please enter feedback for the crypto strategy.'); return; }
            input.value = '';
            await fetchCommand('/crypto-strat ' + text);
            document.getElementById('cryptoStrategySummary').textContent = 'Refining...';
            const resp = await fetch('/crypto_refine', { method:'POST' });
            const data = await resp.json();
            document.getElementById('cryptoStrategySummary').textContent = data.reply;
        }
        // --- Bottom bar helpers (act on current sub-tab) ---
        async function saveCurrentStrategy() {
            const resp = await fetch(currentSubTab === 'stocks' ? '/trading_save' : '/crypto_save', { method:'POST' });
            const data = await resp.json();
            alert(data.reply);
        }
        async function reloadCurrentStrategy() {
            const resp = await fetch(currentSubTab === 'stocks' ? '/trading_reload' : '/crypto_reload', { method:'POST' });
            const data = await resp.json();
            if (currentSubTab === 'stocks') document.getElementById('stockStrategySummary').textContent = data.reply;
            else document.getElementById('cryptoStrategySummary').textContent = data.reply;
        }
        async function resetCurrentStrategy() {
            const type = currentSubTab === 'stocks' ? 'stock' : 'crypto';
            if (!confirm(`Restore factory ${type} strategy?`)) return;
            const resp = await fetch(currentSubTab === 'stocks' ? '/trading_reset' : '/crypto_reset', { method:'POST' });
            const data = await resp.json();
            if (currentSubTab === 'stocks') document.getElementById('stockStrategySummary').textContent = data.reply;
            else document.getElementById('cryptoStrategySummary').textContent = data.reply;
        }
        // --- Load module content ---
        async function loadTradingModule() {
            loadRecentTrades();
            // Stock strategy
            const stockResp = await fetch('/trading_summary');
            document.getElementById('stockStrategySummary').textContent = await stockResp.text() || 'No stock strategy.';
            // Crypto strategy
            const cryptoResp = await fetch('/crypto_summary');
            document.getElementById('cryptoStrategySummary').textContent = await cryptoResp.text() || 'No crypto strategy.';
            // Stock account (Alpaca)
            const stockAcc = await fetch('/account_summary');
            document.getElementById('stockAccountSummary').textContent = await stockAcc.text() || 'Account unavailable.';
            // Crypto account (CoinGecko)
            const cryptoAcc = await fetch('/crypto_account_summary');
            document.getElementById('cryptoAccountSummary').textContent = await cryptoAcc.text() || 'Account unavailable.';
        }
    
        async function logWellness() {
            const input = document.getElementById('wellnessInput');
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            const status = document.getElementById('wellnessStatus');
            status.textContent = 'Logging...';
            const resp = await fetch('/log-wellness', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text}) });
            const data = await resp.json();
            status.textContent = data.reply;
            setTimeout(() => { status.textContent = ''; }, 3000);
        }
    
        async function loadRecentTrades() {
            const resp = await fetch('/recent_trades');
            const text = await resp.text();
            document.getElementById('recentTrades').textContent = text || 'No recent trades.';
        }
    
        async function searchLakeForTrading() {
            const q = document.getElementById('lakeSearchInput').value.trim();
            if (!q) return;
            const resp = await fetch('/command', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:'/lake ' + q}) });
            const data = await resp.json();
            document.getElementById('lakeSearchResults').textContent = data.reply || 'No results found.';
        }
    </script>
</body>
</html>"""

@dashboard_bp.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_HTML)
