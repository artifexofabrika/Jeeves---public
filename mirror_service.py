import os, subprocess, requests, json
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MIRROR_LOG = os.path.expanduser("~/mirror.log")
PERSONA_FILE = os.path.expanduser("~/jeeves_persona.txt")
DEFAULT_FILE = os.path.expanduser("~/jeeves_persona_default.txt")
LLM_URL = "http://localhost:8080/v1/chat/completions"

@app.route('/refine_persona', methods=['POST'])
def refine_persona():
    try:
        with open(MIRROR_LOG, "r") as f:
            entries = f.readlines()
        if not entries:
            return jsonify({"reply": "The Mirror is empty, sir. No feedback to refine."})
        last_feedback = entries[-1].strip()
        core_prompt = open(os.path.expanduser("~/jeeves_core_prompt.txt")).read().strip()
        change_log = open(os.path.expanduser("~/jeeves_change_log.txt")).read().strip()
        prompt = f"You are a meticulous persona editor. The locked core persona is:\n\n{core_prompt}\n\nThe current change log is:\n\n{change_log}\n\nThe user has given this feedback:\n\n{last_feedback}\n\nYour task is to produce a revised change log entry (one or two sentences) that incorporates the feedback. Do NOT modify the core persona. The change log should contain ONLY specific modifications, such as 'address me as master' or 'prefer a warmer tone in the mornings'. Output ONLY the revised change log text, nothing else."
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, "max_tokens": 150
        }, timeout=60)
        if resp.ok:
            new_changes = resp.json()["choices"][0]["message"]["content"].strip()
            # Write the new change log
            with open(os.path.expanduser("~/jeeves_change_log.txt"), "w") as f:
                f.write(new_changes)
            # Rebuild the persona file
            persona = core_prompt + "\n\n" + new_changes if new_changes else core_prompt
            with open(PERSONA_FILE, "w") as f:
                f.write(persona.strip())
            # Clear the mirror log
            with open(MIRROR_LOG, "w") as f:
                f.write("")
            # Restart services
            subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
            subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
            subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
            return jsonify({"reply": f"Persona updated, sir. Change log now: {new_changes}"})
        else:
            return jsonify({"reply": "I am unable to refine the persona at the moment, sir."})
    except Exception as e:
        return jsonify({"reply": f"Error: {e}"})
@app.route('/save_default', methods=['POST'])
def save_default():
    try:
        current = open(PERSONA_FILE).read().strip()
        with open(DEFAULT_FILE, "w") as f:
            f.write(current)
        return jsonify({"reply": "Current persona saved as your personal default, sir."})
    except Exception as e:
        return jsonify({"reply": f"Error saving default: {e}"})

@app.route('/reload_saved', methods=['POST'])
def reload_saved():
    try:
        if os.path.exists(DEFAULT_FILE):
            with open(DEFAULT_FILE, "r") as f:
                saved = f.read().strip()
            with open(PERSONA_FILE, "w") as f:
                f.write(saved)
            subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
            subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
            subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
            return jsonify({"reply": "Your saved persona has been restored, sir."})
        else:
            return jsonify({"reply": "No saved default found. Use Factory Reset to return to the original " + config.AI_NAME + "."})
    except Exception as e:
        return jsonify({"reply": f"Error reloading saved: {e}"})

@app.route('/factory_reset', methods=['POST'])
def factory_reset():
    factory = "You are a helpful AI assistant. Answer questions clearly and concisely."
    try:
        with open(PERSONA_FILE, "w") as f:
            f.write(factory)
        if os.path.exists(DEFAULT_FILE):
            os.remove(DEFAULT_FILE)
        subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
        subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
        subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
        return jsonify({"reply": "Factory persona restored, sir. Your saved default (if any) has been removed."})
    except Exception as e:
        return jsonify({"reply": f"Error during factory reset: {e}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
