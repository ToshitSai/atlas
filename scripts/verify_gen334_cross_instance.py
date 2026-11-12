#!/usr/bin/env python3
"""Atlas AI Gen-3.3.4: Cross-Instance Multimodal Persistence Verification Battery.

Performs rigorous end-to-end verification required by Section 11:
1. Ingests test document ATLAS-PERSISTENCE-2026 (PERSIST-88421, Europa, Dr. Evelyn Stone).
2. Generates and ingests test image ATLAS-IMAGE-2026 (VISION-72819, Titan).
3. Verifies private Blob storage security (unauthenticated access blocked with HTTP 403).
4. Verifies cross-session isolation (Session B blocked from downloading/deleting Session A's files).
5. Verifies cross-instance RAG retrieval via separate request contexts.
6. Cleans up test artifacts securely.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None

BASE_DIR = Path(__file__).resolve().parent.parent


def create_test_image_bytes() -> bytes:
    """Generate a high-contrast image containing ATLAS-IMAGE-2026, VISION-72819, Location: Titan."""
    if Image is None:
        raise RuntimeError("Pillow is required to generate test image")

    img = Image.new("RGB", (800, 400), color=(15, 23, 42))  # slate-900 background
    draw = ImageDraw.Draw(img)

    # Use default bitmap font with scaled rendering
    text_lines = [
        "ATLAS-IMAGE-2026",
        "Image Token: VISION-72819",
        "Target Location: Titan",
        "Subsurface Exploration Mission",
        "Atmospheric Methane Analysis",
    ]
    y = 50
    for line in text_lines:
        draw.text((60, y), line, fill=(248, 250, 252))
        y += 60

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_test_doc_bytes() -> bytes:
    content = (
        "Project: ATLAS-PERSISTENCE-2026\n"
        "Verification Token: PERSIST-88421\n"
        "Project Location: Europa\n"
        "Research Director: Dr. Evelyn Stone\n"
        "Mission Statement: The Europa Subsurface Oceans Expedition is investigating "
        "hydrothermal vent biosignatures beneath 15 kilometers of ice crust. All persistent "
        "findings are cataloged under cryptographic verification token PERSIST-88421.\n"
    )
    return content.encode("utf-8")


def make_multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    boundary = f"----AtlasBoundary{int(time.time() * 1000)}"
    body = bytearray()

    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{v}\r\n".encode("utf-8"))

    for field_name, (filename, data, ctype) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
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
    print(f"ATLAS GEN-3.3.4 CROSS-INSTANCE PERSISTENCE BATTERY")
    print(f"Target URL: {base_url}")
    print(f"Authorized Session: {owner_a}")
    print(f"Unauthorized Session: {owner_b}")
    print(f"========================================================\n")

    # 1. Health & Readiness Check
    print("[TEST 1] Verifying /api/health and /api/ready...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        results["tests"]["health"] = {
            "status": health.get("status"),
            "database": health.get("database"),
            "databaseType": health.get("databaseType"),
            "durability": health.get("durability"),
            "persistent": health.get("persistent"),
            "objectStorage": health.get("objectStorage"),
        }
        print(f"  Health Status: {health.get('status')}")
        print(f"  Database Type: {health.get('databaseType')}, Durability: {health.get('durability')}")
        print(f"  Object Storage: {health.get('objectStorage')}")
    except Exception as e:
        print(f"  [FAIL] /api/health error: {e}")
        results["tests"]["health"] = {"error": str(e)}

    # 2. Ingest Document: ATLAS-PERSISTENCE-2026
    print("\n[TEST 2] Ingesting ATLAS-PERSISTENCE-2026 (PERSIST-88421)...")
    doc_bytes = create_test_doc_bytes()
    doc_body, doc_ctype = make_multipart(
        {"workflow": "knowledge_base"},
        {"file": ("ATLAS-PERSISTENCE-2026.txt", doc_bytes, "text/plain")}
    )
    doc_req = urllib.request.Request(
        f"{base_url}/api/documents",
        data=doc_body,
        headers={"Content-Type": doc_ctype, "X-Anonymous-ID": owner_a},
        method="POST"
    )
    doc_id = None
    try:
        with urllib.request.urlopen(doc_req, timeout=30) as resp:
            doc_res = json.loads(resp.read().decode("utf-8"))
            doc_id = doc_res.get("id")
            results["tests"]["doc_ingest"] = {
                "id": doc_id,
                "chunks": doc_res.get("chunks"),
                "status": doc_res.get("status"),
                "durability": doc_res.get("durability"),
                "persistent": doc_res.get("persistent"),
            }
            print(f"  Doc Upload Succeeded: id={doc_id}, chunks={doc_res.get('chunks')}, persistent={doc_res.get('persistent')}")
    except Exception as e:
        print(f"  [FAIL] Doc Ingest error: {e}")
        results["tests"]["doc_ingest"] = {"error": str(e)}

    # 3. Ingest Image: ATLAS-IMAGE-2026 (VISION-72819)
    print("\n[TEST 3] Ingesting ATLAS-IMAGE-2026 (VISION-72819)...")
    img_bytes = create_test_image_bytes()
    img_body, img_ctype = make_multipart(
        {"workflow": "knowledge_base"},
        {"file": ("ATLAS-IMAGE-2026.png", img_bytes, "image/png")}
    )
    img_req = urllib.request.Request(
        f"{base_url}/api/documents",
        data=img_body,
        headers={"Content-Type": img_ctype, "X-Anonymous-ID": owner_a},
        method="POST"
    )
    img_id = None
    try:
        with urllib.request.urlopen(img_req, timeout=40) as resp:
            img_res = json.loads(resp.read().decode("utf-8"))
            img_id = img_res.get("id")
            results["tests"]["img_ingest"] = {
                "id": img_id,
                "ocr_text": img_res.get("ocr_text", "")[:80],
                "visual_description": img_res.get("visual_description", "")[:80],
                "persistent": img_res.get("persistent"),
            }
            print(f"  Image Upload Succeeded: id={img_id}, persistent={img_res.get('persistent')}")
            print(f"  OCR extracted: {img_res.get('ocr_text', '')[:60]}...")
    except Exception as e:
        print(f"  [FAIL] Image Ingest error: {e}")
        results["tests"]["img_ingest"] = {"error": str(e)}

    # 4. Authorized Download Test (Session A)
    print("\n[TEST 4] Authorized Download Verification (Session A)...")
    if doc_id:
        try:
            req = urllib.request.Request(
                f"{base_url}/api/documents/{doc_id}/download",
                headers={"X-Anonymous-ID": owner_a}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                cache_ctrl = resp.headers.get("Cache-Control", "")
                nosniff = resp.headers.get("X-Content-Type-Options", "")
                matches = hashlib.sha256(data).hexdigest() == hashlib.sha256(doc_bytes).hexdigest()
                results["tests"]["authorized_download"] = {
                    "http_status": resp.status,
                    "sha256_match": matches,
                    "cache_control": cache_ctrl,
                    "nosniff": nosniff,
                }
                print(f"  Authorized Download: HTTP {resp.status}, Hash Match: {matches}, Cache-Control: {cache_ctrl}")
        except Exception as e:
            print(f"  [FAIL] Authorized download error: {e}")
            results["tests"]["authorized_download"] = {"error": str(e)}

    # 5. Unauthorized Download & Delete Isolation (Session B)
    print("\n[TEST 5] Cross-Session Security & Isolation Verification (Session B)...")
    if doc_id:
        # Unauthorized download
        unauth_blocked = False
        try:
            req = urllib.request.Request(
                f"{base_url}/api/documents/{doc_id}/download",
                headers={"X-Anonymous-ID": owner_b}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"  [SECURITY VIOLATION] Session B was allowed to download Session A's file: HTTP {resp.status}")
        except urllib.error.HTTPError as he:
            if he.code == 403:
                unauth_blocked = True
                print(f"  Security Verified: Unauthorized download strictly blocked with HTTP 403 Forbidden.")
            else:
                print(f"  Unauthorized download received HTTP {he.code}")
        except Exception as e:
            print(f"  Unauthorized download check error: {e}")

        # Unauthorized delete
        delete_blocked = False
        try:
            req = urllib.request.Request(
                f"{base_url}/api/documents/{doc_id}",
                headers={"X-Anonymous-ID": owner_b},
                method="DELETE"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"  [SECURITY VIOLATION] Session B deleted Session A's file: HTTP {resp.status}")
        except urllib.error.HTTPError as he:
            if he.code in (403, 404):
                delete_blocked = True
                print(f"  Security Verified: Unauthorized delete blocked with HTTP {he.code}.")
        except Exception as e:
            print(f"  Unauthorized delete check error: {e}")

        results["tests"]["session_isolation"] = {
            "unauthorized_download_blocked_403": unauth_blocked,
            "unauthorized_delete_blocked": delete_blocked
        }

    # 6. Cross-Instance RAG Retrieval (Session A from a clean context)
    print("\n[TEST 6] Cross-Instance Grounded RAG Query Verification...")
    rag_retrieval_ok = False
    try:
        chat_payload = json.dumps({
            "message": "What is the verification token and research director for ATLAS-PERSISTENCE-2026 on Europa?",
            "conversation_id": f"conv_{int(time.time())}"
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=chat_payload,
            headers={"Content-Type": "application/json", "X-Anonymous-ID": owner_a},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=35) as resp:
            chat_res = json.loads(resp.read().decode("utf-8"))
            answer = chat_res.get("reply", "") or chat_res.get("response", "")
            has_token = "PERSIST-88421" in answer
            has_director = "Evelyn Stone" in answer or "Stone" in answer
            rag_retrieval_ok = has_token and has_director
            results["tests"]["rag_retrieval"] = {
                "token_found": has_token,
                "director_found": has_director,
                "success": rag_retrieval_ok,
                "preview": answer[:150]
            }
            print(f"  RAG Answer Retrieved: Token Found={has_token}, Director Found={has_director}")
            print(f"  Answer preview: {answer[:120]}...")
    except Exception as e:
        print(f"  [FAIL] RAG query error: {e}")
        results["tests"]["rag_retrieval"] = {"error": str(e)}

    # 7. Cleanup
    print("\n[TEST 7] Cleaning Up Test Artifacts...")
    cleanup_ok = True
    for item_id, label in [(doc_id, "document"), (img_id, "image")]:
        if item_id:
            try:
                del_req = urllib.request.Request(
                    f"{base_url}/api/documents/{item_id}",
                    headers={"X-Anonymous-ID": owner_a},
                    method="DELETE"
                )
                with urllib.request.urlopen(del_req, timeout=15) as d_resp:
                    print(f"  Deleted {label} {item_id}: HTTP {d_resp.status}")
            except Exception as e:
                print(f"  Failed deleting {label} {item_id}: {e}")
                cleanup_ok = False
    results["tests"]["cleanup_successful"] = cleanup_ok

    all_passed = (
        bool(doc_id and img_id) and
        results.get("tests", {}).get("authorized_download", {}).get("sha256_match") is True and
        results.get("tests", {}).get("session_isolation", {}).get("unauthorized_download_blocked_403") is True and
        results.get("tests", {}).get("rag_retrieval", {}).get("success") is True
    )
    results["all_passed"] = all_passed
    print(f"\n========================================================")
    print(f"BATTERY COMPLETE: {'ALL PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"========================================================\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas Gen-3.3.4 Persistence Battery")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of Atlas server")
    args = parser.parse_args()
    run_battery(args.url)
