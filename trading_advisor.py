import requests, json, os, datetime, time, sys, re
import config
import mirror_engine

LLM_URL = config.LLM_URL
ALPACA_BASE = "https://paper-api.alpaca.markets"
API_KEY = config.ALPACA_API_KEY
SECRET_KEY = config.ALPACA_SECRET_KEY
STRATEGY_FILE = config.TRADING_STRATEGY_FILE
MIRROR_LOG = config.TRADING_MIRROR_LOG
MAX_DAILY_TRADES = 5           # total trades per day
MAX_ORDER_VALUE = 10000        # dollars per order (increased from original 5000)
MAX_DAILY_LOSS = 0.05          # 5% of equity max loss per day
KILL_SWITCH_FILE = os.path.expanduser("~/trading_kill_switch")
TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
CHAT_ID = config.CHAT_ID

if not API_KEY or not SECRET_KEY:
    print("Warning: Alpaca keys not set. Trading functions will fail.")

def alpaca_headers():
    return {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": SECRET_KEY,
        "Content-Type": "application/json"
    }

def get_account():
    resp = requests.get(f"{ALPACA_BASE}/v2/account", headers=alpaca_headers())
    return resp.json() if resp.ok else {}

def get_positions():
    resp = requests.get(f"{ALPACA_BASE}/v2/positions", headers=alpaca_headers())
    return resp.json() if resp.ok else []

def get_bars(symbol, days=5):
    end = datetime.datetime.now().isoformat() + "Z"
    start = (datetime.datetime.now() - datetime.timedelta(days=days+1)).isoformat() + "Z"
    resp = requests.get(
        f"{ALPACA_BASE}/v2/stocks/{symbol}/bars",
        headers=alpaca_headers(),
        params={"timeframe": "1D", "start": start, "end": end, "limit": days+1}
    )
    return resp.json().get("bars", []) if resp.ok else []

def get_market_price(symbol):
    bars = get_bars(symbol, days=1)
    if bars:
        return bars[-1]['c']
    return None

def place_order(symbol, qty, side):
    data = {"symbol": symbol, "qty": qty, "side": side, "type": "market", "time_in_force": "day"}
    resp = requests.post(f"{ALPACA_BASE}/v2/orders", json=data, headers=alpaca_headers())
    return resp.json() if resp.ok else {"error": resp.text}

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

def check_kill_switch():
    if os.path.exists(KILL_SWITCH_FILE):
        log("Kill switch active. Trading halted.")
        send_telegram("Trading advisor halted by kill switch.")
        sys.exit(0)

def daily_loss_exceeded():
    """Check if today's realized losses exceed MAX_DAILY_LOSS of portfolio."""
    today = datetime.date.today().isoformat()
    # Simple approximation: sum of negative P/L from filled orders today
    # Since Alpaca paper account doesn't provide intraday P/L easily, we'll rely on the account equity change.
    # For a full implementation, we'd compare current equity to start-of-day equity stored in a file.
    # For now, we'll skip and just rely on position-level risk checks.
    return False  # placeholder

def main():
    check_kill_switch()
    log("=== Trading Advisor Run ===")

    if not os.path.exists(STRATEGY_FILE):
        log("Error: Strategy file not found.")
        return
    with open(STRATEGY_FILE, 'r') as f:
        strategy = f.read()

    account = get_account()
    positions = get_positions()
    cash = float(account.get("cash", 0))
    portfolio_value = float(account.get("portfolio_value", 0))

    # Check daily loss limit (stubbed; implement later with a persistent daily equity tracker)
    # if daily_loss_exceeded():
    #     log("Daily loss limit reached. Trading halted.")
    #     send_telegram("Trading halted: daily loss limit reached.")
    #     return

    data_summary = f"Cash: ${cash:.2f}\nPortfolio value: ${portfolio_value:.2f}\n\n"
    if positions:
        data_summary += "Current positions:\n"
        for pos in positions:
            data_summary += f"- {pos['symbol']}: {pos['qty']} shares, avg entry ${pos['avg_entry_price']}, "
            data_summary += f"current price ${pos['current_price']}, P/L ${pos['unrealized_pl']}\n"
    else:
        data_summary += "No current positions.\n"

    watchlist = list(set(re.findall(r'\b[A-Z]{1,5}\b', strategy)))
    skip_words = {"I", "ETF", "SMA", "LLM", "API", "JSON", "P/L", "ID", "URL"}
    watchlist = [w for w in watchlist if w not in skip_words]

    if watchlist:
        data_summary += "\nRecent price action:\n"
        for sym in watchlist[:5]:
            bars = get_bars(sym, days=5)
            if bars:
                closes = [b['c'] for b in bars[-5:]]
                data_summary += f"{sym}: last 5 closes: {closes}\n"

    # --- Lake context injection (placeholder) ---
    lake_context = ""
    # When lake is ready, search for relevant notes:
    # for sym in watchlist[:3]:
    #    try:
    #        results = query_lake(f"{sym} outlook")
    #        if results:
    #            lake_context += f"Notes on {sym}: {'; '.join(results)}\n"
    #    except:
    #        pass

    prompt = f"""You are a disciplined trading advisor. Analyze the following data against the user's strategy and recommend a trade in JSON format.

Strategy:
{strategy}

Current state:
{data_summary}

Lake notes:
{lake_context}

Respond ONLY with a SINGLE JSON object, never multiple. The object must follow this format:
{{"action": "buy" or "sell" or "hold", "symbol": "TICKER", "quantity": integer, "rationale": "brief explanation"}}

If no trade, set action to "hold" and quantity to 0."""

    try:
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 200
        }, timeout=60)
        if resp.ok:
            reply = resp.json()["choices"][0]["message"]["content"]
            log(f"LLM raw response: {reply}")
            try:
                json_start = reply.find('{')
                json_end = reply.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = reply[json_start:json_end]
                    rec = json.loads(json_str)
                    action = rec.get("action", "hold")
                    symbol = rec.get("symbol", "").upper()
                    qty = int(rec.get("quantity", 0))
                    rationale = rec.get("rationale", "")

                    if action in ("buy", "sell") and qty > 0:
                        today = datetime.date.today().isoformat()
                        # Count today's trades
                        with open(MIRROR_LOG, 'r') as f:
                            daily_trades = sum(1 for line in f if today in line and "Order executed" in line)
                        if daily_trades >= MAX_DAILY_TRADES:
                            log(f"Daily trade limit reached. Skipping {action} {symbol}.")
                            return
                        price = get_market_price(symbol)
                        if price is None:
                            log("Cannot fetch price.")
                            return
                        if price * qty > MAX_ORDER_VALUE:
                            log(f"Order value exceeds limit. Skipping.")
                            return
                        # Place the order
                        order = place_order(symbol, qty, action)
                        if "id" in order:
                            log(f"Order executed: {action} {qty} {symbol} - {rationale}")
                            send_telegram(f"Trading Advisor: {action.upper()} {qty} {symbol}. {rationale}")
                        else:
                            log(f"Order failed: {order}")
                    else:
                        log(f"Recommendation: HOLD - {rationale}")
                else:
                    log("Could not parse JSON.")
            except (json.JSONDecodeError, ValueError) as e:
                log(f"JSON parse error: {e}")
        else:
            log(f"LLM request failed: {resp.status_code}")
    except Exception as e:
        log(f"Advisor error: {e}")

if __name__ == "__main__":
    main()
