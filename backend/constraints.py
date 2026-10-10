"""Explicit output-constraint detection and conservative validation."""
import json, re

def detect(text: str) -> dict:
    low = str(text or "").lower()
    return {"json_only": bool(re.search(r"strictly?\s+valid\s+json|json\s+only|nothing\s+else", low)),
            "no_markdown": bool(re.search(r"no\s+markdown", low)),
            "sentence_count": (int(m.group(1)) if (m:=re.search(r"exactly\s+(\d+)\s+sentences?", low)) else None),
            "word_range": ((int(m.group(1)), int(m.group(2))) if (m:=re.search(r"(\d+)\s*[-to]+\s*(\d+)\s+words?", low)) else None)}

def json_only(value: str):
    """Return parsed JSON and canonical text, stripping provider wrappers."""
    text = str(value or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
    if fenced: text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start: text = text[start:end+1]
    try:
        obj = json.loads(text)
        return obj, json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None, None
