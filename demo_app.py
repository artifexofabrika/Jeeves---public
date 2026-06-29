import os, datetime, re, json, requests
from flask import Flask, render_template_string, request, jsonify, send_file

app = Flask(__name__)

LLM_URL = "http://localhost:8080/v1/chat/completions"
PERSONA_FILE = os.path.expanduser("~/demo_persona.txt")

def load_persona():
    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE) as f:
            return f.read().strip()
    return "You are Jeeves, a calm, erudite personal valet."

def get_lake_search(query):
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path="/mnt/lake/index")
        collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get('documents', [[]])[0]
        if not docs:
            return "No relevant documents found, sir."
        reply = "🌊 Lake Results:\n"
        for i, doc in enumerate(docs, 1):
            reply += f"{i}. {doc[:300]}...\n\n" if len(doc) > 300 else f"{i}. {doc}\n\n"
        return reply
    except Exception as e:
        return f"Lake search unavailable at the moment: {e}"


def get_lake_context(query, n=3):
    """Return lake snippets as a string, or empty string on failure."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path="/mnt/lake/index")
        collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
        results = collection.query(query_texts=[query], n_results=n)
        docs = results.get('documents', [[]])[0]
        if not docs:
            return ""
        return "\n".join(docs[:n])
    except:
        return ""

def handle_command(user_input):
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return "I beg your pardon?"
    cmd = parts[0].lower()
    if cmd == "/lake":
        if len(parts) > 1:
            return get_lake_search(parts[1])
        return "What shall I search for, sir?"
    if cmd.startswith("/"):
        return "That feature is available in the full Jeeves product. Here you may chat and search the lake. Ask me anything!"
    return None

def ask_llm(question, address="sir"):
    question = "Respond in exactly two or three short sentences. Stay in character as a demo attaché. Do not mention encryption, email, or code. " + question
    persona = load_persona()
    if address:
        persona += f"\nThe user should be addressed as '{address}'."
    try:
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
    except:
        return "I am currently unable to reach my thoughts, sir."

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Demo</title>
    <link rel="icon" type="image/png" href="/favicon.png">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 30%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 40%; display: flex; flex-direction: column; border-bottom: 1px solid #444; }
        .middle-area .tab-buttons { display: flex; flex-wrap: wrap; gap: 0.2rem; padding: 0.3rem 0.6rem; background: #2c2c2c; }
        .middle-area .tab { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.5rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
        .middle-area .tab.active { background: #c0a878; color: #1a1a1a; border-color: #c0a878; }
        .middle-area .tab-content { flex: 1; overflow-y: auto; padding: 0.6rem; }
        .bottom-bar { height: 30%; display: flex; flex-direction: column; background: #1e1e1e; padding: 0.6rem; gap: 0.4rem; }
        .bottom-bar .btn-row { display: flex; flex-wrap: wrap; gap: 0.3rem; }
        .bottom-bar .btn { background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; padding: 0.3rem 0.6rem; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .bottom-bar .btn:hover { background: #4c4c4c; }
        .bottom-bar .status-panel { flex: 1; display: flex; flex-direction: column; gap: 0.3rem; overflow-y: auto; }
        .panel { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 0.6rem; margin-bottom: 0.5rem; white-space: pre-wrap; word-wrap: break-word; font-size: 0.85rem; }
        .message { margin-bottom: 0.4rem; font-size: 0.9rem; }
        .message.user { text-align: right; color: #a0c0ff; }
        .message.jeeves { text-align: left; color: #c0a878; }
        .status { font-size: 0.8rem; color: #888; }
        .demo-badge { display: inline-block; background: #c0a878; color: #1a1a1a; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.7rem; margin-left: 0.4rem; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="chat-messages" id="messages">
            <div class="message jeeves">Good day. I am Jeeves, the demonstration attaché. <span class="demo-badge">DEMO</span></div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Speak to Jeeves..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <div class="middle-area">
        <div class="tab-buttons">
            <button class="tab active" data-tab="mirror" onclick="showTab('mirror')">🪞 Persona Mirror</button>
            <button class="tab" data-tab="cryptostrat" onclick="showTab('cryptostrat')">📈 Trading Strat</button>
            <button class="tab" data-tab="account" onclick="showTab('account')">💼 Account</button>
            <button class="tab" data-tab="email" onclick="showTab('email')">📧 Inbox</button>
            <button class="tab" data-tab="lake" onclick="showTab('lake')">🌊 Lake</button>
        </div>
        <div class="tab-content">
            <div id="tab-mirror" class="panel" style="display: block;">
                <div>🪞 Gentleman's Mirror – Available in the full product. You can refine the AI's persona through feedback loops.</div>
            </div>
            <div id="tab-cryptostrat" class="panel" style="display: none;">
                <div>📈 Trading Strategy – Create and refine strategies with a Mirror‑governed feedback loop. Available in the full product.</div>
            </div>
            <div id="tab-account" class="panel" style="display: none;">
                <div>💼 Portfolio Summary – Display your Alpaca paper account status. Available in the full product.</div>
            </div>
            <div id="tab-email" class="panel" style="display: none;">
                <div>📧 Email Integration – Jeeves can monitor and summarise your inbox. Available in the full product.</div>
            </div>
            <div id="tab-lake" class="panel" style="display: none;">
                <div id="lakeResults">🌊 Knowledge Lake – Type a query in the chat or use the Lake Search button below.</div>
            </div>
        </div>
    </div>

    <div class="bottom-bar">
        <div class="btn-row">
            <button class="btn" onclick="sendCommand('/trade account')">💼 Portfolio</button>
            <button class="btn" onclick="sendCommand('/trade positions')">📊 Positions</button>
            <button class="btn" onclick="sendCommand('/email check')">📧 Inbox</button>
            <button class="btn" onclick="sendCommand('/lake good service')">🌊 Lake Search</button>
            <button class="btn" onclick="sendCommand('/persona')">👤 Persona</button>
        </div>
        <div class="status-panel">
            <div id="cmdOutput" class="status" style="flex:1; overflow-y:auto;"></div>
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
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;
            addMessage('user', text);
            input.value = '';
            if (text.startsWith('/lake')) {
                const resp = await fetch('/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: text }) });
                const data = await resp.json();
                addMessage('jeeves', data.reply);
                document.getElementById('lakeResults').textContent = data.reply;
                showTab('lake');
            } else {
                const resp = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
                const data = await resp.json();
                addMessage('jeeves', data.reply);
            }
        }
        async function sendCommand(cmd) {
            const resp = await fetch('/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: cmd }) });
            const data = await resp.json();
            document.getElementById('cmdOutput').textContent = data.reply;
            if (cmd.startsWith('/lake')) {
                document.getElementById('lakeResults').textContent = data.reply;
                showTab('lake');
            }
        }
        function showTab(tabName) {
            document.querySelectorAll('.tab-content > div').forEach(el => el.style.display = 'none');
            const target = document.getElementById('tab-' + tabName);
            if (target) target.style.display = 'block';
            document.querySelectorAll('.tab-buttons .tab').forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('data-tab') === tabName) btn.classList.add('active');
            });
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_msg = data.get('message', '')
    # Always inject lake context for non‑command messages to ground the response
    if not user_msg.startswith('/'):
        context = get_lake_context(user_msg, n=2)
        if context:
            user_msg = f"Using ONLY the following information from the knowledge lake, answer the user's question. If the information does not contain the answer, say so. Do not invent facts.\n\nLake information:\n{context}\n\nUser question: {user_msg}"
    if user_msg.startswith('/'):
        reply = handle_command(user_msg)
        if reply is None:
            reply = ask_llm(user_msg, address="sir")
    else:
        reply = ask_llm(user_msg, address="sir")
    return jsonify({'reply': reply})

@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    cmd = data.get('command', '')
    reply = handle_command(cmd)
    if reply is None:
        reply = "I am not sure how to handle that command, sir."
    return jsonify({'reply': reply})

@app.route('/favicon.png')
def favicon():
    fav = os.path.expanduser('~/favicon.png')
    if os.path.exists(fav):
        return send_file(fav, mimetype='image/png')
    return '', 204

if __name__ == "__main__":
    print("Demo interface starting on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)