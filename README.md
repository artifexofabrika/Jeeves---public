# Jeeves – Private AI Valet (Open‑Source Core)

Jeeves is a self‑hosted AI valet that runs on a Jetson Orin Nano. It trades crypto and stocks, tracks wellness, and maintains a private knowledge lake. **No cloud. No subscription. No data leaves your house.**

This repository contains the open‑source core of Jeeves. The proprietary, mirror‑tuned persona and pre‑built knowledge lake are available only with a purchased unit.

**Get the full Jeeves experience:** [Indiegogo campaign](https://www.indiegogo.com/projects/jeeves-private-ai-valet)

**Live demo (open‑source base version):** [https://www.artifexofabrika.com/demo](https://www.artifexofabrika.com/demo)

## Quick Start

1. Flash a Jetson Orin Nano with Ubuntu 22.04.
2. Install dependencies: `pip install -r requirements.txt`
3. Set your API keys in `config.py` or environment variables.
4. Run the dashboard: `python3 jeeves_web.py`
5. Open `https://localhost:5000/dashboard` in your browser.

## Features

- Dashboard with Persona, Wellness, Data Lake, Stocks, Crypto, Email tabs
- Live crypto trading via Coinbase (paper trading supported)
- Paper stock trading via Alpaca
- Knowledge lake (ChromaDB) for your documents
- Wellness logging with CSV/JSON upload
- Telegram notifications

## License

Core code: GNU General Public License v3.0  
Persona tuning and pre‑built lake: Proprietary.

## Author

Randy Wolf – [artifexofabrika.com](https://www.artifexofabrika.com)
