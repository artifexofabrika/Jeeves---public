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
        all_feedback = "\n".join([e.strip().split(" | ", 1)[-1] for e in entries if " | " in e])
        current_prompt = open(PERSONA_FILE).read().strip()
        prompt = f"You are a persona editor. The current persona is:\n{current_prompt}\n\nThe user has given the following feedback, each on a separate line. Please revise the persona to incorporate every piece of feedback while preserving its core character. The new persona should be comprehensive and specific, not a single sentence. Output ONLY the revised persona text, with no introductory or concluding remarks.\n\nFeedback:\n{all_feedback}"
        resp = requests.post(LLM_URL, json={
            "model": "llama",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, "max_tokens": 300
        }, timeout=90)
        if resp.ok:
            new_prompt = resp.json()["choices"][0]["message"]["content"].strip()
            with open(PERSONA_FILE, "w") as f:
                f.write(new_prompt)
            # Clear the mirror log
            with open(MIRROR_LOG, "w") as f:
                f.write("")
            # Restart services
            subprocess.run(["sudo", "systemctl", "restart", "jeeves-web"])
            subprocess.run(["sudo", "pkill", "-9", "-f", "jeeves_telegram.py"])
            subprocess.run(["nohup", "python3", os.path.expanduser("~/jeeves_telegram.py"), ">", "/dev/null", "2>&1", "&"])
            return jsonify({"reply": f"Persona refined and updated, sir.\n\nNew persona:\n{new_prompt}"})
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
            return jsonify({"reply": "No saved default found. Use Factory Reset to return to the original Jeeves."})
    except Exception as e:
        return jsonify({"reply": f"Error reloading saved: {e}"})

@app.route('/factory_reset', methods=['POST'])
def factory_reset():
    factory = "You are Jeeves, a calm, erudite personal valet. You respond with concise, direct answers. When asked for suggestions or lists, limit them to 3-5 items maximum. Never print a wall of text. Use dry wit sparingly. You address the user as \"sir\" with restrained warmth, and you may gently challenge unsound decisions."
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
