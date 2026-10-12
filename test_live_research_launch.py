import urllib.request
import urllib.parse
import json
import time

import os
url = os.environ.get("ATLAS_BASE_URL", "http://127.0.0.1:8000") + "/api/research"
timestamp = int(time.time())
objective_text = f"Improve fraud detection on this dataset while improving recall without increasing false-positives ({timestamp})"

params = urllib.parse.urlencode({
    "objective": objective_text,
    "budget": 60,
    "llm_provider": "Heuristic / Rule-based",
    "max_experiments": 3
}).encode('utf-8')

req = urllib.request.Request(url, data=params, headers={
    'Content-Type': 'application/x-www-form-urlencoded'
})

print("Launching Fresh Live Autonomous Research Run...")
try:
    res = urllib.request.urlopen(req, timeout=60)
    print("LAUNCH HTTP STATUS:", res.status)
    body = res.read().decode('utf-8')
    data = json.loads(body)
    project_id = data.get("projectId")
    if not project_id:
        raise RuntimeError(f"Research launch returned no projectId: {data.get('error') or data}")
    print("LAUNCH RESPONSE SUCCESS:", data["success"])
    print("PROJECT ID:", project_id)
    print("STATUS UPON CREATION:", data["project"].get("status"))

    print("\nFetching updated project details...")
    proj_url = f"https://atlas-scientist.vercel.app/api/projects/{project_id}"
    p_res = urllib.request.urlopen(proj_url, timeout=30)
    p_data = json.loads(p_res.read().decode('utf-8'))
    print(f"Status: {p_data.get('status')}")
    print(f"Active Agent: {p_data.get('activeAgent')}")
    print(f"Experiments Executed: {p_data.get('experimentsCount')}")
    print(f"Best Model: {p_data.get('bestModel')}")
    print(f"Best Metric: {p_data.get('bestMetric')}")

    print("\nAgent Logs:")
    for log in p_data.get("agentLogs", []):
        print(f"  [{log.get('agent')}] {log.get('message')} ({log.get('status')})")

except urllib.error.HTTPError as he:
    print("LIVE RESEARCH LAUNCH TEST FAILED HTTPError:", he.code)
    print("ERROR BODY:", he.read().decode('utf-8'))
except Exception as e:
    print("LIVE RESEARCH LAUNCH TEST FAILED:", e)
