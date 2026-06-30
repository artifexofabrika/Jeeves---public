from flask import Blueprint, render_template_string

wellness_bp = Blueprint('wellness_bp', __name__, template_folder=None)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Wellness</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 50%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 40%; display: flex; align-items: center; justify-content: center; background: #1e1e1e; padding: 1rem; }
        .placeholder { text-align: center; color: #888; }
        .placeholder .icon { font-size: 3rem; margin-bottom: 0.5rem; }
        .placeholder h2 { font-size: 1.3rem; color: #c0a878; margin-bottom: 0.5rem; }
        .placeholder p { font-size: 0.9rem; line-height: 1.5; max-width: 400px; }
        .bottom-bar { height: 10%; display: flex; align-items: center; gap: 0.4rem; padding: 0 0.6rem; background: #2c2c2c; }
        .bottom-bar button { padding: 0.35rem 0.7rem; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .bottom-bar button:hover { background: #4c4c4c; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="chat-messages" id="messages">
            <div class="message" style="color:#c0a878;">Good day, sir. The wellness module is under development.</div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Speak to your valet..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <div class="middle-area">
        <div class="placeholder">
            <div class="icon">💚</div>
            <h2>Wellness Tracking</h2>
            <p>Health metrics, medication reminders, and personal journaling will appear here. This module is under active development.</p>
        </div>
    </div>
    <div class="bottom-bar">
        <button disabled>📝 Log Entry (soon)</button>
        <button disabled>📊 View History (soon)</button>
        <button disabled>⏰ Set Reminder (soon)</button>
    </div>
    <script>
        function addMessage(sender, text) {
            const msgDiv = document.createElement('div');
            msgDiv.style.marginBottom = '0.4rem';
            msgDiv.style.color = sender === 'user' ? '#a0c0ff' : '#c0a878';
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
        }
    </script>
</body>
</html>"""

@wellness_bp.route('/wellness')
def wellness():
    return render_template_string(HTML)
