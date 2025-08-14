from flask import Flask, request, jsonify
import os, requests, json

app = Flask(__name__)
OLLAMA = os.environ.get("OLLAMA_URL", "http://ollama2:11434")

SYSTEM_PROMPT = """
You are UI-ACTION-PLANNER. Input: the analysis JSON (tasks). Output: strict JSON list "actions" ordered to perform.
Action schema:
{
 "actions": [
   { "id":1, "type":"click"|"move"|"type"|"screenshot"|"wait", 
     "x": <int|null>, "y": <int|null>, 
     "image_template": <base64 string|null>, 
     "text": <string|null>, "duration": <float|null>,
     "notes": <string|null>
   }
 ]
}
Rules:
- If you know exact coordinates, fill x and y.
- If you can't know exact coords, provide an "image_template" to be matched by the executor (base64 PNG).
- Prefer templates for robustness.
Return JSON only.
"""

@app.route("/plan", methods=["POST"])
def plan():
    data = request.json or {}
    tasks = data.get("analysis")
    if not tasks:
        return jsonify({"error":"analysis required"}), 400
    user_prompt = data.get("prompt","")
    model_prompt = f"{SYSTEM_PROMPT}\nAnalysis JSON:\n{json.dumps(tasks)}\nUser prompt:\n{user_prompt}\nReturn JSON actions."
    payload = {"model":"codellama:code", "prompt": model_prompt, "max_tokens": 4000}
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
