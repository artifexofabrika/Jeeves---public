"""
broker.py – Broker-agnostic interface for trading.
Reads EXCHANGE from the crypto strategy file and delegates to the appropriate adapter.
"""
import importlib
import os
import strategy_parser

def _get_exchange():
    """Return the exchange name from the strategy file, defaulting to 'coinbase'."""
    limits = strategy_parser.parse_limits()
    return limits.get("EXCHANGE", "coinbase").lower()

def _adapter():
    """Import and return the correct adapter module for the current exchange."""
    exchange = _get_exchange()
    try:
        return importlib.import_module(f"adapters.{exchange}")
    except ImportError:
        raise ImportError(
            f"Exchange '{exchange}' is not supported. "
            f"Please add an adapter at adapters/{exchange}.py"
        )

def clean_symbol(raw_symbol):
    return _adapter().clean_symbol(raw_symbol)

def get_price(symbol):
    return _adapter().get_price(symbol)

def place_order(symbol, qty, side):
    return _adapter().place_order(symbol, qty, side)

def get_balances():
    return _adapter().get_balances()
