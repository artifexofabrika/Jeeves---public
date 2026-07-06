"""
trade_logger.py – Reusable trade persistence module.
Stores trades in ~/trade_history.json, provides helpers for counting and retrieval.
No trading logic or limit enforcement lives here.
"""

import json
import os
from datetime import date

TRADE_LOG_FILE = os.path.expanduser("~/trade_history.json")


def _load():
    """Load all trades from the log file. Returns a list, empty if missing."""
    if not os.path.exists(TRADE_LOG_FILE):
        return []
    try:
        with open(TRADE_LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save(trades):
    """Write the trade list to the log file."""
    with open(TRADE_LOG_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def log_trade(trade_dict):
    """
    Append a validated trade record to the log file.
    trade_dict must include: trade_id, timestamp, pair, side, quantity, price, total, status.
    Returns the updated list of all trades.
    """
    required_fields = ["trade_id", "timestamp", "pair", "side", "quantity", "price", "total", "status"]
    for field in required_fields:
        if field not in trade_dict:
            raise ValueError(f"Missing required trade field: {field}")

    trades = _load()
    trades.append(trade_dict)
    _save(trades)
    return trades


def get_recent_trades(n=20):
    """Return the last n trades, most recent first."""
    trades = _load()
    return list(reversed(trades[-n:]))


def trades_today():
    """Return the number of trades executed today (based on timestamp date)."""
    trades = _load()
    today_str = date.today().isoformat()
    count = 0
    for t in trades:
        ts = t.get("timestamp", "")
        if ts.startswith(today_str):
            count += 1
    return count
