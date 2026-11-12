import io
import json
import urllib.error
import urllib.request
import uuid

PROD_URL = "https://atlas-scientist.vercel.app"

def run_production_tests():
    print("=" * 70)
    print("LIVE PRODUCTION VALIDATION FOR GEN-3.3.3")
    print(f"Target: {PROD_URL}")
    print("=" * 70)

    # 1. Health Probe
    print("\n--- 1. Live Health Probe ---")
    req = urllib.request.Request(f"{PROD_URL}/api/health", headers={"User-Agent": "Atlas-Audit/3.3.3"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        health = json.loads(resp.read().decode("utf-8"))
        print(f"  HTTP {resp.status} | Commit: {health.get('build', {}).get('commit')}")
        print(f"  Storage: {health.get('rag', {}).get('storage')} | Persistent: {health.get('rag', {}).get('persistent')}")
        print(f"  Embeddings: {health.get('embeddings', {}).get('provider')} ({health.get('embeddings', {}).get('mode')})")
        assert health.get("rag", {}).get("persistent") is False, "Must not claim persistence when ephemeral"

    # 2. Legacy DOC Rejection
    print("\n--- 2. Live Legacy DOC Rejection Probe ---")
    boundary = "----Boundary" + uuid.uuid4().hex
    body_doc = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="confidential.doc"\r\n'
        f"Content-Type: application/msword\r\n\r\n"
        f"Legacy binary data\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req_doc = urllib.request.Request(
        f"{PROD_URL}/api/files",
        data=body_doc,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_doc, timeout=15) as resp:
            print("  UNEXPECTED: Legacy DOC succeeded!")
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8")
        print(f"  Passed HTTP {err.code}: {err_msg}")
        assert err.code == 400
        assert "Legacy binary Microsoft Office format (.doc) is not supported" in err_msg

    # 3. Modern TXT Document Upload (Workflow A)
    print("\n--- 3. Live Modern TXT Document Upload ---")
    boundary_txt = "----Boundary" + uuid.uuid4().hex
    txt_content = (
        "LIVE PRODUCTION PERSISTENCE TEST 3.3.3\n"
        "Project Code: PROD-VERIFIED-909\n"
        "Lead: Dr. Alexander Ward\n"
        "Location: Geneva Facility\n"
        "Finding: Real-time RAG grounding operates with 99.8% precision.\n"
    )
    body_txt = (
        f"--{boundary_txt}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="live_test.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{txt_content}\r\n"
        f"--{boundary_txt}--\r\n"
    ).encode("utf-8")

    fixed_sid = uuid.uuid4().hex
    session_cookie = f"atlas_sid={fixed_sid}"
    print(f"  Session ID: {fixed_sid}")

    req_upload = urllib.request.Request(
        f"{PROD_URL}/api/files",
        data=body_txt,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary_txt}",
            "Cookie": session_cookie
        },
        method="POST"
    )
    upload_res = None
    with urllib.request.urlopen(req_upload, timeout=20) as resp:
        upload_res = json.loads(resp.read().decode("utf-8"))
        print(f"  Passed Upload: ID={upload_res.get('id')}, Status={upload_res.get('status')}, Chunks={upload_res.get('chunks')}")
        assert upload_res.get("status") == "ready"
        assert upload_res.get("chunks") > 0

    doc_id = upload_res["id"]

    # 3b. Verify listing
    print("\n--- 3b. Live Document Listing ---")
    req_list = urllib.request.Request(
        f"{PROD_URL}/api/documents",
        headers={"Cookie": session_cookie}
    )
    with urllib.request.urlopen(req_list, timeout=15) as resp:
        list_res = json.loads(resp.read().decode("utf-8"))
        print(f"  List response: Total={list_res.get('total')}, Docs={[d.get('id') for d in list_res.get('documents', [])]}")

    # 4. Live Chat RAG Query (Workflow A & Citations)
    print("\n--- 4. Live Chat RAG Query ---")
    chat_payload = json.dumps({
        "message": "What is the project code and lead in the uploaded live test document?",
        "history": []
    }).encode("utf-8")

    req_chat = urllib.request.Request(
        f"{PROD_URL}/api/chat",
        data=chat_payload,
        headers={
            "Content-Type": "application/json",
            "Cookie": session_cookie
        },
        method="POST"
    )
    with urllib.request.urlopen(req_chat, timeout=25) as resp:
        chat_res = json.loads(resp.read().decode("utf-8"))
        ans = chat_res.get("response", "")
        print(f"  QA Response:\n{ans}\n")
        assert "PROD-VERIFIED-909" in ans or "Alexander Ward" in ans, "Failed to retrieve grounded fact"
        print("  Passed Live RAG Grounding & Retrieval!")

    # 5. Cascading Deletion
    print("\n--- 5. Live Cascading Deletion ---")
    req_del = urllib.request.Request(
        f"{PROD_URL}/api/files/{doc_id}",
        headers={"Cookie": session_cookie},
        method="DELETE"
    )
    with urllib.request.urlopen(req_del, timeout=15) as resp:
        del_res = json.loads(resp.read().decode("utf-8"))
        print(f"  Passed Deletion: {del_res}")
        assert del_res.get("success") is True

    # 6. Live PNG Image Upload & OCR Retrieval
    print("\n--- 6. Live PNG Image Upload & Multimodal Extraction ---")
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (600, 300), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (580, 280)], fill=(255, 255, 255), outline=(50, 70, 200), width=3)
    draw.text((40, 50), "ATLAS VISION CODE: LIVE-ORBIT-442\nTarget: Titan Subsurface\nStatus: Online", fill=(20, 20, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    boundary_img = "----Boundary" + uuid.uuid4().hex
    body_img = (
        f"--{boundary_img}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="telemetry.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + png_bytes + f"\r\n--{boundary_img}--\r\n".encode("utf-8")

    img_sid = uuid.uuid4().hex
    img_cookie = f"atlas_sid={img_sid}"

    req_img = urllib.request.Request(
        f"{PROD_URL}/api/files",
        data=body_img,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary_img}",
            "Cookie": img_cookie
        },
        method="POST"
    )
    with urllib.request.urlopen(req_img, timeout=30) as resp:
        img_res = json.loads(resp.read().decode("utf-8"))
        print(f"  Passed Live Image Upload: ID={img_res.get('id')}, is_image={img_res.get('is_image')}, status={img_res.get('status')}")
        assert img_res.get("is_image") is True
        assert img_res.get("status") == "ready"

    # Query image fact
    chat_payload_img = json.dumps({
        "message": "What is the vision code and target in the uploaded telemetry image?",
        "history": []
    }).encode("utf-8")
    req_chat_img = urllib.request.Request(
        f"{PROD_URL}/api/chat",
        data=chat_payload_img,
        headers={"Content-Type": "application/json", "Cookie": img_cookie},
        method="POST"
    )
    with urllib.request.urlopen(req_chat_img, timeout=25) as resp:
        chat_img_res = json.loads(resp.read().decode("utf-8"))
        img_ans = chat_img_res.get("response", "")
        print(f"  Live Image QA Response:\n{img_ans}\n")
        assert "LIVE-ORBIT-442" in img_ans or "Titan" in img_ans, "Failed live image OCR grounding"
        print("  Passed Live Multimodal Image OCR & Grounding!")

    print("\n" + "=" * 70)
    print("ALL PRODUCTION LIVE TESTS PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    run_production_tests()
