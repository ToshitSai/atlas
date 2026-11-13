import os
import sys
import time
import urllib.error
import urllib.request

test_file = r"C:\Users\Toshit\Desktop\youtube\Chico, Rocky & Luna Character Sheet.png"
if not os.path.exists(test_file):
    print("Test file does not exist:", test_file)
    sys.exit(1)

with open(test_file, "rb") as f:
    content = f.read()

size = len(content)
filename = os.path.basename(test_file)
print(f"Testing upload of {filename}: {size} bytes ({size / 1024 / 1024:.2f} MB)")

base_url = "https://atlas-scientist.vercel.app"
boundary = f"----AtlasBoundary{int(time.time() * 1000)}"

body = bytearray()
body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"workflow\"\r\n\r\nchat_attachment\r\n".encode("utf-8"))
body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
body.extend(content)
body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

for endpoint in ["/api/files", "/api/documents"]:
    print(f"\n--- Testing POST {endpoint} ---")
    req = urllib.request.Request(
        f"{base_url}{endpoint}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {resp.read().decode('utf-8')[:300]}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError Status: {e.code} {e.reason}")
        print(f"Response body: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
