"""Live Section 8 RAG Benchmark Test against Production Atlas Deployment.
Tests:
1. Ingestion of Document A (Atlas Orion) & Document B (Atlas Neptune) via POST /api/files
2. Query 1: Orion verification code (ORION-8426)
3. Query 2: Neptune location (Titan)
4. Query 3: Compare the projects (both Orion and Neptune)
5. Query 4: Orion annual budget (honest refusal)
6. Cascading deletion of Document A via DELETE /api/files/{id}
7. Cross-session isolation
"""

import json
import urllib.request
import urllib.error
import uuid
import sys

BASE_URL = "https://atlas-scientist.vercel.app"
session_id = f"s8-{uuid.uuid4().hex[:12]}"
cookie_header = f"atlas_sid={session_id}"

print(f"Target Production: {BASE_URL}")
print(f"Test Session ID: {session_id}\n")

def upload_file(filename: str, text_content: str):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    content_bytes = text_content.encode("utf-8")
    
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header + content_bytes + footer
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/files",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": cookie_header
        }
    )
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode("utf-8"))

# 1. Ingest Document A
doc_a = upload_file(
    "atlas_orion.txt",
    "Project: Atlas Orion\nVerification code: ORION-8426\nLocation: Mars"
)
print(f"1. Ingest Doc A (atlas_orion.txt): {doc_a}")
doc_a_id = doc_a.get("id")
assert doc_a_id, "Missing doc_a id"

# 2. Ingest Document B
doc_b = upload_file(
    "atlas_neptune.txt",
    "Project: Atlas Neptune\nVerification code: NEPTUNE-5931\nLocation: Titan"
)
print(f"2. Ingest Doc B (atlas_neptune.txt): {doc_b}\n")
doc_b_id = doc_b.get("id")
assert doc_b_id, "Missing doc_b id"

def ask(query: str) -> str:
    payload = json.dumps({"message": query}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie_header
        }
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")

# 3. Query 1: What is Orion's verification code?
print("Query 1: 'What is Orion\\'s verification code?'")
ans1 = ask("What is Orion's verification code?")
print(f"Response:\n{ans1}\n")
assert "ORION-8426" in ans1 or "8426" in ans1, "Failed Q1: ORION-8426 not found"
print(">>> Q1 PASSED\n")

# 4. Query 2: Where is Neptune located?
print("Query 2: 'Where is Neptune located?'")
ans2 = ask("Where is Neptune located?")
print(f"Response:\n{ans2}\n")
assert "Titan" in ans2, "Failed Q2: Titan not found"
print(">>> Q2 PASSED\n")

# 5. Query 3: Compare the projects.
print("Query 3: 'Compare the projects.'")
ans3 = ask("Compare the projects.")
print(f"Response:\n{ans3}\n")
assert "Orion" in ans3 and "Neptune" in ans3, "Failed Q3: Orion and Neptune not both mentioned"
print(">>> Q3 PASSED\n")

# 6. Query 4: What is Orion's annual budget?
print("Query 4: 'What is Orion\\'s annual budget?'")
ans4 = ask("What is Orion's annual budget?")
print(f"Response:\n{ans4}\n")
refusal_terms = ["not mentioned", "not provided", "does not contain", "unspecified", "not specified", "no information"]
assert any(m in ans4.lower() for m in refusal_terms), "Failed Q4: Did not refuse missing budget info"
print(">>> Q4 PASSED (Honest Refusal)\n")

# 7. Cascading Deletion of Document A
print(f"7. Deleting Document A (id={doc_a_id})...")
del_req = urllib.request.Request(
    f"{BASE_URL}/api/files/{doc_a_id}",
    method="DELETE",
    headers={"Cookie": cookie_header}
)
with urllib.request.urlopen(del_req, timeout=20) as r:
    del_res = json.loads(r.read().decode("utf-8"))
print(f"Delete response: {del_res}")

list_req = urllib.request.Request(
    f"{BASE_URL}/api/files",
    headers={"Cookie": cookie_header}
)
with urllib.request.urlopen(list_req, timeout=20) as r:
    list_res = json.loads(r.read().decode("utf-8"))
doc_list = list_res.get("documents", [])
remaining_ids = [d["id"] for d in doc_list]
print(f"Remaining doc filenames: {[d['filename'] for d in doc_list]}")
assert doc_a_id not in remaining_ids, "Failed: Document A still present after delete"
assert doc_b_id in remaining_ids, "Failed: Document B missing"
print(">>> Cascading Deletion PASSED\n")

# 8. Cross-Session Isolation
other_session = f"s8-other-{uuid.uuid4().hex[:12]}"
print(f"8. Testing isolation with unassociated session: {other_session}")
list_req_other = urllib.request.Request(
    f"{BASE_URL}/api/files",
    headers={"Cookie": f"atlas_sid={other_session}"}
)
with urllib.request.urlopen(list_req_other, timeout=20) as r:
    list_other_res = json.loads(r.read().decode("utf-8"))
other_docs = list_other_res.get("documents", [])
print(f"Other session document count: {len(other_docs)}")
assert len(other_docs) == 0, "Failed: Documents leaked across sessions"
print(">>> Cross-Session Isolation PASSED\n")

print("==================================================")
print("ALL SECTION 8 PRODUCTION BENCHMARK TESTS PASSED!")
print("==================================================")
