"""Atlas AI — Multimodal Vision & OCR Engine.

Handles image validation, format detection, OCR transcription, visual-content analysis,
and multimodal question-answering across PNG, JPG, JPEG, WEBP, and GIF images.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB


def detect_image_type(content: bytes) -> Optional[str]:
    """Inspect magic bytes to determine actual image MIME type."""
    if not content or len(content) < 8:
        return None
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "image/gif"
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def get_image_mime(filename: str, content: bytes) -> str:
    """Return verified MIME type, checking magic bytes first with extension fallback."""
    magic_mime = detect_image_type(content)
    if magic_mime:
        return magic_mime
    ext = os.path.splitext(filename.lower())[1]
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_map.get(ext, "image/png")


class VisionService:
    """Orchestrates OCR and visual understanding via multimodal vision models."""

    def __init__(self):
        pass

    def is_available(self) -> bool:
        """Check if any multimodal vision provider is configured."""
        return bool(
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )

    def analyze_image(
        self,
        filename: str,
        content: bytes,
        owner_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform OCR and visual analysis on an uploaded image.
        
        Returns structured extraction including:
        - ocr_text: verbatim text, codes, equations, labels, numbers.
        - visual_description: scene, layout, objects, charts, diagrams.
        - image_type: classification.
        - key_entities: identified components.
        - sections: list of RAG-ready sections.
        """
        mime_type = get_image_mime(filename, content)
        b64_data = base64.b64encode(content).decode("utf-8")

        prompt = (
            "You are the Atlas Multimodal Vision Engine. Analyze this image thoroughly and accurately.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. OCR EXTRACTION: Extract ALL visible text, codes, identifiers, labels, numbers, table values, "
            "or mathematical formulas verbatim. If there is no text in the image, return an empty string \"\".\n"
            "2. VISUAL DESCRIPTION: Provide a detailed, factual visual description of what is depicted: "
            "the type of image (e.g. screenshot, photograph, architectural diagram, flowchart, chart, table, UI mockup), "
            "all visible objects, layout structure, colors, relationships, and visual components.\n"
            "3. CLASSIFICATION: Classify the image type.\n"
            "4. KEY ENTITIES: List key entities, components, or topics identified in the image.\n"
            "5. NO HALLUCINATION: Do NOT fabricate text or details that are not visible in the image.\n\n"
            "Return strictly valid JSON with this exact schema:\n"
            "{\n"
            '  "ocr_text": "...",\n'
            '  "visual_description": "...",\n'
            '  "image_type": "...",\n'
            '  "key_entities": ["..."]\n'
            "}"
        )

        res = self._call_multimodal(prompt, b64_data, mime_type, timeout=30)
        
        ocr_text = ""
        visual_desc = ""
        image_type = "Image"
        key_entities = []

        if res:
            try:
                # Strip markdown code blocks if wrapped
                cleaned = res.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```$", "", cleaned)
                data = json.loads(cleaned.strip())
                ocr_text = (data.get("ocr_text") or "").strip()
                visual_desc = (data.get("visual_description") or "").strip()
                image_type = (data.get("image_type") or "Image").strip()
                key_entities = data.get("key_entities") or []
            except Exception as parse_err:
                # If model returned freeform text instead of JSON
                print(f"[VISION SERVICE] JSON parse warning: {parse_err}; using raw text")
                visual_desc = res.strip()
                # Extract potential OCR text
                lines = [line.strip() for line in res.split("\n") if line.strip()]
                ocr_text = "\n".join(lines[:10])

        if not visual_desc and not ocr_text:
            visual_desc = f"Uploaded image: {filename} ({mime_type}, {len(content)} bytes)."

        sections: List[Dict[str, Any]] = []

        # 1. OCR Section (if text exists)
        if ocr_text:
            sections.append({
                "page": 1,
                "section": f"Image OCR: {filename}",
                "text": ocr_text
            })

        # 2. Visual Description Section
        if visual_desc:
            sections.append({
                "page": 1,
                "section": f"Visual Description: {filename}",
                "text": visual_desc
            })

        # 3. Composite metadata section
        entities_str = ", ".join(str(e) for e in key_entities) if key_entities else "None specified"
        meta_summary = (
            f"Image File: {filename}\n"
            f"Type: {image_type}\n"
            f"MIME: {mime_type}\n"
            f"Key Elements: {entities_str}"
        )
        sections.append({
            "page": 1,
            "section": f"Image Summary: {filename}",
            "text": meta_summary
        })

        return {
            "filename": filename,
            "mime_type": mime_type,
            "byte_size": len(content),
            "ocr_text": ocr_text,
            "visual_description": visual_desc,
            "image_type": image_type,
            "key_entities": key_entities,
            "sections": sections,
            "status": "ready"
        }

    def answer_image_question(
        self,
        question: str,
        content: bytes,
        filename: str,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Directly query a multimodal model about an uploaded image (Workflow A: chat attachment)."""
        mime_type = get_image_mime(filename, content)
        b64_data = base64.b64encode(content).decode("utf-8")

        prompt = (
            f"The user has attached an image ({filename}) and asked the following question:\n\n"
            f"User Question: {question}\n\n"
            "Answer the question directly, factually, and concisely using ONLY the visual and textual evidence in the image.\n"
            "If the requested information is not present or visible in the image, state that clearly."
        )
        return self._call_multimodal(prompt, b64_data, mime_type, timeout=35)

    def _call_multimodal(
        self,
        prompt: str,
        b64_data: str,
        mime_type: str,
        timeout: int = 30
    ) -> Optional[str]:
        """Invoke configured multimodal vision provider (Gemini -> OpenAI -> Claude)."""
        # 1. Try Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            candidate_models = [
                "gemini-3-flash-preview",
                "gemini-2.5-flash-lite",
                "gemini-flash-latest",
                "gemini-3.1-flash-lite-preview",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ]
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": b64_data}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        candidates = res.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                            if text:
                                return text
                except urllib.error.HTTPError as http_err:
                    if http_err.code in (404, 429, 503):
                        continue
                    print(f"[VISION SERVICE] Gemini {model} HTTP {http_err.code}: {http_err.reason}")
                except Exception as exc:
                    print(f"[VISION SERVICE] Gemini {model} error: {exc}")

        # 2. Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}}
                    ]
                }],
                "max_tokens": 2048,
                "temperature": 0.1
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    return res["choices"][0]["message"]["content"]
            except Exception as exc:
                print(f"[VISION SERVICE] OpenAI Vision error: {exc}")

        # 3. Try Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if anthropic_key:
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": os.environ.get("ANTHROPIC_VISION_MODEL", "claude-3-5-sonnet-20241022"),
                "max_tokens": 2048,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_data}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    return res["content"][0]["text"]
            except Exception as exc:
                print(f"[VISION SERVICE] Anthropic Vision error: {exc}")

        return None


vision_service = VisionService()
