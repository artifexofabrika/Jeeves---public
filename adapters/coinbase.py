"""
Coinbase adapter for Jeeves broker interface.
Handles all Coinbase-specific symbol cleaning, price fetching, and order placement.
"""
import time
from coinbase.rest import RESTClient
import config

_client = RESTClient(
    api_key=config.COINBASE_API_KEY,
    api_secret=config.COINBASE_API_SECRET
)

def clean_symbol(raw_symbol):
    """
    Convert a raw symbol like 'ETH-USDT' or 'BTC-USD' into a valid Coinbase product ID.
    Result is always of the form 'XXX-USDT'.
    """
    sym = raw_symbol.upper().strip()
    # Remove any existing suffix first
    sym = sym.replace("-USDT", "").replace("-USD", "")
    return sym + "-USDT"

def get_price(symbol):
    """
    Return the current price for a given symbol.
    Expects a raw symbol like 'BTC-USD' or 'ETH-USDT'.
    Returns float price, or raises an exception with a clear message on failure.
    """
    product_id = clean_symbol(symbol)
    try:
        product = _client.get_product(product_id)
        return float(product['price'])
    except Exception as e:
        raise Exception(f"Failed to fetch price for {product_id}: {e}")

def place_order(symbol, qty, side):
    """
    Place a market order.
    Args:
        symbol: raw symbol, e.g. 'ETH-USDT'
        qty: quantity as a float
        side: 'buy' or 'sell'
    Returns:
        (order_id, error_message)
        On success, error_message is None.
        On failure, order_id is None.
    """
    product_id = clean_symbol(symbol)
    try:
        order = _client.market_order(
            client_order_id=f"jeeves_{int(time.time())}",
            product_id=product_id,
            side=side.upper(),
            base_size=str(qty)
        )
        order_dict = order.__dict__ if hasattr(order, '__dict__') else {}
        if order_dict.get('success', False):
            return order_dict.get('order_id', 'unknown'), None
        else:
            return None, str(order_dict)
    except Exception as e:
        return None, str(e)

def get_balances():
    """Return a dict of currency:available_balance for all accounts with non-zero balances."""
    accounts = _client.get_accounts()
    balances = {}
    for acct in accounts['accounts']:
        amt = float(acct['available_balance']['value'])
        if amt > 0:
            balances[acct['currency']] = amt
    return balances
