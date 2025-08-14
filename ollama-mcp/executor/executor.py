from flask import Flask, request, jsonify
import os, json, base64, tempfile, time
import traceback

app = Flask(__name__)
ALLOW = os.environ.get("ALLOW_EXECUTION","false").lower() in ("1","true","yes")

# We import pyautogui and cv2 lazily to avoid requiring display in environments that don't need execution
def import_exec_libs():
    import pyautogui, cv2, numpy as np
    return pyautogui, cv2, np

def match_template_and_get_center(cv2, np, haystack_bgr, template_bgr):
    res = cv2.matchTemplate(haystack_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    th, tw = template_bgr.shape[1], template_bgr.shape[0]
    center_x = max_loc[0] + th//2
    center_y = max_loc[1] + tw//2
    return center_x, center_y, max_val

@app.route("/execute", methods=["POST"])
def execute():
    payload = request.json or {}
    validated = payload.get("validated")
    if not validated:
        return jsonify({"error":"validated required"}),400
    actions = validated.get("validated_actions") or validated.get("actions") or []
    # Compose a dry-run response first
    dry_run = []
    for a in actions:
        dry_run.append({"id": a.get("id"), "type": a.get("type"), "x": a.get("x"), "y": a.get("y")})

    # If not allowed to execute, return a dry run
    if not ALLOW:
        return jsonify({"executed": False, "dry_run": dry_run, "note":"ALLOW_EXECUTION is false in executor env"}), 200

    # Now perform execution
    try:
        pyautogui, cv2, np = import_exec_libs()
    except Exception as e:
        return jsonify({"error":"missing execution libs or display","exc":str(e)}), 500

    results = []
    try:
        screen = pyautogui.screenshot()
        screen_np = np.array(screen)[:,:,::-1]  # rgb->bgr for OpenCV
        for a in actions:
            typ = a.get("type")
            if typ == "wait":
                dur = float(a.get("duration", 0.5))
                time.sleep(dur)
                results.append({"id":a.get("id"), "status":"waited"})
            elif typ in ("move","click"):
                x = a.get("x")
                y = a.get("y")
                if x is None or y is None:
                    # attempt template match
                    img_b64 = a.get("image_template")
                    if not img_b64:
                        results.append({"id":a.get("id"), "status":"failed","reason":"no coords or template"})
                        continue
                    tmp = base64.b64decode(img_b64)
                    tmp_arr = np.frombuffer(tmp, dtype=np.uint8)
                    template = cv2.imdecode(tmp_arr, cv2.IMREAD_COLOR)
                    cx, cy, conf = match_template_and_get_center(cv2, np, screen_np, template)
                    x, y = int(cx), int(cy)
                    results.append({"id":a.get("id"), "matched_conf":float(conf), "x":x, "y":y})
                # move and click per type
                duration = float(a.get("duration", 0.2))
                pyautogui.moveTo(x, y, duration=duration)
                if typ == "click":
                    pyautogui.click()
                    results.append({"id":a.get("id"), "status":"clicked","x":x,"y":y})
                else:
                    results.append({"id":a.get("id"), "status":"moved","x":x,"y":y})
            elif typ == "type":
                text = a.get("text","")
                pyautogui.write(text, interval=0.02)
                results.append({"id":a.get("id"), "status":"typed", "text_preview": text[:100]})
            elif typ == "screenshot":
                fname = f"/tmp/executor_screenshot_{int(time.time())}.png"
                pyautogui.screenshot(fname)
                results.append({"id":a.get("id"), "status":"screenshot_saved","path":fname})
            else:
                results.append({"id":a.get("id"), "status":"unknown_type"})
        return jsonify({"executed": True, "results": results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":"exception during execute","exc":str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
