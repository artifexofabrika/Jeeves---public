from flask import Blueprint, render_template_string, request, jsonify
import os, requests, datetime
import config

persona_bp = Blueprint('persona_bp', __name__, template_folder=None)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Persona</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .top-bar { height: 50%; display: flex; flex-direction: column; border-bottom: 1px solid #444; background: #1e1e1e; }
        .top-bar .chat-messages { flex: 1; overflow-y: auto; padding: 0.6rem; font-size: 0.9rem; }
        .top-bar .chat-input { display: flex; padding: 0.4rem; background: #2c2c2c; }
        .top-bar .chat-input input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .top-bar .chat-input button { padding: 0.4rem 0.8rem; margin-left: 0.4rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .middle-area { height: 40%; display: flex; flex-direction: column; padding: 0.6rem; background: #1e1e1e; }
        .middle-area h2 { font-size: 1.1rem; color: #c0a878; margin-bottom: 0.5rem; }
        .persona-box { background: #2c2c2c; padding: 0.6rem; border-radius: 4px; flex: 1; overflow-y: auto; white-space: pre-wrap; font-size: 0.9rem; margin-bottom: 0.5rem; }
        .feedback-row { display: flex; gap: 0.4rem; }
        .feedback-row input { flex: 1; padding: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        .feedback-row button { padding: 0.4rem 0.8rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .bottom-bar { height: 10%; display: flex; align-items: center; gap: 0.4rem; padding: 0 0.6rem; background: #2c2c2c; }
        .bottom-bar button { padding: 0.35rem 0.7rem; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 3px; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
        .bottom-bar button:hover { background: #4c4c4c; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="chat-messages" id="messages">
            <div class="message" style="color:#c0a878;">Good day, sir. The persona module is ready.</div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Speak to your valet..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <div class="middle-area">
        <h2>Current Persona</h2>
        <div class="persona-box" id="personaText">Loading...</div>
        <div class="feedback-row">
            <input type="text" id="feedbackInput" placeholder="Add feedback for the Mirror...">
            <button onclick="submitFeedback()">✨ Refine</button>
        </div>
    </div>
    <div class="bottom-bar">
        <button onclick="saveMemory()">🧠 Save Memory</button>
        <button onclick="restoreMemory()">📂 Restore Persona</button>
        <button onclick="resetPersona()">⚠️ Reset Persona</button>
        <button onclick="loadPersona()">↻ Refresh</button>
    </div>
    <script>
        async function fetchCommand(cmd) {
            const resp = await fetch('/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: cmd }) });
            const data = await resp.json();
            return data.reply;
        }
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
        async function loadPersona() {
            document.getElementById('personaText').textContent = await fetchCommand('/persona') || 'No persona.';
        }
        async function submitFeedback() {
            const input = document.getElementById('feedbackInput');
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            await fetchCommand('/mirror ' + text);
            const resp = await fetch('/refine_persona', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('personaText').textContent = data.reply;
            setTimeout(loadPersona, 2000);
        }
        async function saveMemory() {
            const resp = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: '/memory-save' }) });
            const data = await resp.json();
            alert(data.reply);
        }
        async function restoreMemory() {
            const resp = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: '/memory-restore' }) });
            const data = await resp.json();
            alert(data.reply);
            loadPersona();
        }
        async function resetPersona() {
            if (!confirm('Restore the factory default persona?')) return;
            const resp = await fetch('/factory_reset', { method: 'POST' });
            const data = await resp.json();
            alert(data.reply);
            loadPersona();
        }
        window.onload = loadPersona;
    </script>
</body>
</html>"""

@persona_bp.route('/persona')
def persona():
    return render_template_string(HTML)
