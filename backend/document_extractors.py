"""Atlas AI — Multi-Format Document Extraction Suite.

Supports:
- PDF (selectable text & scanned PDF OCR)
- DOCX, DOC (Word documents & tables)
- XLSX, XLS (Spreadsheets & structured tables)
- PPTX, PPT (Presentations, slides & speaker notes)
- CSV, JSON, XML, HTML (Structured data)
- TXT, Markdown, Source Code (.py, .js, .ts, etc.)
- Images (PNG, JPG, JPEG, WEBP, GIF via Vision Engine)
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List, Optional

from backend.vision_service import (
    SUPPORTED_IMAGE_EXTENSIONS,
    get_image_mime,
    vision_service,
)

SUPPORTED_DOCUMENT_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".txt", ".md", ".markdown",
    # Spreadsheets
    ".csv", ".tsv", ".xlsx",
    # Structured Data
    ".json", ".html", ".htm", ".xml",
    # Presentations
    ".pptx",
    # Code
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
    ".rs", ".go", ".sql", ".sh", ".yaml", ".yml"
}

ALL_SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


def clean_text(text: str) -> str:
    """Strip null bytes, control characters, and collapse excessive blank lines."""
    if not text:
        return ""
    # Remove control characters except newline and tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(content: bytes, filename: str) -> List[Dict[str, Any]]:
    """Extract text, page numbers, and handle scanned PDFs via multimodal OCR."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        if getattr(reader, "is_encrypted", False):
            try:
                decrypted = reader.decrypt("")
                if not decrypted:
                    raise ValueError("This PDF is password-protected and cannot be decrypted.")
            except Exception as enc_err:
                raise ValueError("This PDF is password-protected and cannot be decrypted.") from enc_err
    except Exception as exc:
        if "password" in str(exc).lower() or "encrypt" in str(exc).lower() or "decrypt" in str(exc).lower():
            raise ValueError("This PDF is password-protected and cannot be decrypted.") from exc
        raise ValueError(f"Failed to parse PDF document: {exc}") from exc

    if len(reader.pages) == 0:
        raise ValueError("PDF document contains 0 pages.")

    pages: List[Dict[str, Any]] = []
    scanned_candidates: List[Tuple[int, bytes]] = []

    for idx, page in enumerate(reader.pages, 1):
        raw_text = (page.extract_text() or "").strip()
        cleaned = clean_text(raw_text)
        if cleaned:
            pages.append({
                "page": idx,
                "section": f"Page {idx}",
                "text": cleaned
            })
        else:
            # Check for embedded page image for scanned PDF handling
            try:
                for img_obj in page.images:
                    if hasattr(img_obj, "data") and img_obj.data:
                        scanned_candidates.append((idx, img_obj.data))
                if not page.images and "/Resources" in page and "/XObject" in page["/Resources"]:
                    xObject = page["/Resources"]["/XObject"].get_object()
                    for obj in xObject:
                        if xObject[obj]["/Subtype"] == "/Image":
                            data = xObject[obj].get_data()
                            if data:
                                scanned_candidates.append((idx, data))
            except Exception:
                pass

    # If no selectable text was found on any page, attempt scanned OCR
    if not pages:
        if scanned_candidates and vision_service.is_available():
            for p_num, img_bytes in scanned_candidates[:5]:  # Process up to 5 scanned pages
                try:
                    res = vision_service.analyze_image(f"scanned_p{p_num}.png", img_bytes)
                    ocr_t = res.get("ocr_text") or res.get("visual_description") or ""
                    if ocr_t:
                        pages.append({
                            "page": p_num,
                            "section": f"Page {p_num} (Scanned OCR)",
                            "text": ocr_t
                        })
                except Exception as ocr_err:
                    print(f"[PDF SCANNED OCR ERROR] Page {p_num}: {ocr_err}")

        if not pages:
            raise ValueError("PDF contains no selectable text layer; OCR is unavailable and no extractable scanned page images were found. Please upload a readable PDF or clear image.")

    return pages


def extract_docx(content: bytes) -> List[Dict[str, Any]]:
    """Extract headings, paragraphs, and tables from DOCX."""
    # Try python-docx first
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        sections: List[Dict[str, Any]] = []
        current_heading = "Introduction"
        current_paras: List[str] = []

        for para in doc.paragraphs:
            txt = clean_text(para.text)
            if not txt:
                continue
            if para.style.name.startswith("Heading"):
                if current_paras:
                    sections.append({
                        "page": None,
                        "section": current_heading,
                        "text": "\n\n".join(current_paras)
                    })
                    current_paras = []
                current_heading = txt
            else:
                current_paras.append(txt)

        if current_paras:
            sections.append({
                "page": None,
                "section": current_heading,
                "text": "\n\n".join(current_paras)
            })

        for t_idx, table in enumerate(doc.tables, 1):
            rows = []
            for row in table.rows:
                row_txt = " | ".join(clean_text(cell.text) for cell in row.cells)
                if row_txt.strip():
                    rows.append(row_txt)
            if rows:
                sections.append({
                    "page": None,
                    "section": f"Table {t_idx}",
                    "text": "\n".join(rows)
                })

        if sections:
            return sections
    except Exception:
        pass

    # Standard library fallback via zipfile + xml.etree
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            if "word/document.xml" in zf.namelist():
                xml_data = zf.read("word/document.xml")
                root = ET.fromstring(xml_data)
                texts = []
                # Namespace handling: search for all 't' (text) tags
                for elem in root.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        texts.append(elem.text)
                joined = clean_text(" ".join(texts))
                if joined:
                    return [{"page": None, "section": "Document", "text": joined}]
    except Exception as exc:
        raise ValueError(f"Failed to parse DOCX file: {exc}") from exc

    raise ValueError("DOCX document contains no readable text.")


def extract_doc_binary(content: bytes) -> List[Dict[str, Any]]:
    """Extract ASCII/UTF-8 strings from legacy DOC binary streams."""
    try:
        # Extract printable text blocks of length >= 6
        text_blocks = re.findall(rb"[\x20-\x7E\t\r\n]{6,}", content)
        decoded = [b.decode("ascii", errors="ignore").strip() for b in text_blocks]
        clean_blocks = [b for b in decoded if len(b) > 10 and not b.startswith("<?xml")]
        joined = clean_text("\n\n".join(clean_blocks))
        if joined:
            return [{"page": None, "section": "Legacy DOC Text", "text": joined}]
    except Exception:
        pass
    raise ValueError("Legacy DOC file contains no extractable text.")


def extract_xlsx(content: bytes) -> List[Dict[str, Any]]:
    """Extract sheets, column headers, and data tables from Excel XLSX."""
    # Try openpyxl first
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sections: List[Dict[str, Any]] = []

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows: List[List[str]] = []
            for row in sheet.iter_rows(values_only=True):
                str_row = [clean_text(str(c)) if c is not None else "" for c in row]
                if any(str_row):
                    rows.append(str_row)

            if not rows:
                continue

            # Format as Markdown table
            headers = rows[0]
            header_line = "| " + " | ".join(h or f"Col_{i+1}" for i, h in enumerate(headers)) + " |"
            sep_line = "| " + " | ".join("---" for _ in headers) + " |"
            table_lines = [header_line, sep_line]

            for r in rows[1:]:
                # Pad row to header length
                padded = r + [""] * (len(headers) - len(r))
                table_lines.append("| " + " | ".join(padded[:len(headers)]) + " |")

            table_text = "\n".join(table_lines)
            sections.append({
                "page": None,
                "section": f"Spreadsheet: {sheet_name}",
                "text": f"### Sheet: {sheet_name}\n\n{table_text}"
            })

        if sections:
            return sections
    except Exception:
        pass

    # Standard library fallback via zipfile + xml.etree
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            shared_strings = []
            if "xl/sharedStrings.xml" in zf.namelist():
                ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for elem in ss_root.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        shared_strings.append(elem.text)

            sheet_texts = []
            for name in zf.namelist():
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                    sh_root = ET.fromstring(zf.read(name))
                    cell_vals = []
                    for c in sh_root.iter():
                        if c.tag.endswith("}v") and c.text:
                            val = c.text
                            if c.get("t") == "s" and val.isdigit() and int(val) < len(shared_strings):
                                val = shared_strings[int(val)]
                            cell_vals.append(val)
                    if cell_vals:
                        sheet_texts.append(" | ".join(cell_vals))

            if sheet_texts:
                return [{"page": None, "section": "Excel Data", "text": "\n".join(sheet_texts)}]
    except Exception as exc:
        raise ValueError(f"Failed to parse Excel file: {exc}") from exc

    raise ValueError("Excel file contains no readable tabular data.")


def extract_xls_binary(content: bytes) -> List[Dict[str, Any]]:
    """Extract readable text and numbers from legacy XLS binary."""
    text_blocks = re.findall(rb"[\x20-\x7E\t\r\n]{4,}", content)
    decoded = [b.decode("ascii", errors="ignore").strip() for b in text_blocks]
    clean_blocks = [b for b in decoded if len(b) > 3]
    joined = clean_text(" | ".join(clean_blocks))
    if joined:
        return [{"page": None, "section": "Legacy XLS Data", "text": joined}]
    raise ValueError("Legacy XLS file contains no readable data.")


def extract_pptx(content: bytes) -> List[Dict[str, Any]]:
    """Extract slide titles, body text, tables, and speaker notes from PowerPoint PPTX."""
    # Try python-pptx first
    try:
        import pptx
        prs = pptx.Presentation(io.BytesIO(content))
        sections: List[Dict[str, Any]] = []

        for idx, slide in enumerate(prs.slides, 1):
            slide_title = f"Slide {idx}"
            slide_lines: List[str] = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        t = clean_text(para.text)
                        if t:
                            if not slide_lines and shape == slide.shapes[0]:
                                slide_title = t
                            slide_lines.append(t)
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_t = " | ".join(clean_text(cell.text) for cell in row.cells)
                        if row_t.strip():
                            slide_lines.append(row_t)

            # Check for speaker notes
            notes_text = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = clean_text(slide.notes_slide.notes_text_frame.text)

            body_content = "\n\n".join(slide_lines)
            if notes_text:
                body_content += f"\n\n**Speaker Notes:**\n{notes_text}"

            if body_content.strip():
                sections.append({
                    "page": idx,
                    "section": f"Slide {idx}: {slide_title}",
                    "text": f"### Slide {idx}: {slide_title}\n\n{body_content}"
                })

        if sections:
            return sections
    except Exception:
        pass

    # Standard library fallback via zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            slide_files = sorted([f for f in zf.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")])
            sections = []
            for s_idx, sf in enumerate(slide_files, 1):
                root = ET.fromstring(zf.read(sf))
                slide_texts = []
                for elem in root.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        slide_texts.append(elem.text)
                if slide_texts:
                    sections.append({
                        "page": s_idx,
                        "section": f"Slide {s_idx}",
                        "text": f"### Slide {s_idx}\n\n" + " ".join(slide_texts)
                    })
            if sections:
                return sections
    except Exception as exc:
        raise ValueError(f"Failed to parse PowerPoint file: {exc}") from exc

    raise ValueError("PowerPoint presentation contains no readable slides.")


def extract_ppt_binary(content: bytes) -> List[Dict[str, Any]]:
    """Extract strings from legacy PPT binary."""
    text_blocks = re.findall(rb"[\x20-\x7E\t\r\n]{6,}", content)
    decoded = [b.decode("ascii", errors="ignore").strip() for b in text_blocks]
    clean_blocks = [b for b in decoded if len(b) > 10 and not b.startswith("<?xml")]
    joined = clean_text("\n\n".join(clean_blocks))
    if joined:
        return [{"page": None, "section": "Legacy PPT Presentation", "text": joined}]
    raise ValueError("Legacy PPT file contains no extractable text.")


def extract_csv(content: bytes) -> List[Dict[str, Any]]:
    """Extract CSV with header and structured rows."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("CSV document is empty.")

    header = rows[0]
    chunks: List[Dict[str, Any]] = []
    batch_size = 30

    for i in range(1, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        table_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |"
        ]
        for r in batch:
            padded = r + [""] * (len(header) - len(r))
            table_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        chunks.append({
            "page": None,
            "section": f"CSV Rows {i}-{min(len(rows)-1, i + batch_size - 1)}",
            "text": "\n".join(table_lines)
        })

    return chunks or [{"page": None, "section": "CSV Header", "text": " | ".join(header)}]


def extract_tsv(content: bytes) -> List[Dict[str, Any]]:
    """Extract TSV (Tab-Separated Values) with header and structured rows."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("TSV document is empty.")

    header = rows[0]
    chunks: List[Dict[str, Any]] = []
    batch_size = 30

    for i in range(1, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        table_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |"
        ]
        for r in batch:
            padded = r + [""] * (len(header) - len(r))
            table_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        chunks.append({
            "page": None,
            "section": f"TSV Rows {i}-{min(len(rows)-1, i + batch_size - 1)}",
            "text": "\n".join(table_lines)
        })

    return chunks or [{"page": None, "section": "TSV Header", "text": " | ".join(header)}]


def extract_json(content: bytes) -> List[Dict[str, Any]]:
    """Extract structured formatted JSON."""
    raw_data = json.loads(content.decode("utf-8", errors="replace"))
    formatted = json.dumps(raw_data, indent=2)
    if not formatted.strip() or formatted.strip() in ("{}", "[]"):
        raise ValueError("JSON file contains no data.")
    return [{"page": None, "section": "JSON Data", "text": formatted}]


def extract_xml(content: bytes) -> List[Dict[str, Any]]:
    """Extract elements, attributes, and text from XML documents."""
    try:
        root = ET.fromstring(content)
        lines = []

        def _traverse(node, depth=0):
            indent = "  " * depth
            attrs = " " + " ".join(f'{k}="{v}"' for k, v in node.attrib.items()) if node.attrib else ""
            txt = (node.text or "").strip()
            if txt:
                lines.append(f"{indent}<{node.tag}{attrs}>: {txt}")
            elif attrs:
                lines.append(f"{indent}<{node.tag}{attrs}>")
            for child in node:
                _traverse(child, depth + 1)

        _traverse(root)
        body = clean_text("\n".join(lines))
        if not body:
            raise ValueError("XML file contains no text elements.")
        return [{"page": None, "section": f"XML Root: <{root.tag}>", "text": body}]
    except ET.ParseError as err:
        raise ValueError(f"Invalid XML syntax: {err}") from err


def extract_html(content: bytes) -> List[Dict[str, Any]]:
    """Extract clean title and body text from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()
        text = clean_text(soup.get_text(separator="\n\n"))
        if not text:
            raise ValueError("HTML document contains no readable text.")
        title = soup.title.string.strip() if soup.title and soup.title.string else "HTML Document"
        return [{"page": None, "section": title, "text": text}]
    except Exception as exc:
        raise ValueError(f"Failed to parse HTML: {exc}") from exc


def extract_plain_text(content: bytes, ext: str) -> List[Dict[str, Any]]:
    """Extract plain text, Markdown, or source code."""
    text = clean_text(content.decode("utf-8", errors="replace"))
    if not text:
        raise ValueError("Document contains no text content.")
    section_name = "Markdown" if ext in (".md", ".markdown") else (f"Source Code ({ext})" if ext != ".txt" else "Document")
    return [{"page": None, "section": section_name, "text": text}]


def extract_document_or_image(
    filename: str,
    content: bytes,
    owner_session: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Main extraction dispatcher supporting all documents and images.
    
    Returns:
    (sections_list, extra_metadata_dict)
    """
    if not content or len(content.strip()) == 0:
        raise ValueError("Uploaded document is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File exceeds maximum allowed size (50 MB).")

    ext = os.path.splitext(filename.lower())[1]

    # Explicit rejection for legacy binary formats (DOC, XLS, PPT) or OLE CFBF magic bytes
    is_ole_magic = content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if ext in (".doc", ".xls", ".ppt") or (is_ole_magic and ext not in (".docx", ".xlsx", ".pptx")):
        clean_ext = ext.lstrip(".") or "doc"
        target_modern = "docx" if clean_ext == "doc" else ("xlsx" if clean_ext == "xls" else "pptx")
        raise ValueError(
            f"Legacy binary Microsoft Office format (.{clean_ext}) is not supported. "
            f"Please save or export your file as modern .{clean_ext}x (.{target_modern}) and upload again."
        )

    # Explicit rejection for video formats
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}
    is_video_magic = (
        (len(content) >= 12 and (content[4:8] == b"ftyp" or content[:12].startswith(b"\x00\x00\x00\x18ftyp") or content[:12].startswith(b"\x00\x00\x00\x20ftyp")))
        or content.startswith(b"\x1a\x45\xdf\xa3")  # Matroska / WebM
        or (content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"AVI ")
    )
    if ext in VIDEO_EXTENSIONS or is_video_magic:
        video_name = ext.lstrip(".") or "video"
        raise ValueError(
            f"Video format (.{video_name}) is not supported for document analysis or RAG. "
            "Please upload documents (PDF, DOCX, XLSX, PPTX, TXT) or still images (PNG, JPG, WEBP)."
        )

    if ext not in ALL_SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Supported: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
        )

    # 1. Images (.png, .jpg, .jpeg, .webp, .gif)
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        img_analysis = vision_service.analyze_image(filename, content, owner_session=owner_session)
        sections = img_analysis.get("sections") or []
        if not sections:
            raise ValueError("Failed to analyze image content.")
        meta = {
            "is_image": True,
            "mime_type": img_analysis.get("mime_type"),
            "image_type": img_analysis.get("image_type"),
            "ocr_text": img_analysis.get("ocr_text"),
            "visual_description": img_analysis.get("visual_description"),
            "key_entities": img_analysis.get("key_entities"),
        }
        return sections, meta

    # 2. PDF (.pdf)
    if ext == ".pdf":
        return extract_pdf(content, filename), {"is_image": False, "format": "pdf"}

    # 3. Word (.docx)
    if ext == ".docx":
        return extract_docx(content), {"is_image": False, "format": "docx"}

    # 4. Excel (.xlsx)
    if ext == ".xlsx":
        return extract_xlsx(content), {"is_image": False, "format": "xlsx"}

    # 5. PowerPoint (.pptx)
    if ext == ".pptx":
        return extract_pptx(content), {"is_image": False, "format": "pptx"}

    # 6. CSV and TSV (.csv, .tsv)
    if ext == ".csv":
        return extract_csv(content), {"is_image": False, "format": "csv"}
    if ext == ".tsv":
        return extract_tsv(content), {"is_image": False, "format": "tsv"}

    # 7. JSON (.json)
    if ext == ".json":
        return extract_json(content), {"is_image": False, "format": "json"}

    # 8. XML (.xml)
    if ext == ".xml":
        return extract_xml(content), {"is_image": False, "format": "xml"}

    # 9. HTML (.html, .htm)
    if ext in (".html", ".htm"):
        return extract_html(content), {"is_image": False, "format": "html"}

    # 10. Plain text, Markdown, and Source Code
    return extract_plain_text(content, ext), {"is_image": False, "format": ext.lstrip(".")}
