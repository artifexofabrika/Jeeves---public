import os, datetime, json, requests, time
from coinbase.rest import RESTClient
import config
import strategy_parser, trade_logger
import lake_utils

client = RESTClient(
    api_key=config.COINBASE_API_KEY,
    api_secret=config.COINBASE_API_SECRET
)

# MAX_ORDER_VALUE = 10.0
# MAX_DAILY_LOSS  = 5.0
# MAX_TRADES_PER_DAY = 1

STRATEGY_FILE = config.CRYPTO_STRATEGY_FILE
MIRROR_LOG    = os.path.expanduser("~/coinbase_mirror.log")

TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
CHAT_ID            = config.CHAT_ID

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

def get_balances():
    accounts = client.get_accounts()
    balances = {}
    for acct in accounts['accounts']:
        amt = float(acct['available_balance']['value'])
        if amt > 0:
            balances[acct['currency']] = amt
    return balances

def get_price(symbol):
    # Strip any existing "-USD" suffix so we can add it cleanly
    clean = symbol.upper().replace("-USD", "")
    try:
        product = client.get_product(clean + "-USDT")
        return float(product['price'])
    except:
        return None


def get_base_precision(symbol):
    """Return the allowed decimal precision for a given symbol."""
    precisions = {
        "BTC": 8,
        "ETH": 8,
        "SOL": 4,
        "USDT": 2,
        "PEPE": 0,   # PEPE is whole units
    }
    return precisions.get(symbol.upper(), 2)

def round_qty(symbol, qty):
    """Round quantity to the exchange-allowed precision."""
    decimals = get_base_precision(symbol)
    return round(qty, decimals)

def place_market_order(symbol, qty, side):
    """Place a live market order. Returns (order_id, error_message)."""
    try:
        clean_sym = symbol.upper().replace("-USD", "")
        order = client.market_order(
            client_order_id=f"jeeves_{int(time.time())}",
            product_id=clean_sym + "-USDT",
            side=side.upper(),
            base_size=str(round_qty(symbol, qty))
        )
        # The response is a CreateOrderResponse object; convert to dict
        order_dict = order.__dict__ if hasattr(order, '__dict__') else {}
        success = order_dict.get('success', False)
        if success:
            resp = order_dict.get('success_response', {})
            order_id = resp.get('order_id', 'unknown')
            log("Live order placed successfully. Order ID: " + str(order_id))
            return order_id, None
        else:
            err = order_dict.get('error_response', {})
            msg = err.get('error', 'unknown') + ': ' + err.get('message', '')
            log("Order failed: " + msg)
            return None, msg
    except Exception as e:
        log("Order error: " + str(e))
        return None, str(e)



def get_market_trends(symbols, days=7):
    trends = ""
    for sym in symbols:
        try:
            coin_id_map = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana",
                "USDT": "tether",
                "PEPE": "pepe"
            }
            coin_id = coin_id_map.get(sym, sym.lower())
            url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
            params = {"vs_currency": "usd", "days": days}
            resp = requests.get(url, params=params, timeout=15)
            if resp.ok:
                prices = resp.json()["prices"]
                if len(prices) >= 2:
                    start_price = prices[0][1]
                    end_price   = prices[-1][1]
                    pct_change = ((end_price - start_price) / start_price) * 100
                    sma = sum(p[1] for p in prices[-7:]) / min(7, len(prices))
                    above_sma = "above" if end_price > sma else "below"
                    trend_line = sym + "-USD: $" + str(round(end_price,2)) + " (" + str(round(pct_change,1)) + "% over " + str(days) + "d, " + above_sma + " 7-day SMA)"
                    trends += trend_line + "\n"
                else:
                    trends += sym + "-USD: insufficient data\n"
            else:
                trends += sym + "-USD: data unavailable\n"
        except Exception as e:
            trends += sym + "-USD: error (" + str(e) + ")\n"
    return trends

def main():
    # Check halt signal
    halt_file = os.path.expanduser("~/coinbase_halt.signal")
    if os.path.exists(halt_file):
        os.remove(halt_file)
        log("Halt signal received. Exiting.")
        send_telegram("🛑 Advisor halted by user command.")
        return

    # Lock file to prevent concurrent runs
    lock_path = os.path.expanduser("~/coinbase_advisor.lock")
    import fcntl
    with open(lock_path, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Another advisor instance is already running. Exiting.")
            return
    log("=== Coinbase Live Advisor Run ===")

    if not os.path.exists(STRATEGY_FILE):
        log("Error: Strategy file not found.")
        return
    with open(STRATEGY_FILE, 'r') as f:
        strategy = f.read()

    balances = get_balances()
    log("Balances: " + str(balances))

    # Fetch live market trends
    symbols = [c for c in balances.keys() if c != 'USD']
    market_trends = get_market_trends(symbols, days=7)
    log("Market trends:\n" + market_trends)

    data_summary = "Market Trends (7 days):\n" + market_trends + "\n"
    for currency, amount in balances.items():
        if currency == 'USD':
            data_summary += "Cash: $" + str(round(amount,2)) + "\n"
        else:
            price = get_price(currency)
            if price:
                data_summary += currency + ": " + str(amount) + " (value $" + str(round(amount*price,2)) + ")\n"

    prompt = 'You are a disciplined crypto trader. Analyze the current portfolio and strategy, and recommend a trade in JSON format.\n\n'
    prompt += 'Strategy:\n' + strategy + '\n\n'
    prompt += 'Current state:\n' + data_summary + '\n'
    prompt += 'Respond with a SINGLE JSON object, never multiple. The object must follow this exact format:\n'
    prompt += '{"action": "buy" or "sell" or "hold", "symbol": "SYMBOL-USDT", "quantity": float, "rationale": "brief explanation"}\n\n'
    prompt += 'Recommend exactly ONE trade. Output only one JSON object on a single line. If no trade, set action to "hold" and quantity to 0. Ensure the quantity you choose, when multiplied by the current market price, results in a total value of $' + str(MAX_ORDER_VALUE) + ' or less. Do not propose any trade that would exceed this cap.'

    llm_url = config.LLM_URL
    try:
        resp = requests.post(llm_url, json={
            "model": "llama",
            "messages": [{"role":"user","content":prompt}],
            "temperature":0.2, "max_tokens":200
        }, timeout=60)
        if resp.ok:
            reply = resp.json()["choices"][0]["message"]["content"]
            log("LLM raw: " + reply)
            try:
                # Extract the first JSON object (in case the LLM returns multiple)
                json_start = reply.find('{')
                json_end   = reply.find('}', json_start) + 1
                if json_start >= 0 and json_end > json_start:
                    rec = json.loads(reply[json_start:json_end])
                    action    = rec.get("action", "hold")
                    symbol    = rec.get("symbol", "").upper()
                    qty       = float(rec.get("quantity", 0))
                    rationale = rec.get("rationale", "")

                    if action in ("buy", "sell") and qty > 0:
                        price = get_price(symbol)
                        if price is None:
                            log("Cannot fetch price.")
                            return
                        order_value = qty * price
                        if order_value > MAX_ORDER_VALUE:
                            log("Order value $" + str(round(order_value,2)) + " exceeds limit. Skipping.")
                            return
                        if order_value < 1.0:
                            log("Order value $" + str(round(order_value,2)) + " below minimum $1. Skipping.")
                            return
                        if qty < 0.0001 and symbol.upper() != "PEPE-USD":
                            log("Quantity too small for " + symbol + ". Skipping.")
                            return

                        # Autonomous execution – notify and execute immediately
                        info_msg = "Coinbase Advisor executing:\n\n" + action.upper() + " " + str(qty) + " " + symbol + "-USD\nValue: $" + str(round(order_value,2)) + "\nRationale: " + rationale
                        send_telegram(info_msg)

                        log("Autonomous mode – executing immediately.")
                        order_id, error_msg = place_market_order(symbol, qty, action)
                        if order_id:
                            # Log trade to history and lake
                            trade_record = {
                                "trade_id": str(order_id),
                                "timestamp": datetime.datetime.now().isoformat(),
                                "pair": symbol + "-USDT",
                                "side": action,
                                "quantity": str(qty),
                                "price": str(round(order_value / qty, 2)) if qty else "0",
                                "total": str(round(order_value, 2)),
                                "status": "filled",
                                "metadata": {"rationale": rationale}
                            }
                            trade_logger.log_trade(trade_record)
                            lake_utils.ingest_trade(trade_record)

                            send_telegram("Trade executed: " + action.upper() + " " + str(qty) + " " + symbol + "-USD. Order ID: " + str(order_id))
                        else:
                            send_telegram("Trade failed: " + str(error_msg))
                    else:
                        log("Recommendation: HOLD - " + rationale)
            except (json.JSONDecodeError, ValueError) as e:
                log("JSON parse error: " + str(e))
        else:
            log("LLM request failed: " + str(resp.status_code))
    except Exception as e:
        log("Advisor error: " + str(e))

if __name__ == "__main__":
    # Read trading limits from strategy file
    limits = strategy_parser.parse_limits()
    MAX_ORDER_USD = limits["MAX_ORDER_USD"]
    DAILY_TRADE_LIMIT = limits["DAILY_TRADE_LIMIT"]
    print(f"Limits loaded: max_order=${MAX_ORDER_USD}, daily_limit={DAILY_TRADE_LIMIT} trades")
    # Assign parsed limits to the variable names used throughout the script
    global MAX_ORDER_VALUE, MAX_DAILY_LOSS, MAX_TRADES_PER_DAY
    MAX_ORDER_VALUE = limits["MAX_ORDER_USD"]
    MAX_DAILY_LOSS = limits["MAX_DAILY_LOSS"]
    MAX_TRADES_PER_DAY = limits["DAILY_TRADE_LIMIT"]


    main()
