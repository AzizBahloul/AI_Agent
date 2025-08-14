from flask import Flask, request, jsonify
import os, requests, json, textwrap

app = Flask(__name__)
OLLAMA = os.environ.get("OLLAMA_URL", "http://ollama1:11434")

SYSTEM_PROMPT = """
You are TASK-ANALYZER. Given a user prompt, break it into an ordered list of atomic tasks
required to accomplish the user's request on a desktop UI. Return strict JSON only, with schema:
{ "tasks": [ {"id": 1, "description": "open browser", "notes": "...", "priority": 1 }, ... ] }
Do not return any text outside JSON. If ambiguous, include a "clarify" task first.
"""

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error":"prompt required"}), 400

    # Build the prompt for the model
    model_prompt = f"{SYSTEM_PROMPT}\nUser prompt:\n{prompt}\nReturn JSON."
    payload = {"model":"llama3.2", "prompt": model_prompt, "max_tokens": 8000, "stream": False}
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=600)
    r.raise_for_status()
    text = r.text
    # Ollama returns streaming newline-delimited chunks sometimes; attempt to parse JSON
    try:
        # Some Ollama clients return the JSON as plain text body
        parsed = json.loads(text)
    except Exception:
        # try to extract first {...}
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return jsonify({"error":"invalid model output","raw":text}), 500
        parsed = json.loads(text[start:end+1])
    return jsonify(parsed)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
