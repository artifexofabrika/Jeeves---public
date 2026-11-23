# Project Delta — Jeeves

Tracks the distance between where the project is and where "Ready to Launch" sits, with milestones
marked met and unmet, plus a dated log so a successive instance does not have to reconstruct the
thread from git history.

**Relationships.** `PHILOSOPHY.md` states what Jeeves is and the invariants it must satisfy.
`PROJECT-STATE.md` is the audit of record — the evidence base produced by the read-only evaluation of
2026-11-23; this file references it and does not restate its findings. `PARKING-LOT.md` holds work
that is real but not now.

**Status vocabulary.** MET · ACTIVE · UNMET · BLOCKED (needs a fact or decision) · DEFERRED (decided
later, deliberately) · OUT OF SCOPE. The evidence column must point at a file, a command result or an
audit section. An opinion is not evidence.

**Cadence.** Updated at least once per session, and immediately on any major milestone or change of
direction. Newest session first in the log.

---

## Current state — 2026-11-23

**Hardware.** Jetson Orin Nano 8GB "Super" Developer Kit — 8 GB 128-bit LPDDR5 at 102 GB/s, usable
≈ 7.4 GB. Storage is a 256 GB NVMe SSD; the SD card that failed has been removed from service. A
2 TB option exists. Production units are specified at 1 TB minimum.

**Software.** Branch `main`, 47 tracked files, 31 Python modules (28 at root, 3 under `adapters/`).
No tests. No `requirements.txt`. Dormant.

**Runs.** `jeeves_web.py` on port 5000 over hardcoded TLS, with persona, wellness and dashboard
blueprints; `llama-server` on 8080 serving Llama-3.2-1B-Instruct Q4_K_M at 2048 context; the Telegram
bridge; `lake_ingest.py` as a one-shot.

**Does not run.** Anything expecting a model on port 8081 (five modules); every trading advisor (no
scheduler exists); `/settings` (blueprint never registered); `/email` (stub); `/trading_feedback` (no
registered handler); the approval-signal files (nothing reads them).

**Memory.** Estimated 1.5–2.1 GB resident, ~2.8 GB peak during a lake query. **Not yet measured on
the target board** — that is milestone M2.

Evidence for all of the above: `PROJECT-STATE.md` §1–§3.

## Future state — "Ready to Launch"

A unit that can be handed to its owner: one model tier running within its memory budget, TLS trusted
by a phone, an authenticated interface reachable only over a private tunnel, health and financial
data encrypted at rest with a rotation backup proven to restore, a single crypto execution path with
real caps and a human approval step, an install that works from a clean JetPack image with
`requirements.txt`, and a valet that says "I do not know" instead of guessing.

Launch is not: 14B, fine-tuned persona layers, multi-user, any cloud dependency, or a second model
server running alongside the first.

## Milestones

| ID | Milestone | Status | Evidence / next action |
|---|---|---|---|
| M0 | Read-only audit of record | **MET** | `PROJECT-STATE.md`, 2026-11-23 |
| M1 | Documentation protocol in place | **MET** | This file set |
| M2 | Boots cleanly on the target board | **ACTIVE** | Port off 5000; TLS path out of `/home/jeeves/ssl`; one lake-path constant instead of seven hardcoded strings; then record `free -m` with `llama-server` resident |
| M3 | TLS trusted by phone and tablet | UNMET | mkcert internal CA already in use on other projects; install root on each device |
| M4 | Auth, CSRF and interface binding | UNMET | Session auth, CSRF tokens on all POSTs, bind to the tunnel interface rather than `0.0.0.0` |
| M5 | Backup that restores | UNMET | Two USB drives in rotation, LUKS, scheduled; Chroma-safe snapshot; one successful restore test; alert on failure |
| M6 | PWA replaces Telegram | UNMET | Single UI shell + manifest + service worker; approvals queue; delete the Telegram bridge and its token from config |
| M7 | One crypto execution path with real limits | UNMET | Choose paper-sim or broker+adapters, delete the others; enforce caps in the execution path; approval gate |
| M8 | Shipping model tier | UNMET | 3B–4B within 8 GB; embedding model cached at module scope; summariser attached to a model server that actually runs |
| M9 | Installable by someone else | UNMET | `requirements.txt`, install doc, first tests |
| M10 | NX 16GB and 7B validation | DEFERRED | Commercial decision; arithmetic in audit §2 |
| M11 | 14B on AGX 32GB | OUT OF SCOPE | Launch does not require it |
| M12 | VPN substrate decision | **BLOCKED** | Needs one fact: does the ISP provide a public IPv4, or is it CGNAT? |

### M2 — boot and measurement checklist

Run on the target board, as the user the unit runs as. Record the results in the session log below;
this is the first milestone whose evidence is a measurement rather than a reading.

1. Port free? `ss -ltnp | grep 8443` — if something is there, pick another and set `JEEVES_WEB_PORT`.
2. Certificates: mkcert cert and key at `~/ssl/cert.pem` and `~/ssl/key.pem`, or set
   `JEEVES_TLS_ENABLED=false` for a first plain-HTTP test. With TLS on and files missing the app now
   prints which paths it wanted and exits 1 rather than starting half-broken.
3. Lake path: `LAKE_INDEX_PATH` should point at the NVMe, not the old SD mount. `mkdir -p` it first.
4. `systemctl start llama-server`, confirm 8080 answers.
5. `python3 jeeves_web.py` — expect one startup line naming scheme, host and port.
6. Measure with both processes resident: `free -m`, and RSS per process
   (`ps -o rss=,cmd= -p $(pgrep -f jeeves_web)`) plus `systemctl status llama-server`.
7. Measure the peak: RSS before and after one lake query from the dashboard, so the embedding-model
   cost is a number rather than an inference.

## Conventions

**Python filenames.** `jeeves_<domain>_<role>.py`, lowercase, underscores only — hyphens are illegal
in an importable module name, so `jeeves-app.py` cannot be imported at all. The prefix namespaces a
flat root folder against the standard library and against anything installed. Roles in use: `_web`
and `_chat` for entry points; a bare domain name for a Flask page (`jeeves_dashboard.py`); `_advisor`
for an LLM decision loop; `_paper` and `_broker` for order execution, which is the distinction the old
names hid; `_engine` for shared logic; `_ingest` for pipelines; `_log`, `_search`, `_graph`, `_keys`
for supporting modules.

**Folders.** A folder supplies its own prefix, so `adapters/coinbase.py` needs none.

**Documented exception.** `config.py` keeps its name. The README instructs users to edit it, `.env`
tooling and the `dotenv` convention expect it, and every module imports it; renaming it would touch
every import and the install documentation for no gain.

**Application.** New files conform from the moment they are created. Existing survivors are renamed
the next time they are opened for other work. Files scheduled for deletion are **deleted, never
renamed**: the Telegram bridge, `mirror_service.py`, the duplicate `trading_blueprint.py` and
`trading_routes.py`, `static/trading.js`, `demo.html`, `landing.html`, and the stray 73-byte
`persona.txt`.

**Markdown.** Governing documents in uppercase with hyphens: `PHILOSOPHY.md`, `PROJECT-STATE.md`,
`PROJECT-DELTA.md`, `PARKING-LOT.md`.

**Runtime state.** Never tracked, never named after a module: `~/crypto_sim_portfolio.json`,
`~/trade_history.json`, `~/personal_graph.json`, `~/api_keys.json`, `~/trade_daily_equity.json`.

**Templates.** `.example` suffix for anything a user must copy and fill; no real credential in any
tracked file (audit §4).

## Decisions log

**2026-11-23 — Target board confirmed** as the Orin Nano 8GB Super Developer Kit. Audit §2 rewritten
against 7.4 GB usable; conclusion that today's stack (~2 GB) fits with room.

**2026-11-23 — Storage.** Failed SD card replaced with a 256 GB NVMe SSD. 2 TB upgrade available; not
taken. Production units specified at 1 TB minimum.

**2026-11-23 — Backup standard.** Two USB drives in rotation, LUKS-encrypted. Decided before the card
failure; **not implemented in the repository** — no script, no unit, no `cryptsetup` call exists.

**2026-11-23 — Telegram retired in favour of a PWA over VPN.** Reason: bot traffic and message
history sit on a third party's infrastructure, which contradicts invariant I1 for medical content. It
was a testing channel, not the product.

**2026-11-23 — TLS via internal CA.** mkcert, already the standard on other projects, rather than a
public certificate.

**2026-11-23 — VPN substrate.** Plain WireGuard preferred for one server and two or three client
devices; Headscale researched and documented as the fallback if CGNAT forces a relay. Blocked on the
CGNAT test (M12).

**2026-11-23 — Documentation protocol adopted.** Philosophy, Delta, Parking Lot, with
`PROJECT-STATE.md` retained as the audit of record that the Delta references rather than duplicates.

**2026-11-23 — Grounding contract accepted** as invariant I2, which obliges changes to `/chat` and
forbids trading on unparsed model output.

**2026-11-23 — Naming convention adopted.** `jeeves_<domain>_<role>.py`, underscores, because hyphens
break imports. New files conform immediately; survivors are renamed when next opened; files pending
deletion are not renamed. `config.py` is a documented exception. The two misleading crypto survivors
are settled by name now and applied when M7 lands: `crypto_sim.py` → `jeeves_crypto_paper.py`,
`trading_advisor.py` → `jeeves_stock_advisor.py`.

## Session log

### 2026-11-23 — Session 1: audit, board sizing, protocol

Read the whole tree without changing code. Produced `PROJECT-STATE.md`: entry point and reachability,
fifteen Python files plus one static asset that nothing imports, runtime demand (~2 GB resident today,
~5 GB with a Q4 3.8B second model, ~18 GB for a 14B at 32k context), eight things that were mid-flight
when the card failed, `config.py` variable inventory and the unauthenticated-dashboard exposure, and
three ordered recommendations.

Then sized the 8 GB board against the intended 7B/14B roadmap, corrected the earlier "AGX buys
nothing" conclusion, and recorded storage, backup, Telegram and VPN decisions as they were taken in
conversation. Adopted the three-document protocol and the naming convention.

**Open.** M2 is the only milestone that can move next without a decision from the owner. M12 needs the
CGNAT fact. The working copy on this machine is the only copy of the project; nothing has been staged
or committed this session.
