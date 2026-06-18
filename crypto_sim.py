import json, os, datetime
from pycoingecko import CoinGeckoAPI

PORTFOLIO_FILE = os.path.expanduser("~/crypto_sim_portfolio.json")

# Initialize if not present
if not os.path.exists(PORTFOLIO_FILE):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump({
            "cash": 100.0,
            "holdings": {},
            "trades": []
        }, f, indent=2)

def _load():
    with open(PORTFOLIO_FILE, 'r') as f:
        return json.load(f)

def _save(data):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_account():
    data = _load()
    cash = data['cash']
    holdings = data['holdings']
    equity = cash
    cg = CoinGeckoAPI()
    for coin, qty in holdings.items():
        try:
            price = cg.get_price(ids=coin, vs_currencies='usd')[coin]['usd']
        except:
            price = 0
        equity += qty * price
    trade_count = len(data['trades'])
    return (f"Simulated Crypto Account:\n"
            f"Cash: ${cash:.2f}\n"
            f"Equity: ${equity:.2f}\n"
            f"Total Trades: {trade_count}")

def get_positions():
    data = _load()
    holdings = data['holdings']
    if not holdings:
        return "No open crypto positions, sir."
    cg = CoinGeckoAPI()
    summary = "Crypto Positions:\n"
    for coin, qty in holdings.items():
        try:
            price = cg.get_price(ids=coin, vs_currencies='usd')[coin]['usd']
        except:
            price = 0
        market_value = qty * price
        buy_trades = [t for t in data['trades'] if t['side'] == 'buy' and t['symbol'] == coin]
        if buy_trades:
            total_cost = sum(t['price'] * t['qty'] for t in buy_trades)
            total_qty = sum(t['qty'] for t in buy_trades)
            avg_entry = total_cost / total_qty if total_qty else 0
        else:
            avg_entry = 0
        summary += (f"{coin}: {qty} coins @ avg ${avg_entry:.2f} "
                    f"(market: ${market_value:.2f}) P/L: ${market_value - avg_entry * qty:.2f}\n")
    return summary

def get_price(symbol):
    coin_map = {
        "BTC/USD": "bitcoin",
        "ETH/USD": "ethereum",
        "USDT/USD": "tether",
        "LTC/USD": "litecoin",
        "XRP/USD": "ripple"
    }
    coin_id = coin_map.get(symbol.upper())
    if not coin_id:
        return f"Unsupported symbol: {symbol}. Supported: {', '.join(coin_map.keys())}"
    cg = CoinGeckoAPI()
    price = cg.get_price(ids=coin_id, vs_currencies='usd')[coin_id]['usd']
    return f"The latest price of {symbol} is ${price}."

def place_order(symbol, qty, side="buy", order_type="market", time_in_force="gtc"):
    symbol = symbol.upper()
    if symbol not in ["BTC/USD", "ETH/USD", "USDT/USD", "LTC/USD", "XRP/USD"]:
        return f"Unsupported symbol: {symbol}."
    qty = float(qty)
    if qty <= 0:
        return "Quantity must be positive."
    cg = CoinGeckoAPI()
    coin_id = {
        "BTC/USD": "bitcoin",
        "ETH/USD": "ethereum",
        "USDT/USD": "tether",
        "LTC/USD": "litecoin",
        "XRP/USD": "ripple"
    }[symbol]
    try:
        price = cg.get_price(ids=coin_id, vs_currencies='usd')[coin_id]['usd']
    except:
        return "Could not fetch price."
    data = _load()
    if side == "buy":
        cost = qty * price
        if data['cash'] < cost:
            return f"Insufficient cash. Required ${cost:.2f}, available ${data['cash']:.2f}."
        data['cash'] -= cost
        data['holdings'][symbol] = data['holdings'].get(symbol, 0) + qty
    else:  # sell
        current_qty = data['holdings'].get(symbol, 0)
        if current_qty < qty:
            return f"Insufficient {symbol}. You hold {current_qty}."
        data['cash'] += qty * price
        data['holdings'][symbol] -= qty
        if data['holdings'][symbol] == 0:
            del data['holdings'][symbol]
    trade = {
        "timestamp": datetime.datetime.now().isoformat(),
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "price": price,
        "type": order_type
    }
    data['trades'].append(trade)
    _save(data)
    return (f"Simulated {side} order filled: {qty} {symbol} at ${price}.\n"
            f"Cash remaining: ${data['cash']:.2f}.")
