import requests, json, os, datetime, time, sys, re
import crypto_sim
import config

VAULT_PATH = os.path.expanduser('~/crypto_sim_vault.json')

def load_vault():
    if os.path.exists(VAULT_PATH):
        with open(VAULT_PATH, 'r') as f:
            return json.load(f)
    return {"core_capital": 100.0, "secured_vault": 0.0}

def save_vault(vault):
    with open(VAULT_PATH, 'w') as f:
        json.dump(vault, f)

LLM_URL = config.LLM_URL
STRATEGY_FILE = config.CRYPTO_STRATEGY_FILE
MIRROR_LOG = config.CRYPTO_MIRROR_LOG
MAX_DAILY_TRADES = 5
MAX_OPEN_POSITIONS = 3
MAX_RISK_PER_TRADE = 0.02  # 2% of simulated equity
TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
CHAT_ID = config.CHAT_ID

def log(message):
    timestamp = datetime.datetime.now().isoformat()
    with open(MIRROR_LOG, "a") as f:
        f.write(f"{timestamp} | {message}\n")
    print(message)

def send_telegram(message):
    if TELEGRAM_BOT_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": CHAT_ID, "text": message})
        except:
            pass

def main():
    log("=== Crypto-Sim Advisor Run ===")

    if not os.path.exists(STRATEGY_FILE):
        log("Error: Crypto strategy file not found. Please create ~/crypto_sim_strategy.txt")
        return
    with open(STRATEGY_FILE, 'r') as f:
        strategy = f.read()

    account_info = crypto_sim.get_account()
    positions_info = crypto_sim.get_positions()
    # Parse equity from account string (simple extraction)
    equity_match = re.search(r'Equity: \$(\d+\.\d+)', account_info)
    equity = float(equity_match.group(1)) if equity_match else 100.0
    cash_match = re.search(r'Cash: \$(\d+\.\d+)', account_info)
    cash = float(cash_match.group(1)) if cash_match else 100.0

    # Load vault and apply ratchet
    vault = load_vault()
    core_capital = vault['core_capital']
    secured_vault = vault['secured_vault']
    if equity >= core_capital * 1.5:
        gain = equity - core_capital
        new_core = core_capital + gain * 0.5
        new_secured = secured_vault + gain * 0.5
        vault = {"core_capital": new_core, "secured_vault": new_secured}
        save_vault(vault)
        log(f"Ratchet triggered: core capital increased to ${new_core:.2f}, secured vault now ${new_secured:.2f}")
        core_capital = new_core
        secured_vault = new_secured

    data_summary = f"Cash: ${cash:.2f}\nEquity: ${equity:.2f}\n\n"
    data_summary += positions_info

    prompt = f"""You are a disciplined crypto trading advisor. Analyze the following data against the user's strategy and recommend a trade in JSON format.

Strategy:
{strategy}

Current state:
{data_summary}

Respond ONLY with a JSON object in this exact format:
{{"action": "buy" or "sell" or "hold", "symbol": "SYMBOL/USD", "quantity": float, "rationale": "brief explanation"}}

If no trade, set action to "hold" and quantity to 0."""

    try:
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 200
        }, timeout=90)
        if resp.ok:
            reply = resp.json()["choices"][0]["message"]["content"]
            log(f"LLM raw: {reply}")
            try:
                json_start = reply.find('{')
                json_end = reply.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = reply[json_start:json_end]
                    rec = json.loads(json_str)
                    action = rec.get("action", "hold")
                    symbol = rec.get("symbol", "").upper()
                    qty = float(rec.get("quantity", 0))
                    rationale = rec.get("rationale", "")

                    if action in ("buy", "sell") and qty > 0:
                        # Risk checks
                        today = datetime.date.today().isoformat()
                        with open(MIRROR_LOG, 'r') as f:
                            daily_trades = sum(1 for line in f if today in line and "Simulated order filled" in line)
                        if daily_trades >= MAX_DAILY_TRADES:
                            log("Daily trade limit reached.")
                            return
                        # Count current positions
                        data = crypto_sim._load()
                        if len(data['holdings']) >= MAX_OPEN_POSITIONS and action == "buy":
                            log("Max open positions reached.")
                            return
                        # Check risk amount
                        risk_amount = equity * MAX_RISK_PER_TRADE
                        price = 0
                        try:
                            from pycoingecko import CoinGeckoAPI
                            cg = CoinGeckoAPI()
                            coin_id = {"BTC/USD":"bitcoin","ETH/USD":"ethereum","USDT/USD":"tether","LTC/USD":"litecoin","XRP/USD":"ripple"}.get(symbol)
                            if coin_id:
                                price = cg.get_price(ids=coin_id, vs_currencies='usd')[coin_id]['usd']
                        except:
                            pass
                        if price > 0:
                            max_qty = risk_amount / price
                            if qty > max_qty:
                                log(f"Reducing quantity from {qty} to {max_qty:.4f} due to risk limits.")
                                qty = max_qty

                        # Execute simulated order
                        result = crypto_sim.place_order(symbol, qty, action)
                        log(f"Order result: {result}")
                        send_telegram(f"Crypto-Sim Advisor: {action.upper()} {qty} {symbol}. {rationale}")
                    else:
                        log(f"Recommendation: HOLD - {rationale}")
                else:
                    log("Could not parse JSON.")
            except (json.JSONDecodeError, ValueError) as e:
                log(f"JSON parse error: {e}")
        else:
            log(f"LLM request failed: {resp.status_code}")
    except Exception as e:
        log(f"Crypto-Sim advisor error: {e}")

if __name__ == "__main__":
    main()
