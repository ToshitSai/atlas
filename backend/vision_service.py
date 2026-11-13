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

        # Inspect GIF frames if image is a GIF
        gif_note = ""
        keyframe_ocr_texts = []
        if mime_type == "image/gif":
            try:
                import io
                from PIL import Image
                gif_img = Image.open(io.BytesIO(content))
                n_frames = getattr(gif_img, "n_frames", 1)
                is_animated = getattr(gif_img, "is_animated", False)
                if is_animated or n_frames > 1:
                    gif_note = f"\nThis image is an animated GIF containing {n_frames} frames. Inspect and analyze content across frames.\n"
                    # Sample keyframes for OCR if multiple frames
                    key_indices = sorted(set([0, n_frames // 2, n_frames - 1]))
                    for f_idx in key_indices[1:]:
                        try:
                            gif_img.seek(f_idx)
                            frame_rgb = gif_img.convert("RGB")
                            f_buf = io.BytesIO()
                            frame_rgb.save(f_buf, format="PNG")
                            f_b64 = base64.b64encode(f_buf.getvalue()).decode("utf-8")
                            f_res = self._call_multimodal(
                                f"Extract any visible text in frame {f_idx + 1} of this animated GIF verbatim. Return only the text.",
                                f_b64, "image/png", timeout=15
                            )
                            if f_res and f_res.strip():
                                keyframe_ocr_texts.append(f"[Frame {f_idx + 1}]: {f_res.strip()}")
                        except Exception:
                            pass
            except Exception as gif_err:
                print(f"[VISION SERVICE] GIF inspection notice: {gif_err}")

        prompt = (
            "You are the Atlas Multimodal Vision Engine. Analyze this image thoroughly and accurately."
            + gif_note +
            "\nCRITICAL INSTRUCTIONS:\n"
            "1. OCR EXTRACTION: Extract ALL visible text, codes, identifiers, labels, numbers, table values, "
            "or mathematical formulas verbatim. If there is no text in the image, return an empty string \"\".\n"
            "2. VISUAL DESCRIPTION: Provide a detailed, factual visual description of what is depicted: "
            "the type of image (e.g. screenshot, photograph, architectural diagram, flowchart, chart, table, UI mockup, animated sequence), "
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

        if keyframe_ocr_texts:
            extra_ocr = "\n".join(keyframe_ocr_texts)
            ocr_text = f"{ocr_text}\n\nKeyframe Text:\n{extra_ocr}".strip() if ocr_text else extra_ocr

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
        system_prompt: Optional[str] = None,
        on_token: Optional[Any] = None
    ) -> Optional[str]:
        """Directly query a multimodal model about an uploaded image (Workflow A: chat attachment)."""
        return self.answer_multiple_images(
            question=question,
            images=[{"filename": filename, "content": content, "mime_type": get_image_mime(filename, content)}],
            system_prompt=system_prompt,
            on_token=on_token
        )

    def answer_multiple_images(
        self,
        question: str,
        images: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        on_token: Optional[Any] = None
    ) -> Optional[str]:
        """Directly query a multimodal vision model about one or more uploaded images.

        Enforces structured multi-image format:
        ### Image 1 — [Subject/Filename]
        ### Image 2 — [Subject/Filename]
        ### Overall
        """
        if not images:
            return None

        # Prepare normalized image entries
        prepared_images = []
        for idx, img in enumerate(images, 1):
            if isinstance(img, (tuple, list)):
                fn = str(img[0]) if len(img) > 0 and img[0] else f"image_{idx}.png"
                raw = img[1] if len(img) > 1 else b""
                mime = str(img[2]) if len(img) > 2 and img[2] else get_image_mime(fn, raw)
            elif isinstance(img, dict):
                fn = str(img.get("filename") or f"image_{idx}.png")
                raw = img.get("content") or img.get("bytes") or b""
                mime = str(img.get("mime_type") or get_image_mime(fn, raw))
            else:
                fn = f"image_{idx}.png"
                raw = img
                mime = get_image_mime(fn, raw)
            b64 = base64.b64encode(raw).decode("utf-8") if isinstance(raw, bytes) else str(raw)
            prepared_images.append({
                "index": idx,
                "filename": fn,
                "mime_type": mime,
                "b64": b64,
                "size_bytes": len(raw) if isinstance(raw, bytes) else 0
            })

        is_multi = len(prepared_images) > 1
        is_actionable = bool(re.search(
            r'\b(course|certificate|cert|link|enroll|how to (get|do|take)|where (can|to)|cost|price|register|fix|error|solve|recommend)\b',
            question or "",
            re.IGNORECASE
        ))

        if is_actionable:
            instructions = (
                f"You are Atlas AI, an intelligent multimodal assistant. The user has uploaded {len(prepared_images)} image(s) and asked:\n\n"
                f"\"{question}\"\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Read and extract all visible text, titles, course names, organizations, certifications, dates, and key identifiers from each image.\n"
                "2. Directly answer the user's specific request using the extracted information.\n"
                "3. Provide clear, structured, actionable guidance with course details, provider information, and direct enrollment steps."
            )
        elif is_multi:
            instructions = (
                f"You are Atlas AI, an advanced multimodal research assistant. The user has uploaded {len(prepared_images)} images and asked:\n\n"
                f"\"{question}\"\n\n"
                "CRITICAL MULTIMODAL INSTRUCTIONS:\n"
                "1. Analyze ALL provided images directly from their visual content.\n"
                "2. Provide your answer structured cleanly with these exact Markdown headings:\n\n"
            )
            for img in prepared_images:
                instructions += f"### Image {img['index']} — {img['filename']}\nDescribe visible subjects, appearance, colors, characters/clothing/features, visible text/labels, layout and design.\n\n"
            instructions += (
                "### Overall\nExplain the relationship, comparison, or synthesis between the images.\n\n"
                "3. Ground all statements strictly in the visible pixels of the provided images. Do not guess or extrapolate details that cannot be verified visually."
            )
        else:
            single = prepared_images[0]
            instructions = (
                f"You are Atlas AI, an advanced multimodal assistant. The user has attached the image `{single['filename']}` and asked:\n\n"
                f"User Question: \"{question}\"\n\n"
                "Answer directly, factually, and concisely using the visual and textual evidence in the image.\n"
                "If specific details asked about are not visible in the image, state that clearly."
            )

        resp = self._call_multimodal_multi(instructions, prepared_images, timeout=40)
        if resp and on_token:
            # Stream tokens to callback in smooth increments
            words = resp.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                try:
                    on_token(token)
                except Exception:
                    pass
        return resp

    def _call_multimodal_multi(
        self,
        prompt: str,
        images: List[Dict[str, Any]],
        timeout: int = 35
    ) -> Optional[str]:
        """Invoke configured multimodal vision provider (Gemini -> OpenAI -> Claude) with multiple images."""
        # 1. Try Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            candidate_models = [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-flash-lite-latest",
                "gemini-flash-latest",
                "gemini-3.1-flash-lite-preview",
                "gemini-3-flash-preview",
                "gemini-2.5-pro",
            ]
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                parts: List[Dict[str, Any]] = [{"text": prompt}]
                for img in images:
                    parts.append({
                        "inline_data": {
                            "mime_type": img["mime_type"],
                            "data": img["b64"]
                        }
                    })
                payload = {
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=min(timeout, 15)) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        candidates = res.get("candidates", [])
                        if candidates:
                            c_parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join(p.get("text", "") for p in c_parts if isinstance(p, dict))
                            if text:
                                return text
                except urllib.error.HTTPError as http_err:
                    if http_err.code in (404, 429, 503):
                        continue
                    print(f"[VISION SERVICE] Gemini {model} HTTP {http_err.code}: {http_err.reason}")
                except Exception as exc:
                    print(f"[VISION SERVICE] Gemini {model} multi-image error: {exc}")

        # 2. Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            url = "https://api.openai.com/v1/chat/completions"
            content_list: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            for img in images:
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['mime_type']};base64,{img['b64']}"}
                })
            payload = {
                "model": os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": content_list}],
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
                print(f"[VISION SERVICE] OpenAI Vision multi-image error: {exc}")

        # 3. Try Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if anthropic_key:
            url = "https://api.anthropic.com/v1/messages"
            content_list_anthropic: List[Dict[str, Any]] = []
            for img in images:
                content_list_anthropic.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": img["mime_type"], "data": img["b64"]}
                })
            content_list_anthropic.append({"type": "text", "text": prompt})
            payload = {
                "model": os.environ.get("ANTHROPIC_VISION_MODEL", "claude-3-5-sonnet-20241022"),
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": content_list_anthropic}]
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
                print(f"[VISION SERVICE] Anthropic Vision multi-image error: {exc}")

        return None

    def _call_multimodal(
        self,
        prompt: str,
        b64_data: str,
        mime_type: str,
        timeout: int = 30
    ) -> Optional[str]:
        """Invoke configured multimodal vision provider (Gemini -> OpenAI -> Claude) for a single image."""
        return self._call_multimodal_multi(
            prompt,
            [{"mime_type": mime_type, "b64": b64_data, "filename": "image"}],
            timeout=timeout
        )


vision_service = VisionService()
