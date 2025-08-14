from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)
ORCH = os.environ.get("ORCH_URL","http://orchestrator:8000")

@app.route("/submit", methods=["POST"])
def submit():
    d = request.json or {}
    prompt = d.get("prompt")
    execute = bool(d.get("execute", False))
    r = requests.post(f"{ORCH}/run", json={"prompt":prompt, "execute": execute}, timeout=600)
    return (r.text, r.status_code, r.headers.items())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
