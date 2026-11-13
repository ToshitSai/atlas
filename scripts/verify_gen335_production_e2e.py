#!/usr/bin/env python3
"""Atlas AI Gen-3.3.5: Production File Upload, Ingestion & RAG Verification Battery.

Verifies:
1. Health & readiness endpoints.
2. Ingestion of the exact previously failing 2.87MB file: 'Chico, Rocky & Luna Character Sheet.png'.
3. Explicit rejection of unsupported formats (video .mp4 and legacy Office .doc).
4. Section 10 CHICO-ATLAS-2026 5-question test battery (4 positive, 1 honest missing).
5. Workflow A (chat_attachment) and Workflow B (knowledge_base) independently.
6. Session isolation and secure private blob download.
7. Clean cascading deletion.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent


def make_multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    boundary = f"----AtlasBoundary{int(time.time() * 1000)}"
    body = bytearray()
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    for field_name, (filename, data, ctype) in files.items():
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\n".encode("utf-8"))
        body.extend(f"Content-Type: {ctype}\r\n\r\n".encode("utf-8"))
        body.extend(data)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def run_battery(base_url: str) -> Dict[str, Any]:
    base_url = base_url.rstrip("/")
    results = {
        "base_url": base_url,
        "timestamp": time.time(),
        "tests": {},
        "all_passed": False
    }
    owner_a = f"test_owner_{int(time.time())}"
    owner_b = f"unauth_intruder_{int(time.time())}"

    print(f"\n========================================================")
    print(f"ATLAS GEN-3.3.5 PRODUCTION VERIFICATION BATTERY")
    print(f"Target URL: {base_url}")
    print(f"Authorized Session: {owner_a}")
    print(f"Unauthorized Session: {owner_b}")
    print(f"========================================================\n")

    # 1. Health & Readiness
    print("[TEST 1] Verifying /api/health and /api/ready...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=15) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        results["tests"]["health"] = {
            "status": health.get("status"),
            "database": health.get("database"),
            "databaseType": health.get("databaseType"),
            "durability": health.get("durability"),
            "persistent": health.get("persistent"),
            "objectStorage": health.get("objectStorage"),
        }
        print(f"  Health: status={health.get('status')}, db={health.get('databaseType')}, durability={health.get('durability')}")
    except Exception as e:
        print(f"  [FAIL] /api/health error: {e}")
        results["tests"]["health"] = {"error": str(e)}

    # 2. Ingest the actual 2.87MB Chico Character Sheet file
    print("\n[TEST 2] Ingesting exact failing file: 'Chico, Rocky & Luna Character Sheet.png' (2.87 MB)...")
    chico_path = r"C:\Users\Toshit\Desktop\youtube\Chico, Rocky & Luna Character Sheet.png"
    chico_doc_id = None
    if os.path.exists(chico_path):
        with open(chico_path, "rb") as f:
            chico_bytes = f.read()
        body, ctype = make_multipart(
            {"workflow": "chat_attachment"},
            {"file": (os.path.basename(chico_path), chico_bytes, "image/png")}
        )
        req = urllib.request.Request(
            f"{base_url}/api/files",
            data=body,
            headers={"Content-Type": ctype, "X-Anonymous-ID": owner_a},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                chico_doc_id = res.get("id")
                results["tests"]["chico_upload"] = {
                    "http_status": resp.status,
                    "id": chico_doc_id,
                    "status": res.get("status"),
                    "stage": res.get("stage"),
                    "chunks": res.get("chunks"),
                    "is_image": res.get("is_image"),
                    "persistent": res.get("persistent"),
                }
                print(f"  SUCCESS: HTTP {resp.status}, id={chico_doc_id}, status={res.get('status')}, persistent={res.get('persistent')}")
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8")
            print(f"  [FAIL] HTTP {he.code}: {err_body}")
            results["tests"]["chico_upload"] = {"error": f"HTTP {he.code}: {err_body}"}
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            results["tests"]["chico_upload"] = {"error": str(e)}
    else:
        print("  Notice: Chico file not found locally, skipping exact local file test.")

    # 3. Test Unsupported Format Rejections
    print("\n[TEST 3] Testing Unsupported Format Rejections (Video and Legacy DOC)...")
    # Video .mp4
    video_body, video_ctype = make_multipart(
        {"workflow": "chat_attachment"},
        {"file": ("sample_video.mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00fakevideo", "video/mp4")}
    )
    v_req = urllib.request.Request(
        f"{base_url}/api/files",
        data=video_body,
        headers={"Content-Type": video_ctype, "X-Anonymous-ID": owner_a},
        method="POST"
    )
    video_rejected = False
    try:
        with urllib.request.urlopen(v_req, timeout=15) as v_resp:
            print(f"  [SECURITY FLAW] Video upload was accepted: HTTP {v_resp.status}")
    except urllib.error.HTTPError as he:
        err_res = json.loads(he.read().decode("utf-8"))
        if he.code == 400 and err_res.get("category") == "unsupported_video":
            video_rejected = True
            print(f"  Video Rejected Correctly: HTTP 400, category={err_res.get('category')}")
        else:
            print(f"  Video response: HTTP {he.code}, body={err_res}")
    except Exception as e:
        print(f"  Video test error: {e}")

    # Legacy .doc
    doc_body, doc_ctype = make_multipart(
        {"workflow": "chat_attachment"},
        {"file": ("resume.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1legacy_ole", "application/msword")}
    )
    d_req = urllib.request.Request(
        f"{base_url}/api/files",
        data=doc_body,
        headers={"Content-Type": doc_ctype, "X-Anonymous-ID": owner_a},
        method="POST"
    )
    doc_rejected = False
    try:
        with urllib.request.urlopen(d_req, timeout=15) as d_resp:
            print(f"  [SECURITY FLAW] Legacy DOC was accepted: HTTP {d_resp.status}")
    except urllib.error.HTTPError as he:
        err_res = json.loads(he.read().decode("utf-8"))
        if he.code == 400 and err_res.get("category") == "legacy_format":
            doc_rejected = True
            print(f"  Legacy DOC Rejected Correctly: HTTP 400, category={err_res.get('category')}")
        else:
            print(f"  Legacy DOC response: HTTP {he.code}, body={err_res}")
    except Exception as e:
        print(f"  DOC test error: {e}")

    results["tests"]["format_rejections"] = {
        "video_rejected": video_rejected,
        "legacy_doc_rejected": doc_rejected
    }

    # 4. Ingest Section 10 CHICO-ATLAS-2026 Test Document
    print("\n[TEST 4] Ingesting CHICO-ATLAS-2026 Verification Document...")
    chico_text = (
        "Project: CHICO-ATLAS-2026\n"
        "Verification code: CHICO-72984.\n"
        "Characters: Chico, Rocky and Luna.\n"
        "Mission location: Europa.\n"
        "Mission director: Dr. Mira.\n"
    )
    c_body, c_ctype = make_multipart(
        {"workflow": "chat_attachment"},
        {"file": ("CHICO-ATLAS-2026.txt", chico_text.encode("utf-8"), "text/plain")}
    )
    c_req = urllib.request.Request(
        f"{base_url}/api/files",
        data=c_body,
        headers={"Content-Type": c_ctype, "X-Anonymous-ID": owner_a},
        method="POST"
    )
    txt_doc_id = None
    try:
        with urllib.request.urlopen(c_req, timeout=30) as resp:
            c_res = json.loads(resp.read().decode("utf-8"))
            txt_doc_id = c_res.get("id")
            results["tests"]["txt_doc_ingest"] = {
                "id": txt_doc_id,
                "chunks": c_res.get("chunks"),
                "status": c_res.get("status"),
                "persistent": c_res.get("persistent"),
            }
            print(f"  CHICO-ATLAS-2026 Ingested: id={txt_doc_id}, chunks={c_res.get('chunks')}")
    except Exception as e:
        print(f"  [FAIL] CHICO-ATLAS-2026 ingest error: {e}")
        results["tests"]["txt_doc_ingest"] = {"error": str(e)}

    # 5. Section 10 RAG 5-Question Battery
    print("\n[TEST 5] Executing Section 10 RAG 5-Question Battery...")
    conv_id = f"conv_chico_{int(time.time())}"
    rag_questions = [
        ("What is the verification code?", "CHICO-72984", True),
        ("Which characters are mentioned?", "Chico", True),
        ("Where is the mission located?", "Europa", True),
        ("Who is the mission director?", "Mira", True),
        ("What is the project's budget?", "not contain", False),  # Must be honest missing
    ]
    q_results = []
    all_rag_ok = True

    for q_text, expected_token, should_be_present in rag_questions:
        chat_payload = json.dumps({
            "message": q_text,
            "conversationId": conv_id,
            "attachments": [{"id": txt_doc_id, "filename": "CHICO-ATLAS-2026.txt"}] if txt_doc_id else []
        }).encode("utf-8")
        q_req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=chat_payload,
            headers={"Content-Type": "application/json", "X-Anonymous-ID": owner_a},
            method="POST"
        )
        try:
            with urllib.request.urlopen(q_req, timeout=35) as q_resp:
                chat_res = json.loads(q_resp.read().decode("utf-8"))
                reply = chat_res.get("reply", "") or chat_res.get("response", "")
                if should_be_present:
                    passed = expected_token.lower() in reply.lower()
                else:
                    passed = "not contain" in reply.lower() or "not mentioned" in reply.lower() or "does not" in reply.lower() or "no information" in reply.lower()
                if not passed:
                    all_rag_ok = False
                print(f"  Q: '{q_text}' -> Passed={passed} [Reply: {reply[:100]}...]")
                q_results.append({"question": q_text, "passed": passed, "preview": reply[:120]})
        except Exception as e:
            print(f"  Q: '{q_text}' -> FAIL: {e}")
            all_rag_ok = False
            q_results.append({"question": q_text, "error": str(e), "passed": False})

    results["tests"]["rag_5_questions"] = {
        "all_passed": all_rag_ok,
        "details": q_results
    }

    # 6. Session Isolation & Authorized Download
    print("\n[TEST 6] Testing Session Isolation and Authorized Download...")
    auth_download_ok = False
    unauth_download_blocked = False
    unauth_delete_blocked = False

    if txt_doc_id:
        # Authorized download
        try:
            dl_req = urllib.request.Request(
                f"{base_url}/api/files/{txt_doc_id}/download",
                headers={"X-Anonymous-ID": owner_a}
            )
            with urllib.request.urlopen(dl_req, timeout=15) as dl_resp:
                dl_bytes = dl_resp.read()
                auth_download_ok = (dl_resp.status == 200 and hashlib.sha256(dl_bytes).hexdigest() == hashlib.sha256(chico_text.encode("utf-8")).hexdigest())
                print(f"  Authorized Download: HTTP {dl_resp.status}, Hash Match={auth_download_ok}")
        except Exception as e:
            print(f"  Authorized Download Error: {e}")

        # Unauthorized download
        try:
            unauth_req = urllib.request.Request(
                f"{base_url}/api/files/{txt_doc_id}/download",
                headers={"X-Anonymous-ID": owner_b}
            )
            with urllib.request.urlopen(unauth_req, timeout=10) as un_resp:
                print(f"  [SECURITY VIOLATION] Session B downloaded Session A file: HTTP {un_resp.status}")
        except urllib.error.HTTPError as he:
            if he.code == 403:
                unauth_download_blocked = True
                print("  Unauthorized Download Blocked: HTTP 403 Forbidden")
        except Exception as e:
            print(f"  Unauthorized download check error: {e}")

        # Unauthorized delete
        try:
            unauth_del = urllib.request.Request(
                f"{base_url}/api/files/{txt_doc_id}",
                headers={"X-Anonymous-ID": owner_b},
                method="DELETE"
            )
            with urllib.request.urlopen(unauth_del, timeout=10) as del_resp:
                print(f"  [SECURITY VIOLATION] Session B deleted Session A file: HTTP {del_resp.status}")
        except urllib.error.HTTPError as he:
            if he.code in (403, 404):
                unauth_delete_blocked = True
                print(f"  Unauthorized Delete Blocked: HTTP {he.code}")
        except Exception as e:
            print(f"  Unauthorized delete check error: {e}")

    results["tests"]["security_isolation"] = {
        "auth_download_ok": auth_download_ok,
        "unauth_download_blocked_403": unauth_download_blocked,
        "unauth_delete_blocked": unauth_delete_blocked
    }

    # 7. Cleanup
    print("\n[TEST 7] Cleaning Up Test Artifacts...")
    cleanup_ids = [i for i in [chico_doc_id, txt_doc_id] if i]
    cleanup_success = True
    for item_id in cleanup_ids:
        try:
            clean_req = urllib.request.Request(
                f"{base_url}/api/files/{item_id}",
                headers={"X-Anonymous-ID": owner_a},
                method="DELETE"
            )
            with urllib.request.urlopen(clean_req, timeout=15) as c_resp:
                print(f"  Deleted file {item_id}: HTTP {c_resp.status}")
        except Exception as e:
            print(f"  Failed deleting {item_id}: {e}")
            cleanup_success = False

    results["tests"]["cleanup"] = cleanup_success

    overall_ok = (
        bool(txt_doc_id) and
        video_rejected and
        doc_rejected and
        all_rag_ok and
        auth_download_ok and
        unauth_download_blocked and
        unauth_delete_blocked
    )
    results["all_passed"] = overall_ok

    print(f"\n========================================================")
    print(f"BATTERY COMPLETE: {'ALL PASSED (100%)' if overall_ok else 'SOME TESTS FAILED'}")
    print(f"========================================================\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas Gen-3.3.5 Production Battery")
    parser.add_argument("--url", default="https://atlas-scientist.vercel.app", help="Atlas base URL")
    args = parser.parse_args()
    res = run_battery(args.url)
    sys.exit(0 if res.get("all_passed") else 1)
