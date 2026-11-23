# Parking Lot — Jeeves

Things that are real, worth fixing, and not the task at hand. The purpose is to keep them from being
lost without letting them pull focus. Nothing is deleted from here; it leaves only by being promoted
into a milestone in `PROJECT-DELTA.md`, or by an explicit "won't do" with a reason.

**Rules.** One row per item. The revisit trigger must be a condition, not a date — "when the PWA work
starts", not "next month". Severity is a guess, not a promise: LOW means "no user-visible harm today".

| ID | Item | Why it is parked | Revisit trigger | Severity |
|---|---|---|---|---|
| PL-01 | `mirror_service.py` references `config.AI_NAME` without importing `config`; its own `except` hides the `NameError` | Orphaned module, nothing imports it | When the mirror routes are consolidated, or the module is deleted | LOW |
| PL-02 | `jeeves_chat.py` has `/crypto-halt` and `/crypto-resume` defined twice, verbatim | Dead code; second pair unreachable | When the command router is next touched | LOW |
| PL-03 | `/crypto-strat_read` calls `json.dumps` without importing `json`, so it always returns `[]` | Bare `except` hides it; no functional loss today | With PL-02 | LOW |
| PL-04 | `email_skill.py` sends to an undefined `YOUR_PROTON_EMAIL` | Module is orphaned pending M6-era email work | When the email tab stops saying "Coming Soon" | LOW |
| PL-05 | `extract_facts_worker.py` docstring claims a systemd timer every 15 seconds that does not exist | Behaviour is correct-ish without it; doc lies | When the summariser loop is rebuilt for M8 | LOW |
| PL-06 | Two credential stores: `keychain.py` (`~/api_keys.json`) and `dashboard_module.add_api_key` writing the same file by a different route | Tied to the auth work; fixing now would be redone | During M4 | MED |
| PL-07 | `persona.txt` (73 bytes, tracked) versus `~/jeeves_persona.txt` as used by code — two names for the persona | Confusing but harmless; deployment copies the right one | When install docs are written (M9) | LOW |
| PL-08 | `demo.html`, `landing.html` and `static/trading.js` are unreferenced by any live route or template | Superseded by the PWA consolidation | During M6 | LOW |
| PL-09 | Triple definition of `/trading_refine`, `/trading_save`, `/trading_reload`, `/trading_reset` across `jeeves_web.py`, `dashboard_module.py` and `trading_blueprint.py` | Deletion belongs with the crypto-path collapse | During M7 | MED |
| PL-10 | `ask_llm` caps replies at `max_tokens=120`, which can truncate a legitimate answer mid-sentence | The voice guard wants 1–2 sentences, so it may be intentional | When the voice guard is revisited | LOW |
| PL-11 | UI polish: fonts, spacing, the dark palette, button sizing across three UI copies | Cosmetic, and would be redone by the PWA shell anyway | After M6 | LOW |
| PL-12 | Live Coinbase ordering (`broker.py` + `adapters/coinbase.py`) has never been exercised against the real API in this tree | Needs real keys and a decision in M7 | During M7 | MED |
| PL-13 | 2 TB NVMe upgrade available, not taken | Money, not engineering; 1 TB already sufficient | If model zoo or media ingestion outgrows 256 GB | LOW |
| PL-14 | `requirements.txt` still missing though README instructs its use | Trivially fixed, but belongs with install work | M9 | MED |
| PL-15 | Chroma directory is plaintext with no export path | Blocked behind M4/M5 auth and encryption decisions | During M5 | HIGH→promoted if lake holds health data before then |
| PL-16 | Behaviour when the tunnel drops: PWA offline handling, queued writes, stale cache of health data | Depends on the PWA existing | During M6 | MED |
| PL-17 | Mass rename of surviving modules to `jeeves_<domain>_<role>.py` (21 files plus every importer) | Renaming files that M6/M7 will delete is wasted diff; new files already conform | As a byproduct of the M6/M7 deletions, not as its own task | LOW |

**Not parked, deliberately:** the unauthenticated dashboard, the missing loss limit, the silent 8081
failures and the three coexisting crypto paths are mission-critical and live in `PROJECT-DELTA.md`
milestones M4, M7 and M8. The parking lot is for what is left after those.
