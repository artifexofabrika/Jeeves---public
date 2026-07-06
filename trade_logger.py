"""
trade_logger.py – Reusable trade persistence module.
Stores trades in ~/trade_history.json, provides helpers for counting and retrieval.
Supports market tagging ("crypto", "stocks") for unified logging.
"""

import json
import os
from datetime import date

TRADE_LOG_FILE = os.path.expanduser("~/trade_history.json")

def _load():
    if not os.path.exists(TRADE_LOG_FILE):
        return []
    try:
        with open(TRADE_LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def _save(trades):
    with open(TRADE_LOG_FILE, "w") as f:
        json.dump(trades, f, indent=2)

def log_trade(trade_dict):
    required_fields = ["trade_id", "timestamp", "pair", "side", "quantity", "price", "total", "status"]
    for field in required_fields:
        if field not in trade_dict:
            raise ValueError(f"Missing required trade field: {field}")
    if "market" not in trade_dict:
        trade_dict["market"] = "crypto"
    trades = _load()
    trades.append(trade_dict)
    _save(trades)
    return trades

def get_recent_trades(n=20, market=None):
    trades = _load()
    if market:
        trades = [t for t in trades if t.get("market") == market]
    return list(reversed(trades[-n:]))

def trades_today(market=None):
    trades = _load()
    if market:
        trades = [t for t in trades if t.get("market") == market]
    today_str = date.today().isoformat()
    return sum(1 for t in trades if t.get("timestamp", "").startswith(today_str))
