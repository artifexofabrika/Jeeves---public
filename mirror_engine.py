import os, datetime, json, requests, shutil
import config

# ──────────────────────────────────────────────
# Factory default helpers
# ──────────────────────────────────────────────
def _ensure_factory(active_path, factory_path):
    """If no factory file exists, copy the current active file as factory default."""
    if not os.path.exists(factory_path) and os.path.exists(active_path):
        shutil.copy(active_path, factory_path)

# ──────────────────────────────────────────────
# Feedback logging / reading
# ──────────────────────────────────────────────
def log_feedback(log_path, note):
    timestamp = datetime.datetime.now().isoformat()
    os.makedirs(os.path.dirname(log_path) or '.', exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{timestamp} | {note}\n")

def read_feedback(log_path, n=3):
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r") as f:
        lines = [line.strip() for line in f.readlines()[-n:] if line.strip()]
    return lines

def clear_feedback(log_path):
    if os.path.exists(log_path):
        open(log_path, "w").close()

# ──────────────────────────────────────────────
# Version‑control actions (persona & strategy)
# ──────────────────────────────────────────────
def save_baseline(active_path, saved_path):
    """Copy active → saved (create a checkpoint)."""
    if os.path.exists(active_path):
        shutil.copy(active_path, saved_path)
        return "Baseline saved, sir."
    return "Active file not found."

def reload_baseline(saved_path, active_path):
    """Copy saved → active (restore the checkpoint)."""
    if os.path.exists(saved_path):
        shutil.copy(saved_path, active_path)
        return "Saved baseline restored, sir."
    return "No saved baseline exists."

def factory_reset(factory_path, active_path, saved_path):
    """Restore the immutable factory default, overwriting active and saved."""
    _ensure_factory(active_path, factory_path)
    if os.path.exists(factory_path):
        shutil.copy(factory_path, active_path)
        shutil.copy(factory_path, saved_path)
        return "Factory default restored, sir."
    return "Factory default not available."

# ──────────────────────────────────────────────
# LLM‑based refinement (used by Mirror Apply)
# ──────────────────────────────────────────────
def apply_feedback(log_path, active_path, llm_url, system_instruction="",
                   max_tokens=400, temperature=0.7):
    """Read feedback, ask LLM to revise the active file, return proposed text."""
    entries = read_feedback(log_path)
    if not entries:
        return None, "No feedback to apply."
    feedback_text = "\n".join(entries)
    if not os.path.exists(active_path):
        return None, "Active file not found."
    current_text = open(active_path).read().strip()

    prompt = f"""{system_instruction}
Current text:
{current_text}

User feedback:
{feedback_text}

Produce a revised version that incorporates the feedback while preserving the original tone and purpose. Output ONLY the revised text, nothing else."""
    try:
        resp = requests.post(llm_url, json={
            "model": "llama",
            "messages": [{"role":"user","content":prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }, timeout=90)
        if resp.ok:
            new_text = resp.json()["choices"][0]["message"]["content"].strip()
            return new_text, None
        else:
            return None, f"LLM request failed: {resp.status_code}"
    except Exception as e:
        return None, f"Error: {e}"

def confirm_apply(proposed_text, active_path, log_path):
    """Write the proposed text to the active file and clear the feedback log."""
    with open(active_path, "w") as f:
        f.write(proposed_text)
    clear_feedback(log_path)
    return "Applied, sir. Feedback log cleared."

# ──────────────────────────────────────────────
# Convenience wrappers for Persona
# ──────────────────────────────────────────────
def persona_factory_path():
    return os.path.expanduser("~/persona_factory.txt")

def persona_saved_path():
    return os.path.expanduser("~/persona_saved.txt")

def persona_active_path():
    return config.PERSONA_FILE

def persona_log_path():
    return config.MIRROR_LOG

# ──────────────────────────────────────────────
# Convenience wrappers for Crypto Strategy
# ──────────────────────────────────────────────
def crypto_factory_path():
    return os.path.expanduser("~/crypto_strategy_factory.txt")

def crypto_saved_path():
    return os.path.expanduser("~/crypto_strategy_saved.txt")

def crypto_active_path():
    return config.CRYPTO_STRATEGY_FILE

def crypto_log_path():
    return config.CRYPTO_MIRROR_LOG

# ──────────────────────────────────────────────
# Convenience wrappers for Trading Strategy (Stocks)
# ──────────────────────────────────────────────
def trading_factory_path():
    return os.path.expanduser("~/trading_strategy_factory.txt")

def trading_saved_path():
    return os.path.expanduser("~/trading_strategy_saved.txt")

def trading_active_path():
    return config.TRADING_STRATEGY_FILE

def trading_log_path():
    return config.TRADING_MIRROR_LOG
