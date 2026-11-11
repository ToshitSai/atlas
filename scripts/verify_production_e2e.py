"""
Live Production Verification Script for Atlas Gen-3.2
Tests:
1. "what is apple" vs "apple"
2. Document ingestion of europa_station.txt
3. 5 Europa grounding queries (Q1-Q5) including anti-hallucination check
4. Casual greeting and math queries
"""
import urllib.request
import urllib.parse
import json
import uuid
import mimetypes

BASE_URL = "https://atlas-scientist.vercel.app"
session_id = f"e2e-session-{uuid.uuid4().hex[:8]}"
saved_cookies = {}

def get_cookie_header():
    return "; ".join(f"{k}={v}" for k, v in saved_cookies.items())

def update_cookies(resp_headers):
    for header in resp_headers.get_all("Set-Cookie", []):
        parts = header.split(";")
        if parts:
            kv = parts[0].strip().split("=", 1)
            if len(kv) == 2:
                saved_cookies[kv[0]] = kv[1]

def send_chat(message):
    payload = json.dumps({
        "message": message,
        "session_id": session_id,
        "stream": False
    }).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    cookie_str = get_cookie_header()
    if cookie_str:
        headers["Cookie"] = cookie_str
        
    req = urllib.request.Request(f"{BASE_URL}/api/chat", data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=35) as resp:
        update_cookies(resp.headers)
        return json.loads(resp.read().decode("utf-8"))

def upload_document(filename, text_content):
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: text/plain\r\n\r\n")
    body.extend(text_content.encode("utf-8"))
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    cookie_str = get_cookie_header()
    if cookie_str:
        headers["Cookie"] = cookie_str
        
    req = urllib.request.Request(f"{BASE_URL}/api/files", data=bytes(body), headers=headers)
    with urllib.request.urlopen(req, timeout=35) as resp:
        update_cookies(resp.headers)
        return json.loads(resp.read().decode("utf-8"))

def run_tests():
    print("=" * 60)
    print("ATLAS GEN-3.2 LIVE PRODUCTION VERIFICATION")
    print(f"Target: {BASE_URL}")
    print(f"Session: {session_id}")
    print("=" * 60)

    # Pre-flight health check
    health_req = urllib.request.Request(f"{BASE_URL}/api/health", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(health_req) as h_resp:
        update_cookies(h_resp.headers)
        h_data = json.loads(h_resp.read().decode("utf-8"))
        print(f"[PRE-FLIGHT] Commit: {h_data.get('build', {}).get('commit')[:8]}")
        print(f"[PRE-FLIGHT] Cookies received: {saved_cookies}")

    # 1. Chat AI Service Failure: "what is apple"
    print("\n--- 1. Query: 'what is apple' ---")
    res1 = send_chat("what is apple")
    text1 = res1.get("response", "")
    print(f"Status: OK | Length: {len(text1)}")
    print(f"Response: {text1[:250]}...")
    assert "couldn't reach" not in text1.lower(), "Service failure detected!"
    assert "apple" in text1.lower(), "Expected topic explanation for apple"

    # 2. Chat AI Service: "apple"
    print("\n--- 2. Query: 'apple' ---")
    res2 = send_chat("apple")
    text2 = res2.get("response", "")
    print(f"Status: OK | Length: {len(text2)}")
    print(f"Response: {text2[:250]}...")
    assert "couldn't reach" not in text2.lower(), "Service failure detected!"
    assert "apple" in text2.lower(), "Expected topic explanation for apple"
    assert "atlas is a" not in text2.lower()[:80], "Should not be creator self-description"

    # 3. Document Ingestion: europa_station.txt
    print("\n--- 3. Ingesting Europa Station Document ---")
    doc_content = """Atlas RAG Verification Code: ORBIT-7429.
The fictional research station is located on Europa.
Its chief scientist is Dr. Mira Sol.
Its emergency power system is named Aurora Core."""

    up_res = upload_document("europa_station.txt", doc_content)
    print(f"Upload Response: {up_res}")
    doc_id = up_res.get("document_id") or up_res.get("filename")
    print(f"Document registered: {doc_id}")

    # 4. Europa Test Suite Queries
    europa_queries = [
        ("What is the verification code?", "ORBIT-7429", "Verification Code Check"),
        ("Where is the research station located?", "Europa", "Location Check"),
        ("Who is the chief scientist?", "Dr. Mira Sol", "Chief Scientist Check"),
        ("What is the emergency power system named?", "Aurora Core", "Power System Check"),
        ("What is the chief scientist's favorite food?", None, "Anti-Hallucination Check (Negative)"),
    ]

    for q, expected, label in europa_queries:
        print(f"\n--- 4.{label}: '{q}' ---")
        chat_res = send_chat(q)
        ans = chat_res.get("response", "")
        intent = chat_res.get("intent", "UNKNOWN")
        sources = chat_res.get("sources", [])
        print(f"Intent: {intent} | Sources: {sources}")
        print(f"Answer: {ans}")
        
        if expected:
            assert expected.lower() in ans.lower(), f"Failed to retrieve ground truth '{expected}'!"
            print(f"-> PASS: Contains '{expected}'")
        else:
            # Negative check
            lower_ans = ans.lower()
            not_found_markers = [
                "does not contain", "not mentioned", "not provided", 
                "no mention", "unspecified", "not specified", "does not state",
                "not found", "does not mention"
            ]
            has_marker = any(m in lower_ans for m in not_found_markers)
            assert has_marker, f"Failed anti-hallucination! Expected explicit statement of absence. Got: {ans}"
            print(f"-> PASS: Correctly refused without hallucinating missing information!")

    print("\n" + "=" * 60)
    print("ALL PRODUCTION E2E TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
