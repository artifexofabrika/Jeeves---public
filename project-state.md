# Jeeves — Project State, before touching anything

Read-only evaluation of `C:\Users\drinr\Desktop\Jeeves`, branch `main`, 47 tracked files
(confirmed against `.git/index`, not assumed). No code was changed to produce this. Nothing here
is inferred from a filename; each claim is sourced to a file and line where it matters.

**Status: audit of record, frozen at 2026-11-23.** This document is evidence, not a tracker. Progress
lives in `PROJECT-DELTA.md`, intent in `PHILOSOPHY.md`, and deferred work in `PARKING-LOT.md`. Do not
update findings here as they are fixed; record the fix in the Delta and let this stand as what was
true at evaluation.

Two corrections to the brief so the counts below are honest: there are **28 Python modules at the
root, not 30**, plus 3 under `adapters/` — 31 Python modules. And there is **no
`requirements.txt`**, so README step 2 (`pip install -r requirements.txt`) cannot be executed as
written.

---

## 1. What actually runs, and what does not

### The entry point

`jeeves_web.py`. It creates Flask at line 7, registers three blueprints at 853–858
(`persona_bp`, `wellness_bp`, `dashboard_bp`), and starts at line 878:

`app.run(host="0.0.0.0", port=5000, debug=False, ssl_context=("/home/jeeves/ssl/cert.pem", "/home/jeeves/ssl/key.pem"))`

Three things follow from that one line, and all three block a clean redeploy:

- **Port 5000**, as the README says. Occupied on the Jetson by another product. Noted, not fixed.
- **TLS is mandatory and hardcoded.** If `/home/jeeves/ssl/cert.pem` is absent, `app.run` raises
  before the first request is served. `jeeves-web.service` runs as user `drinrin` with
  `WorkingDirectory=/home/drinrin`, so the process has no route to `/home/jeeves/` unless those
  certs were copied there by hand. Most likely reason a clean deploy never comes up.
- The README's URL is `https://localhost:5000/dashboard`, i.e. TLS is assumed throughout.

At import time the web process pulls in `crypto_sim`, `trading_advisor`, `config`, `lake_utils`,
`web_search`, `personal_graph` and `chromadb` (lines 3–5). So `chromadb`, and through it NumPy and
the embedding stack, is resident from the first second, before any request arrives.

### Live, reachable from the entry point

- `jeeves_web.py` — `/` (an older chat UI), `/chat` keyword router, `/command`, the mirror routes,
  `/api/recent_trades`, `/landing`, `/favicon.png`.
- `persona_module.py` — blueprint, one route `/persona`, renders a static page.
- `wellness_module.py` — blueprint, one route `/wellness`, renders a **placeholder page** ("This
  module is under active development"; all three buttons `disabled`).
- `dashboard_module.py` — `/dashboard` plus 20 endpoints: `/add_api_key`, `/wellness_upload_api`,
  `/live_crypto_account`, `/update_persona`, `/update_strategy`, and the trading/crypto
  refine·save·reload·reset family.
- `config.py` — imported by nearly everything; env loader, no literals.
- `crypto_sim.py` — **paper** crypto. CoinGecko prices, JSON portfolio on disk, 5 hardcoded pairs.
- `trading_advisor.py` — Alpaca **paper** stocks. Account/positions/order functions work; `main()`
  does not (see §3).
- `mirror_engine.py` — file-copy persona/strategy versioning plus one LLM rewrite call. The
  `apply_feedback` path is real and is what the Mirror tab actually calls.
- `lake_utils.py` — Chroma helpers: query, store messages, wellness entries, memory baseline.
- `personal_graph.py` — dot-path JSON fact store; `graph_summary()` is injected into the final
  prompt at `jeeves_web.py:532`.
- `trade_logger.py`, `strategy_parser.py` — `~/trade_history.json`; limits parsed from the
  strategy text file.
- `web_search.py` — optional DDG/Brave search, gated on `WEB_SEARCH_ENABLED`.

Live as *processes* rather than imported modules: `jeeves_telegram.py` (systemd via
`start_jeeves_services.sh`, long-poll loop) and `lake_ingest.py` (same script, `nohup`).

### Nothing imports these

Twelve root modules, all three adapters, and one static asset have **no importer and no reference
anywhere in the tree**: `chat_summarizer.py`, `classifier.py`, `crypto_sim_advisor.py`,
`email_skill.py`, `extract_facts_worker.py`, `live_trading_advisor.py`, `mirror_service.py`,
`settings_module.py`, `trading_blueprint.py`, `trading_routes.py`, `broker.py`, `keychain.py`,
plus `adapters/binance.py`, `adapters/coinbase.py`, `adapters/kraken.py`, and `static/trading.js`.

Three of those are one hop from the trunk and matter, because together they make the "live crypto
trading" claim look true when it is not:

- `keychain.py` is imported by `email_skill.py` only, and `email_skill.py` is imported by nothing.
- `broker.py` is imported by `live_trading_advisor.py` only, and `live_trading_advisor.py` is
  imported by nothing. `adapters/*` are reachable only through `broker._adapter()`'s `importlib`
  call. **The entire Coinbase order path is a closed island.** `dashboard_module.py:239` does build
  a Coinbase `RESTClient` inline for `/live_crypto_account`, so read-only balances are genuinely
  reachable; order placement is not.
- `static/trading.js` is the front-end for the trading tab and calls `/trading_feedback`, which is
  defined only in `trading_blueprint.py:15` and `trading_routes.py:14` — neither registered. That
  URL is a 404. This is the split-out trading UI that was never reconnected.

`lake_ingest.py` and `jeeves_telegram.py` are script-only (started by the unit, imported by
nobody). `jeeves_chat.py` is a REPL script that `jeeves_telegram` imports for `handle_command`, and
that single import is the only reason any of it is live.

### Does not run

- **Anything speaking to port 8081.** Five modules point at `http://127.0.0.1:8081`
  (`classifier.py:8`, `chat_summarizer.py:9`, `extract_facts_worker.py:13`, `email_skill.py:21`,
  `lake_ingest.py:15`) expecting Phi-3-mini. `llama-server.service` starts only 8080 with a 1B
  model. Nothing in the repo starts 8081. Each of those five catches the connection error and
  returns `""` or `CONVERSATION`, so the failure is completely silent.
- **Any autonomous trading.** Nothing calls `.main()` on any advisor: no cron entry, no `.timer`
  unit (three `.service` files, zero timers), no thread. Every advisor runs only when a human types
  its filename.
- **The approval gate.** `jeeves_telegram.py:107` writes `~/coinbase_approve_<id>.signal`; line 92
  writes `~/coinbase_halt.signal`. **No file in the tree reads either one.**
  `live_trading_advisor.py` logs "Autonomous mode – executing immediately." and places the order.
- **`mirror_service.py`** — a second Flask app on port 5001 with `CORS(app)`, orphaned, and it
  references `config.AI_NAME` at line 68 while never importing `config`, so that branch raises
  `NameError` which its own `except` swallows.
- **`/settings`** — `settings_module.py` defines `settings_bp` and a full key-entry page;
  `jeeves_web.py` never registers it. The route does not exist.
- **`/email`** — returns "Email module not yet available, sir." in `jeeves_web.py:597` and
  `jeeves_chat.py:243`; the dashboard tab says "Email (Coming Soon)"; and `email_skill.py` is a
  266-line IMAP/SMTP implementation that nobody calls.
- **The wellness *tab*** — logging genuinely works through `/chat` ("add to wellness …") and
  `lake_utils.store_wellness_entry`, but the page the tab renders is a placeholder. UI and engine
  are at different stages of the same feature.

`/dashboard` and `/` are two different chat UIs sharing duplicated CSS, each with its own
`sendMessage()`. `/trading_refine`, `/trading_save`, `/trading_reload` and `/trading_reset` are
each defined **twice** — on `app` at `jeeves_web.py:807–843` and on `dashboard_bp` at
`dashboard_module.py:123–166`. Flask does not error on that; the first matching rule wins, so which
implementation answers is registration order, not intent. `trading_blueprint.py` holds a third copy
of the same four routes.

---

## 2. Runtime demand — the number to size a board against

Derived from what the code and unit files actually load, plus published model sizes. **These are
estimates, not measurements.** Run `free -m` on the target with `llama-server` up and reconcile
before committing to a board; the estimates are the part I expect to be wrong.

### The board this is being sized against

Confirmed: **Jetson Orin Nano 8GB "Super" Developer Kit** — 8 GB 128-bit LPDDR5 at 102 GB/s, 6-core
Cortex-A78AE, 1024 CUDA cores / 32 tensor cores, 67 INT8 TOPS, 7–25 W, SD card slot plus external
NVMe. One thing the numbers below have to respect: the memory is **unified**, so model weights and
GPU working set come out of the same 8 GB (usable ≈ 7.4 GB after the JetPack carveout).

Storage is no longer a question: the failed SD card has been replaced with a **256 GB NVMe SSD**.
That retires the I/O half of the "it felt slow" diagnosis and makes the Chroma index resident on
fast local storage rather than on a card. It does not make the drive a backup — the owner's stated
standard is two USB drives in rotation, LUKS-encrypted, with production units shipping at a 1 TB
minimum. None of that is implemented in this repository. See the note at the end of this section.

### Resident simultaneously, steady state

| Process | Source | RAM, estimated |
|---|---|---|
| `llama-server` — Llama-3.2-1B-Instruct **Q4_K_M**, `--ctx-size 2048`, 0.0.0.0:8080 | `llama-server.service` | ~0.81 GB weights + ~0.07 GB KV at 2048 ctx + runtime ≈ **1.1–1.4 GB** |
| `jeeves_web.py` — Flask + `chromadb` at module scope, `trading_advisor`, `crypto_sim` | `jeeves-web.service` | interpreter+Flask ≈ 70 MB; `chromadb`+NumPy ≈ 250–400 MB; **0.4–0.6 GB idle** |
| `all-MiniLM-L6-v2` under PyTorch | constructed per call, see below | ~90 MB weights, +300–450 MB torch arena at first use |
| `jeeves_telegram.py` — long-poll, `time.sleep(1)` | `jeeves-services.service` | **40–70 MB** |
| Chroma client on `/mnt/lake/index` | mmapped by the web process | tens of MB, grows with the lake |

**Steady state, all three processes, nothing in flight: roughly 1.5–2.1 GB.** With a lake query or
a wellness upload in flight: **peak ~2.5–2.8 GB**, then it settles.

Two structural reasons the peak is that high, both worth knowing before the board decision:

1. `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")` is constructed **inside
   request handlers** and never cached — `jeeves_web.py:19`, `:405`, `jeeves_chat.py:27`,
   `trading_advisor.py:90`, `dashboard_module.py:69`. Every lake hit, every wellness upload, every
   advisor run pays a fresh model construction. That, more than the LLM, is "it felt slow on a Nano".
2. `lake_ingest.py` builds the same embedding function **at import**, so the one-shot that
   `start_jeeves_services.sh` fires with `nohup` drags a full PyTorch load into memory, does one
   batch, and exits. Not resident, but a ~0.7 GB spike on every start.

### What a trading loop costs

There is no loop. One advisor run is a single LLM completion (`max_tokens` 150–200 in
`live_trading_advisor.py`, 200 in `trading_advisor.py` and `crypto_sim_advisor.py`), three lake
queries in `trading_advisor.main()` (lines 168–171) each rebuilding the embedding model, plus
several CoinGecko/Alpaca HTTP calls. On a Nano that is tens of seconds of wall clock and a transient
0.7–1 GB process that exits. Scheduling it every five minutes would cost nothing in RAM and a lot in
latency and heat — probably the honest reason it was run by hand.

### The decision that determines the board

The five 8081 clients expect Phi-3-mini (3.8B). If that becomes real, on top of the above:

- Q4_K_M ≈ **2.2–2.6 GB** with KV at 2048 ctx → total **~4.5–5 GB**
- fp16 ≈ **7.5–8 GB** → total **~9.5–10 GB**, which on a shared-memory Jetson is over budget at 8 GB

Against the confirmed 8 GB board (≈ 7.4 GB usable), the arithmetic reads like this:

- **Today's stack, ~2 GB:** comfortable. Roughly 5 GB of headroom. The 8 GB Nano is not what was
  failing, and this is worth stating plainly — if the "could not carry the load" experience was the
  stack as it exists in this repo, then RAM was not the constraint and a 16 GB NX will not feel
  faster. With the NVMe now in place that leaves one suspect standing: the per-request embedding
  reload (see above), and that one is fixable in software for free.
- **Plus Phi-3-mini at Q4 (~2.3 GB), a llama.cpp CUDA context (0.2–0.4 GB) and the OS (0.8–1.2 GB):**
  lands near 6 GB. It fits, with under 1.5 GB spare and no room for a lake re-index spike.
- **Plus Phi-3-mini at fp16 (~7.5 GB):** does not fit on 8 GB at all, in any arrangement.

So the board decision turns on one question the repo cannot answer: what exactly was loaded when it
failed. If it was Phi-3-mini at fp16, no 8 GB board carries it and 16 GB is the correct fix. If it
was the ~2 GB stack, the NX is buying headroom you have not yet written code to use.

The AGX is a separate question, and the owner has since stated the answer: a 7B/14B conversational
target changes the arithmetic, and the table below works it out. On that roadmap the AGX is
justified — but only by the 14B tier, and by nothing in this repository today.

### Headroom for the intended 7B/14B valet

Stated target: ship on a 3B–4B model, move to 7B and then 14B on NX or AGX, keep enough context to
feel like an old friend, and eventually tune selected layers.

The number that decides this is **not model size, it is the KV cache**, because it grows linearly
with context and has to live in the same unified pool as the weights. Per token, fp16 KV costs
2 × layers × kv_heads × head_dim × 2 bytes:

| Model | Layers / KV heads | KV per token | Weights Q4_K_M | @8k ctx | @32k ctx |
|---|---|---|---|---|---|
| Qwen2.5-3B | 36 / 2 | 36 KiB | ~1.9 GB | +0.3 GB | +1.1 GB |
| Qwen2.5-7B | 28 / 4 | 56 KiB | ~4.7 GB | +0.45 GB | +1.75 GB |
| Llama-3.1-8B | 32 / 8 | 128 KiB | ~4.9 GB | +1.0 GB | +4.0 GB |
| Qwen2.5-14B | 48 / 8 | 192 KiB | ~9.0 GB | +1.5 GB | +6.0 GB |

Add ~2 GB for Jeeves itself (§ above) and ~1 GB for the OS:

- **3B at 8k on the current Nano:** ~5.2 GB. Fits 8 GB with room. The shipping plan is sound.
- **7B at 32k on an NX 16GB:** ~9.5 GB. Fits, with roughly 6 GB spare. This is the sweet spot.
- **8B at 32k on an NX 16GB:** ~11.9 GB. Fits, ~4 GB spare.
- **14B at 8k on an NX 16GB:** ~13.5 GB. Fits barely — no room for a second model, none for training.
- **14B at 32k:** ~18 GB. Does not fit 16 GB. This is the AGX case, and the only one.

Decode speed is memory-bandwidth bound, not TOPS bound: tokens/sec ceiling ≈ bandwidth ÷ bytes read
per token. Per the Orin series datasheet, Orin NX is 102.4 GB/s (both SKUs) and AGX Orin is
204.8 GB/s, at 10–25 W for NX versus 15–60 W for AGX.

- 7B Q4 (4.7 GB) on NX: ceiling ~21 tok/s, realistic 10–14.
- 14B Q4 (9.0 GB) on NX: ceiling ~11 tok/s, realistic 5–7 — too slow for conversation.
- The same 14B on AGX 32GB: roughly double, so 10–14 tok/s. Conversational.

Two levers matter more than the model tier for the "old friend" feel, and both are free:

1. **Retrieval and summarisation instead of a long context window.** `personal_graph.py` already
   caps `conversation_memory` at 30 entries, and `chat_summarizer.py` was written to fold exchanges
   into the lake — on the 8081 model that was never started. That loop, working, will make a 3B
   model feel more like a trusted valet than a 14B model with a 4k window.
2. **Cache the embedding model.** One module-level singleton instead of a per-request construction
   (`jeeves_web.py:19`, `:405`, `jeeves_chat.py:27`, `dashboard_module.py:69`). That is the
   difference between a lake answer arriving in ~2s and ~6s on the Nano, and it costs nothing.

On tuning "selected layers": that is LoRA/QLoRA. An NX 16GB can QLoRA a 7B at short sequence
lengths, slowly; a 14B QLoRA does not fit in 16 GB. Train off-device, merge the adapter, convert to
GGUF, and deploy — a Jetson is inference iron, not training iron. The GPLv3 core stays open; the
adapter stays yours.

Storage redundancy was settled before the card failed: two USB drives in rotation, LUKS-encrypted,
1 TB minimum on production units. That is a sound standard and it answers the backup objection. The
caveat is that **none of it exists in the tree** — no backup unit, no script, no `cryptsetup` call,
no README section. The decision lives in the owner's head and in this document, which is precisely
the state that lost a working copy to a dead card.

When it gets built, two details decide whether it is real or theatre:

- **A live Chroma directory cannot be copied safely.** The SQLite file and the HNSW segment files may
  be mid-write, so a plain `cp`/`rsync` of `/mnt/lake/index` yields a torn backup some fraction of
  the time. Stop the service, or use the SQLite backup API / `VACUUM INTO`, and verify the copy
  restores before trusting it.
- **The LUKS key must not live on the disk being backed up**, and not in `~/api_keys.json` either —
  that file is plaintext on the same NVMe (§4). A rotation with the key sitting beside the ciphertext
  protects against theft of one drive and nothing else.

The concern that outranks both: once the lake holds bowel, mood and medication conversations, an
unauthenticated dashboard on the LAN serving a plaintext Chroma directory is not a place to keep a
man's health journal.

---

## 3. What was in progress when the card failed

Ordered by how much each tells you about where the design was heading.

1. **A two-model split that was never finished.** The 8081/Phi-3-mini clients in five modules are
   the newest stratum: intent classification, chat summarisation, fact extraction, email triage,
   lake keyword tagging. The service definition for 8081 was never written. The files that would
   have made Jeeves feel quick are all silently degraded right now.

2. **The broker refactor, mid-flight.** Three generations of crypto execution sit side by side:
   `crypto_sim.py` (paper, live, oldest, dumb), `crypto_sim_advisor.py` (an LLM brain bolted onto
   the paper sim), and `live_trading_advisor.py` + `broker.py` + `adapters/{binance,coinbase,kraken}.py`
   (exchange-agnostic, newest, cleanest). The newest is the only one that touches a real exchange,
   and the only one nothing imports. The refactor was heading there and stopped.

3. **Human approval, half-wired.** `/approve` and `/halt` in the Telegram bridge write signal files;
   the executing advisor ignores them and trades immediately. The most consequential unfinished
   thing in the repo.

4. **Two half-migrations inside `trading_advisor.main()`, on the same risk control.**
   `daily_loss_exceeded()` at line 78 is a stub returning `False  # placeholder`; its call site is
   commented out at 138–142; and a *second*, newer attempt at the same check was pasted in at
   117–122, reading `portfolio_value` at line 119 **before it is assigned at line 136**. First run
   of the day works, every run after that raises `NameError`. `MAX_DAILY_TRADES`, `MAX_ORDER_VALUE`
   and `MAX_DAILY_LOSS` exist only inside the `if __name__` block, so the function is unusable when
   imported by the dashboard. The risk layer was being rewritten and the incoming version never ran.

5. **The personal graph was moved, not abandoned.** `jeeves_web.py:479–482` has the injection
   commented out as "temporarily disabled; moved to final prompt assembly", and it is re-implemented
   at 532–534. That migration completed. The graph file (`~/personal_graph.json`) is gitignored and
   absent from the tree, so on a fresh board the graph is empty until conversation fills it.

6. **`extract_facts_worker.py`'s docstring claims "Runs independently via systemd timer every 15
   seconds." No such timer exists.** Its last-run file and the `extracted` metadata flag show it was
   designed for a cadence that was never installed.

7. **Copy-paste debris from the last session.** `jeeves_chat.py` has the `/crypto-halt` and
   `/crypto-resume` blocks **duplicated verbatim**; the second pair is dead. `/mirror_apply` calls
   `ask_llm(...)`, which does not exist in that file (it lives in `jeeves_web.py`), and the
   `NameError` is caught by a bare `except` and reported as "Mirror apply error".
   `/crypto-strat_read` calls `json.dumps` without importing `json`, also swallowed, so it always
   returns `[]`. `email_skill.py:250` sends to an undefined `YOUR_PROTON_EMAIL`.

8. **Diagnostic rather than functional:** the `# Email (stubbed)` comment in two files, "Coming Soon"
   in the dashboard, and a 266-line working email engine in the tree — a feature finished on one
   side and never connected on the other.

No tests, no session deltas, no `requirements.txt`. The repo is the engine only, as you said.

---

## 4. What is publicly exposed that should not be

### `config.py` — by variable name, no values

Tracked and public. It contains **no literal credentials**: every value is `os.getenv(...)`, and the
file's only literal defaults are a localhost URL, `"llama"`, `2048`, and `~`-relative paths.

Variables, in file order: `BOT_TOKEN`, `CHAT_ID`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`,
`COINBASE_API_KEY`, `COINBASE_API_SECRET`, `COINBASE_PASSPHRASE`, `WEB_SEARCH_ENABLED`,
`WEB_SEARCH_PROVIDER`, `BRAVE_SEARCH_API_KEY`, `AI_NAME`, `LLM_URL`, `LLM_MODEL`, `LLM_CTX_SIZE`,
`PERSONA_FILE`, `MIRROR_LOG`, `LAKE_INDEX_PATH`, `CRYPTO_STRATEGY_FILE`, `CRYPTO_MIRROR_LOG`,
`TRADING_STRATEGY_FILE`, `TRADING_MIRROR_LOG`, `USER_NAME`.

The file is clean today. **What still matters if it were real:** README step 3 tells a user to "Set
your API keys in `config.py` or environment variables", and `config.py` is tracked. Anyone following
the documentation puts live Coinbase and Alpaca secrets into a file that `git status` will offer to
commit. The variable names also enumerate exactly which seven credentials to hunt for on a unit. The
instruction is the hazard, not the current contents. Flagging, not arguing.

One default is decorative: `LAKE_INDEX_PATH` defaults to `/mnt/lake/index` and **no live module
reads it**. `jeeves_web.py:20`, `:406`, `jeeves_chat.py:27`, `trading_advisor.py:91`,
`lake_ingest.py:19`, `dashboard_module.py:70` and `extract_facts_worker.py:25` all hardcode that
string. Moving the lake means editing seven files, not one variable.

### Tracked files that `.gitignore` was supposed to cover

`.gitignore` contains `*.json` and names `personal_graph.json` explicitly. Two JSON files are
tracked anyway: `crypto_sim_portfolio.json` (`cash`, `holdings`, `trades`) and
`crypto_sim_vault.json` (`core_capital`, `secured_vault`). They are **paper-trading state, not
secrets** — no keys, no real balances. Two notes: ignore rules never apply to already-tracked paths,
and these copies are dead weight regardless, because `crypto_sim.py:4` reads
`~/crypto_sim_portfolio.json`. The working directory is `/home/drinrin`, so `~` is correct and the
repo copies are never consulted.

### The exposure that is actually serious

Not `config.py` — **the dashboard is unauthenticated.** `jeeves_web.py:880` binds `0.0.0.0:5000`,
TLS or not, and every route is open:

- `POST /add_api_key` (`dashboard_module.py:23`) takes a label, key, secret and passphrase and writes
  them **in plaintext** to `~/api_keys.json`. No auth, no CSRF, no origin check. That file is then
  read back by `keychain.py`, whose `list_all()` exists "for dashboard display".
- `POST /update_persona` and `POST /update_strategy` (`:276`, `:261`) overwrite the persona file and
  the trading strategy file with arbitrary text. The strategy is what the advisor reads before
  placing an order.
- `POST /refine_persona`, `/factory_reset`, `/reload_saved`, `/trading_reset` overwrite or destroy
  prompt state.
- `mirror_service.py`, if ever started, adds `CORS(app)` — any origin — and runs
  `sudo systemctl restart jeeves-web` from inside a request handler.
- `/live_crypto_account` returns raw Coinbase balances as a plain string to anyone who asks.

That should be fixed before this unit sits on a network that is not your own.

---

## 5. The three things I would do first, in order

**1. Make it start on the new board, and take a real measurement while it is up.**
The hardcoded `/home/jeeves/ssl` cert paths against a unit running as `drinrin`, the occupied port
5000, and the seven hardcoded `/mnt/lake/index` paths are three guaranteed first-hour failures, and
none of them is the interesting kind. Until it boots on the NX and prints `free -m` with
`llama-server` resident, every figure in §2 is my arithmetic rather than your machine.

**2. Decide the Phi-3-mini question — resident, or delete its five clients.**
It is the only thing that moves the answer between 8 GB and 16 GB, and it is half-built: five
modules expect it, no unit starts it, and all five fail silently. Either commit and size for ~5 GB,
or strip the 8081 calls so the degradation becomes visible instead of mute.

**3. Kill two of the three crypto paths, and decide whether trading is manual or scheduled.**
Three brains, no scheduler, a placeholder loss limit, and an approval handshake whose signal files
nothing reads. Keep `live_trading_advisor` + `adapters/` if live Coinbase is the goal, or keep
`crypto_sim` if paper is, and delete the others in a commit that records why. This is the only place
in the repo where being wrong costs money rather than time.

Deliberately not on that list, though I would do it in the same fortnight: the unauthenticated
dashboard. It is not load-bearing for a board move, and it should not outlive one either.
