"""
strategy_parser.py – Reads trading limits from the crypto strategy file.
Parses MAX_ORDER_USD, DAILY_TRADE_LIMIT, and DASHBOARD_TRADE_COUNT.
Provides safe fallback defaults.
"""

import os

STRATEGY_FILE = os.path.expanduser("~/crypto_sim_strategy.txt")

DEFAULTS = {
    "MAX_ORDER_USD": 10,
    "DAILY_TRADE_LIMIT": 20,
    "DASHBOARD_TRADE_COUNT": 20,
    "MAX_DAILY_LOSS": 5.0,
}


def parse_limits(filepath=None):
    """
    Return a dict with keys max_order_usd, daily_trade_limit, dashboard_trade_count.
    Values are floats/ints read from the strategy file, falling back to DEFAULTS.
    """
    limits = DEFAULTS.copy()
    path = filepath or STRATEGY_FILE
    if not os.path.exists(path):
        return limits

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().upper()
            value = value.strip()
            if key in ("MAX_ORDER_USD", "DAILY_TRADE_LIMIT", "DASHBOARD_TRADE_COUNT", "MAX_DAILY_LOSS"):
                try:
                    if key == "MAX_ORDER_USD":
                        limits["MAX_ORDER_USD"] = float(value)
                    else:
                        limits[key] = int(value)
                except ValueError:
                    # Malformed line; keep default and log warning
                    print(f"Warning: could not parse '{line}' in {path}")
    return limits
