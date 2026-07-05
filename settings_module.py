from flask import Blueprint, render_template_string, request, jsonify
import json, os

settings_bp = Blueprint('settings_bp', __name__, template_folder=None)

SETTINGS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeeves – Settings</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #d4d4d4; padding: 1rem; }
        h1 { color: #c0a878; margin-bottom: 1rem; }
        .section { background: #2c2c2c; border: 1px solid #444; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; }
        .section h2 { color: #c0a878; font-size: 1.1rem; margin-bottom: 0.5rem; }
        input { width: 100%; padding: 0.4rem; margin-bottom: 0.4rem; background: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 4px; font-size: 0.85rem; }
        button { padding: 0.4rem 0.8rem; background: #c0a878; border: none; border-radius: 4px; cursor: pointer; color: #1a1a1a; font-weight: bold; font-size: 0.85rem; }
        .status { font-size: 0.85rem; color: #888; margin-left: 0.5rem; }
    </style>
</head>
<body>
    <label style="color:#c0a878; cursor:pointer; display:block; margin-bottom:0.5rem;">
        <input type="checkbox" id="showKeys" onchange="toggleKeys()"> Show Keys
    </label>
    <h1>⚙️ API Key Settings</h1>
    <p><a href="/dashboard" style="color:#c0a878;">← Back to Dashboard</a></p>
    <p>Add your API keys for each service. You may label them however you like.</p>

    <div class="section">
        <h2>📈 Stocks (Broker)</h2>
        <input type="text" id="apiLabel_Stocks" placeholder="Label (e.g., Alpaca Paper)">
        <input type="password" id="apiKey_Stocks" placeholder="API Key">
        <input type="password" id="apiSecret_Stocks" placeholder="API Secret">
        <input type="text" id="apiPassphrase_Stocks" placeholder="Passphrase (optional)">
        <button onclick="saveApiKey('Stocks')">Save Key</button>
        <span class="status" id="apiStatus_Stocks"></span>
    </div>

    <div class="section">
        <h2>🪙 Crypto (Exchange)</h2>
        <input type="text" id="apiLabel_Crypto" placeholder="Label (e.g., Coinbase Live)">
        <input type="password" id="apiKey_Crypto" placeholder="API Key">
        <input type="password" id="apiSecret_Crypto" placeholder="API Secret">
        <input type="text" id="apiPassphrase_Crypto" placeholder="Passphrase (optional)">
        <button onclick="saveApiKey('Crypto')">Save Key</button>
        <span class="status" id="apiStatus_Crypto"></span>
    </div>

    <div class="section">
        <h2>💚 Wellness (Fitness App)</h2>
        <input type="text" id="apiLabel_Wellness" placeholder="Label (e.g., Strava)">
        <input type="password" id="apiKey_Wellness" placeholder="API Key">
        <input type="password" id="apiSecret_Wellness" placeholder="API Secret">
        <input type="text" id="apiPassphrase_Wellness" placeholder="Passphrase (optional)">
        <button onclick="saveApiKey('Wellness')">Save Key</button>
        <span class="status" id="apiStatus_Wellness"></span>
    </div>

    <div class="section">
        <h2>📧 Email (Provider)</h2>
        <input type="text" id="apiLabel_Email" placeholder="Label (e.g., Gmail)">
        <input type="password" id="apiKey_Email" placeholder="API Key / Username">
        <input type="password" id="apiSecret_Email" placeholder="API Secret / Password">
        <input type="text" id="apiPassphrase_Email" placeholder="Passphrase (optional)">
        <button onclick="saveApiKey('Email')">Save Key</button>
        <span class="status" id="apiStatus_Email"></span>
    </div>

    <script>
        async function saveApiKey(module) {
            const label = document.getElementById('apiLabel_' + module).value.trim();
            const key   = document.getElementById('apiKey_'   + module).value.trim();
            const secret = document.getElementById('apiSecret_'+ module).value.trim();
            const pass   = document.getElementById('apiPassphrase_'+module).value.trim();
            if (!label || !key || !secret) { alert('Label, Key, and Secret are required.'); return; }
            const status = document.getElementById('apiStatus_'+module);
            status.textContent = 'Saving…';
            const resp = await fetch('/add_api_key', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({label, key, secret, passphrase:pass, module})
            });
            const data = await resp.json();
            status.textContent = data.message;
            if (data.status === 'ok') {
                document.getElementById('apiLabel_'+module).value = '';
                document.getElementById('apiKey_'+module).value = '';
                document.getElementById('apiSecret_'+module).value = '';
                document.getElementById('apiPassphrase_'+module).value = '';
            }
        }
    
        function toggleKeys() {
            const show = document.getElementById('showKeys').checked;
            const type = show ? 'text' : 'password';
            document.querySelectorAll('input[type="password"], input[type="text"]').forEach(el => {
                if (el.id.startsWith('apiKey_') || el.id.startsWith('apiSecret_') || el.id.startsWith('apiPassphrase_')) {
                    el.type = type;
                }
            });
        }

</script>
</body>
</html>"""

@settings_bp.route('/settings')
def settings():
    return render_template_string(SETTINGS_HTML)
