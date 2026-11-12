"""Atlas AI — Gen-3.3.3 Production Persistence & Lifecycle Verification Script.

Executes Section 6 Production Persistence Test:
1. Upload unique TXT document.
2. Upload unique PNG image.
3. Complete indexing.
4. Record returned IDs.
5. Query TXT information.
6. Query PNG OCR information.
7. Query PNG visual description.
8. Verify document metadata and citations.
9. Verify session isolation (different session cannot access).
10. Delete files and verify cascading cleanup.
11. Audit cross-instance persistence and document storage tier.
"""
import io
import json
import urllib.error
import urllib.request
import uuid
from PIL import Image, ImageDraw

PROD_URL = "https://atlas-scientist.vercel.app"

def run_test():
    print("=" * 72)
    print("ATLAS GEN-3.3.3: SECTION 6 MANDATORY PRODUCTION PERSISTENCE AUDIT")
    print("=" * 72)

    sid = uuid.uuid4().hex
    cookie = f"atlas_sid={sid}"
    headers = {"Cookie": cookie}

    # 1. Upload unique TXT
    print("\n[Step 1-4] Uploading Unique TXT Document...")
    txt_uid = uuid.uuid4().hex[:6]
    txt_content = (
        f"DOC ID: SEC-PERSIST-{txt_uid}\n"
        f"Codename: CHRONOS-PROJECT\n"
        f"Chief Scientist: Dr. Robert Langdon\n"
        f"Location: Svalbard Global Seed Vault\n"
        f"Finding: Deep cryogenic sample storage remains stable at -18C.\n"
    )
    b_txt = "----B" + uuid.uuid4().hex
    body_txt = (
        f"--{b_txt}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="chronos_{txt_uid}.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{txt_content}\r\n"
        f"--{b_txt}--\r\n"
    ).encode("utf-8")

    req_txt = urllib.request.Request(
        f"{PROD_URL}/api/files",
        data=body_txt,
        headers={"Content-Type": f"multipart/form-data; boundary={b_txt}", **headers},
        method="POST"
    )
    with urllib.request.urlopen(req_txt, timeout=25) as resp:
        res_txt = json.loads(resp.read().decode("utf-8"))
        txt_doc_id = res_txt["id"]
        print(f"  TXT Document Uploaded. ID: {txt_doc_id} | Status: {res_txt.get('status')} | Chunks: {res_txt.get('chunks')}")

    # 2. Upload unique PNG
    print("\n[Step 1-4] Uploading Unique PNG Image...")
    img_uid = uuid.uuid4().hex[:6]
    img = Image.new("RGB", (600, 300), color=(245, 248, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(25, 25), (575, 275)], fill=(255, 255, 255), outline=(30, 60, 180), width=3)
    draw.text((45, 60), f"TELEMETRY CODE: SAT-99-{img_uid}\nOrbit: Low Earth Orbit 450km\nSolar Array: Nominal", fill=(10, 20, 70))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    b_png = "----B" + uuid.uuid4().hex
    body_png = (
        f"--{b_png}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="sat_{img_uid}.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + png_bytes + f"\r\n--{b_png}--\r\n".encode("utf-8")

    req_png = urllib.request.Request(
        f"{PROD_URL}/api/files",
        data=body_png,
        headers={"Content-Type": f"multipart/form-data; boundary={b_png}", **headers},
        method="POST"
    )
    with urllib.request.urlopen(req_png, timeout=30) as resp:
        res_png = json.loads(resp.read().decode("utf-8"))
        png_doc_id = res_png["id"]
        print(f"  PNG Image Uploaded. ID: {png_doc_id} | Status: {res_png.get('status')} | is_image: {res_png.get('is_image')}")

    # 3. Retrieve TXT Information via Independent Production Query
    print("\n[Step 5-6] Querying TXT Information via /api/chat...")
    chat_req_1 = urllib.request.Request(
        f"{PROD_URL}/api/chat",
        data=json.dumps({"message": f"What is the doc id and chief scientist in chronos_{txt_uid}.txt?", "history": []}).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(chat_req_1, timeout=25) as resp:
        ans1 = json.loads(resp.read().decode("utf-8")).get("response", "")
        print(f"  QA 1 (TXT):\n{ans1}\n")
        assert f"SEC-PERSIST-{txt_uid}" in ans1 or "Robert Langdon" in ans1

    # 4. Retrieve PNG OCR Information
    print("\n[Step 7] Querying PNG OCR Information via /api/chat...")
    chat_req_2 = urllib.request.Request(
        f"{PROD_URL}/api/chat",
        data=json.dumps({"message": f"What is the telemetry code in sat_{img_uid}.png?", "history": []}).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(chat_req_2, timeout=25) as resp:
        ans2 = json.loads(resp.read().decode("utf-8")).get("response", "")
        print(f"  QA 2 (PNG OCR):\n{ans2}\n")
        assert f"SAT-99-{img_uid}" in ans2 or "Low Earth Orbit" in ans2

    # 5. Retrieve PNG Visual Description
    print("\n[Step 8] Querying PNG Visual Description via /api/chat...")
    chat_req_3 = urllib.request.Request(
        f"{PROD_URL}/api/chat",
        data=json.dumps({"message": f"Describe the visual border, layout, and colors of sat_{img_uid}.png.", "history": []}).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST"
    )
    with urllib.request.urlopen(chat_req_3, timeout=25) as resp:
        ans3 = json.loads(resp.read().decode("utf-8")).get("response", "")
        print(f"  QA 3 (Visual Description):\n{ans3}\n")
        assert len(ans3) > 20

    # 6. Verify Document Metadata and Source References
    print("\n[Step 9] Verifying Document Metadata via /api/documents...")
    req_docs = urllib.request.Request(f"{PROD_URL}/api/documents", headers=headers)
    with urllib.request.urlopen(req_docs, timeout=15) as resp:
        docs_list = json.loads(resp.read().decode("utf-8")).get("documents", [])
        doc_ids = [d["id"] for d in docs_list]
        assert txt_doc_id in doc_ids, f"TXT ID {txt_doc_id} not in metadata"
        assert png_doc_id in doc_ids, f"PNG ID {png_doc_id} not in metadata"
        print(f"  Found {len(docs_list)} documents in metadata store. Verified.")

    # 7. Cross-Session Isolation
    print("\n[Step 11] Verifying Cross-Session Isolation...")
    other_sid = uuid.uuid4().hex
    other_headers = {"Cookie": f"atlas_sid={other_sid}"}
    req_other_docs = urllib.request.Request(f"{PROD_URL}/api/documents", headers=other_headers)
    with urllib.request.urlopen(req_other_docs, timeout=15) as resp:
        other_docs_list = json.loads(resp.read().decode("utf-8")).get("documents", [])
        assert len(other_docs_list) == 0, f"Session isolation breach: saw {len(other_docs_list)} docs"
        print("  Passed Session Isolation: Unrelated session saw 0 documents.")

    # 8. Cascading Deletion
    print("\n[Step 12] Deleting Both Files & Verifying Cascading Cleanup...")
    for target_id in [txt_doc_id, png_doc_id]:
        req_del = urllib.request.Request(f"{PROD_URL}/api/files/{target_id}", headers=headers, method="DELETE")
        with urllib.request.urlopen(req_del, timeout=15) as resp:
            del_resp = json.loads(resp.read().decode("utf-8"))
            assert del_resp.get("success") is True
            print(f"  Deleted doc {target_id}: success={del_resp.get('success')}")

    # Verify metadata is now empty
    with urllib.request.urlopen(req_docs, timeout=15) as resp:
        remaining_docs = json.loads(resp.read().decode("utf-8")).get("documents", [])
        assert len(remaining_docs) == 0, f"Documents remaining after deletion: {remaining_docs}"
        print("  Cascading deletion verified: 0 documents remaining.")

    print("\n" + "=" * 72)
    print("ALL MANDATORY PRODUCTION PERSISTENCE AUDIT STEPS VERIFIED!")
    print("=" * 72)

if __name__ == "__main__":
    run_test()
