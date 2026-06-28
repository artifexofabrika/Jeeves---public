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
async function loadCryptoStrat() {
    const resp = await fetch('/trading_summary');
    const text = await resp.text();
    document.getElementById('cryptoStratSummary').textContent = text || 'No strategy.';
    const fbResp = await fetch('/trading_feedback');
    const fbData = await fbResp.json();
    document.getElementById('cryptoStratFeedback').textContent = fbData.length ? fbData.join('\\n') : 'No feedback yet.';
    document.getElementById('cryptoVaultDisplay').textContent = '';
    document.getElementById('vaultStatus').textContent = 'Trading Mirror active';
}
