import os
import sys

sys.path.insert(0, r"C:\Users\Toshit\Desktop\Atlas")

env_path = r"C:\Users\Toshit\Desktop\Atlas\.env.local"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip("\"'")

from backend.rag_service import service as rag_svc

docs = rag_svc.list_documents("test_session_chico")
print("Total docs found:", len(docs))
for d in docs:
    print("Doc:", d["filename"], d["id"])

queries = [
    "Analyze attached Chico, Rocky & Luna Character Sheet.png",
    "What characters are in the sheet?",
    "Tell me about Chico and Rocky",
]

for q in queries:
    print(f"\nQuery: '{q}'")
    res = rag_svc.retrieve_context(q, owner_session="test_session_chico", rag_mode="on")
    print(f"Retrieved chunks count: {len(res['chunks'])}")
    for i, c in enumerate(res["chunks"]):
        print(f"  Chunk {i+1} [{c.get('source')}]: {c.get('content')[:120]}...")
