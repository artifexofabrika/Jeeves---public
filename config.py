import os

LLM_URL = os.getenv("LLM_URL", "http://localhost:8080/v1/chat/completions")

# API keys – replace with your own
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY", "")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET", "")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")

# Telegram (optional)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# File paths
CRYPTO_STRATEGY_FILE = os.path.expanduser("~/crypto_sim_strategy.txt")
TRADING_STRATEGY_FILE = os.path.expanduser("~/trading_strategy.txt")
TRADING_MIRROR_LOG = os.path.expanduser("~/trading_mirror.log")
