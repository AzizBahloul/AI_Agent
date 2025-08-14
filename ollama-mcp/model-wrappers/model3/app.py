from flask import Flask, request, jsonify
import os, requests, json

app = Flask(__name__)
OLLAMA = os.environ.get("OLLAMA_URL", "http://ollama3:11434")

SYSTEM_PROMPT = """
You are ACTION-VALIDATOR. Input is actions JSON. Validate:
- types and required keys present
- coordinates are integers or null
- image_template base64 valid if present
- add missing waits or retries if needed
Return strict JSON: { "validated_actions": [ ... ], "issues": [ ... ] }
"""

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json or {}
    actions = data.get("actions")
    if not actions:
        return jsonify({"error":"actions required"}), 400
    model_prompt = f"{SYSTEM_PROMPT}\nActions JSON:\n{json.dumps(actions)}\nReturn JSON."
    payload = {"model":"mistral:latest", "prompt": model_prompt, "max_tokens": 3000}
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=600)
    r.raise_for_status()
    text = r.text
    try:
        parsed = json.loads(text)
    except Exception:
        start = text.find("{"); end = text.rfind("}")
        parsed = json.loads(text[start:end+1])
    return jsonify(parsed)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
