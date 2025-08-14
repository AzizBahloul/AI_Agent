from flask import Flask, request, jsonify
import os, requests, json, time

app = Flask(__name__)
MODEL1_URL = os.environ.get("MODEL1_URL","http://model1-wrapper:5000")
MODEL2_URL = os.environ.get("MODEL2_URL","http://model2-wrapper:5000")
MODEL3_URL = os.environ.get("MODEL3_URL","http://model3-wrapper:5000")
EXECUTOR_URL = os.environ.get("EXECUTOR_URL","http://executor:5001")

@app.route("/run", methods=["POST"])
def run_pipeline():
    body = request.json or {}
    prompt = body.get("prompt","")
    execute = bool(body.get("execute", False))
    if not prompt:
        return jsonify({"error":"prompt required"}),400

    # 1) Model1 analyze
    r1 = requests.post(f"{MODEL1_URL}/analyze", json={"prompt":prompt}, timeout=120)
    r1.raise_for_status()
    analysis = r1.json()

    # 2) Model2 plan
    r2 = requests.post(f"{MODEL2_URL}/plan", json={"analysis":analysis, "prompt":prompt}, timeout=600)
    r2.raise_for_status()
    plan = r2.json()

    # 3) Model3 validate
    r3 = requests.post(f"{MODEL3_URL}/validate", json={"actions": plan.get("actions", plan)}, timeout=120)
    r3.raise_for_status()
    validated = r3.json()

    response = {
        "analysis": analysis,
        "plan": plan,
        "validated": validated
    }

    if execute:
        # send to executor for dry-run or execution
        ex = requests.post(f"{EXECUTOR_URL}/execute", json={"validated": validated, "prompt": prompt}, timeout=300)
        ex.raise_for_status()
        response["executor_result"] = ex.json()

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
