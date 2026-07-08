#!/usr/bin/env python3
"""
live_trading_advisor.py – Exchange‑agnostic autonomous trading advisor.
Reads EXCHANGE and trading limits from the crypto strategy file.
Uses the broker interface for all price/order operations.
All exchange‑specific logic lives in adapters/.
"""
import os, datetime, json, time, sys, requests
import config
import strategy_parser, trade_logger, lake_utils
import broker

STRATEGY_FILE = os.path.expanduser("~/crypto_sim_strategy.txt")
LOG_FILE      = os.path.expanduser("~/coinbase_mirror.log")
LOCK_FILE     = os.path.expanduser("~/coinbase_advisor.lock")

TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
CHAT_ID            = config.CHAT_ID

def log(msg):
    ts = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} | {msg}\n")
    print(msg)

def send_telegram(text):
    if TELEGRAM_BOT_TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text},
                timeout=10
            )
        except Exception:
            pass

def main():
    import fcntl
    try:
        lf = open(LOCK_FILE, "w")
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Another advisor instance is already running. Exiting.")
        return

    log("=== Live Trading Advisor Run ===")

    limits = strategy_parser.parse_limits(STRATEGY_FILE)
    MAX_ORDER_USD   = limits["MAX_ORDER_USD"]
    DAILY_TRADE_LIM = limits["DAILY_TRADE_LIMIT"]

    if trade_logger.trades_today(market="crypto") >= DAILY_TRADE_LIM:
        log(f"Daily trade limit reached ({DAILY_TRADE_LIM}). Exiting.")
        return

    try:
        balances = broker.get_balances()
    except Exception as e:
        log(f"Failed to fetch balances: {e}")
        return
    log(f"Balances: {balances}")

    trends = []
    for cur, amt in balances.items():
        if cur == "USD":
            continue
        try:
            price = broker.get_price(cur)
        except Exception:
            continue
        if price is None:
            continue
        trends.append(f"{cur}-USD: ${price:.2f} (amount: {amt})")
    if not trends:
        log("No supported assets with valid prices.")
        return
    log(f"Market trends:\n" + "\n".join(trends))

    data_summary = "Balances:\n" + "\n".join(
        f"{c}: {a}" for c, a in balances.items()
    ) + "\n\nMarket Prices (USD):\n" + "\n".join(trends)

    with open(STRATEGY_FILE, "r") as f:
        strategy_text = f.read()

    prompt = (
        f"{strategy_text}\n\n"
        f"Current portfolio state:\n{data_summary}\n\n"
        "You are a disciplined trading algorithm. Recommend exactly ONE trade.\n"
        "Output ONLY a valid JSON object on a single line with no line breaks.\n"
        'Keys: "action" ("buy"/"sell"/"hold"), "symbol" (e.g. "ETH-USDT"), '
        '"quantity" (float), "rationale" (string).\n'
        f"Total order value (quantity × price) MUST NOT exceed ${MAX_ORDER_USD}.\n"
        "If no trade fits, set action to \"hold\" and quantity to 0.\n"
        "Ensure the JSON has a closing brace."
    )

    try:
        resp = requests.post(
            config.LLM_URL,
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 0.3,
                "stop": ["\n\n"]
            },
            timeout=120
        )
        if resp.status_code != 200:
            log(f"LLM request failed: {resp.status_code}")
            return
        reply = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM request error: {e}")
        return
    log(f"LLM raw: {reply}")

    try:
        start = reply.find("{")
        end   = reply.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        rec = json.loads(reply[start:end])
        action    = rec.get("action", "hold").lower()
        symbol    = rec.get("symbol", "").upper()
        qty       = float(rec.get("quantity", 0))
        rationale = rec.get("rationale", "")
    except Exception as e:
        log(f"JSON parse error: {e}")
        return

    if action not in ("buy", "sell") or qty <= 0:
        log(f"Recommendation: HOLD - {rationale}")
        return

    try:
        price = broker.get_price(symbol)
    except Exception as e:
        log(f"Cannot fetch price for {symbol}: {e}")
        return
    if price is None:
        log(f"Cannot fetch price for {symbol}.")
        return

    order_value = qty * price
    if order_value > MAX_ORDER_USD:
        log(f"Order value ${order_value:.2f} exceeds limit ${MAX_ORDER_USD:.2f}. Skipping.")
        return

    info_msg = (
        f"Live Advisor executing:\n"
        f"{action.upper()} {qty} {symbol} ~ ${order_value:.2f}\n"
        f"Rationale: {rationale}"
    )
    send_telegram(info_msg)
    log("Autonomous mode – executing immediately.")

    order_id, error_msg = broker.place_order(symbol, qty, action)
    if order_id:
        log(f"Order executed: {order_id}")
        send_telegram(f"Trade executed: {action.upper()} {qty} {symbol}. Order ID: {order_id}")

        trade_record = {
            "trade_id": str(order_id),
            "timestamp": datetime.datetime.now().isoformat(),
            "pair": symbol,
            "side": action,
            "quantity": str(qty),
            "price": str(round(price, 2)),
            "total": str(round(order_value, 2)),
            "status": "filled",
            "market": "crypto",
            "metadata": {"rationale": rationale}
        }
        trade_logger.log_trade(trade_record)
        lake_utils.ingest_trade(trade_record)
    else:
        log(f"Order failed: {error_msg}")
        send_telegram(f"Trade failed: {error_msg}")

if __name__ == "__main__":
    main()
