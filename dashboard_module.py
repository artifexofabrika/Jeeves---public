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
        whisper_model = whisper.load_model("base.en")
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
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Dashboard</title>
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
                <div style="text-align:center;padding:2rem;color:#888;">
                    <div style="font-size:2rem;">💚</div>
                    <div>Wellness tracking is under development.</div>
                </div>
            </div>
            <div id="tab-datalake" class="panel" style="display:none;">
                <div style="margin-bottom:1rem;">
                    <div style="font-size:1.1rem;color:#c0a878;">Lake Search</div>
                    <input type="text" id="lakeQuery" placeholder="Search your knowledge lake..." style="width:100%;padding:0.5rem;background:#2c2c2c;border:1px solid #555;color:#fff;border-radius:4px;margin-bottom:0.4rem;" onkeypress="if(event.key==='Enter') searchLake()">
                    <button onclick="searchLake()" style="padding:0.35rem 0.7rem;background:#c0a878;border:none;border-radius:3px;color:#1a1a1a;font-weight:bold;">🔍 Search</button>
                </div>
                <div id="lakeSearchResults" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;min-height:3rem;">Results will appear here.</div>
            </div>
            <div id="tab-trading" class="panel" style="display:none;">
                <div style="margin-bottom:1rem;">
                    <div style="font-size:1.1rem;color:#c0a878;">Stock Strategy</div>
                    <div id="stockStrategySummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;">Loading...</div>
                </div>
                <div style="margin-bottom:1rem;">
                    <div style="font-size:1.1rem;color:#c0a878;">Crypto Strategy</div>
                    <div id="cryptoStrategySummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;">Loading...</div>
                </div>
                <div style="margin-bottom:1rem;">
                    <div style="font-size:1.1rem;color:#c0a878;">Account</div>
                    <div id="accountSummary" style="background:#1e1e1e;padding:0.6rem;border-radius:4px;">Loading...</div>
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
                trading: `<button onclick="sendCommand('/trade account')">💼 Portfolio</button><button onclick="sendCommand('/trade positions')">📊 Positions</button><button onclick="sendCommand('/crypto-sim account')">🪙 Crypto</button>`,
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
            document.getElementById('stockStrategySummary').textContent = await fetchCommand('/crypto-strat_summary') || 'No stock strategy.';
            document.getElementById('cryptoStrategySummary').textContent = await fetchCommand('/crypto-strat_summary') || 'No crypto strategy.';
            document.getElementById('accountSummary').textContent = await fetchCommand('/trade account') || 'Account unavailable.';
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
    </script>
</body>
</html>"""

@dashboard_bp.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_HTML)
