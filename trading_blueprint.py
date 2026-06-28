from flask import Blueprint, jsonify
import config
import mirror_engine

trading_bp = Blueprint('trading_bp', __name__)

@trading_bp.route('/trading_summary')
def trading_summary():
    try:
        with open(config.TRADING_STRATEGY_FILE) as f:
            return f.read().strip()
    except:
        return "No strategy file found."

@trading_bp.route('/trading_feedback')
def trading_feedback():
    import json
    entries = mirror_engine.read_feedback(config.TRADING_MIRROR_LOG, n=3)
    return json.dumps(entries)

@trading_bp.route('/trading_refine', methods=['POST'])
def trading_refine():
    llm = config.LLM_URL
    active = mirror_engine.trading_active_path()
    log = mirror_engine.trading_log_path()
    instruction = "You are a trading strategy editor. Revise the current strategy based on user feedback."
    proposed, error = mirror_engine.apply_feedback(log, active, llm, system_instruction=instruction, max_tokens=400, temperature=0.7)
    if error:
        return jsonify({"reply": f"Refinement failed: {error}"})
    if not proposed or not proposed.strip():
        return jsonify({"reply": "Refinement failed: the model returned an empty response. Please try again."})
    mirror_engine.confirm_apply(proposed, active, log)
    return jsonify({"reply": proposed})

@trading_bp.route('/trading_save', methods=['POST'])
def trading_save():
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.save_baseline(active, saved)
    return jsonify({"reply": msg})

@trading_bp.route('/trading_reload', methods=['POST'])
def trading_reload():
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    msg = mirror_engine.reload_baseline(saved, active)
    return jsonify({"reply": msg})

@trading_bp.route('/trading_reset', methods=['POST'])
def trading_reset():
    active = mirror_engine.trading_active_path()
    saved = mirror_engine.trading_saved_path()
    factory = mirror_engine.trading_factory_path()
    msg = mirror_engine.factory_reset(factory, active, saved)
    return jsonify({"reply": msg})
