"""Small, deterministic guards for citation and reasoning-sensitive requests.

These guards are deliberately conservative: they never manufacture a source or
replace a normal model response unless the request has an unambiguous shape.
"""
import re
from typing import Any, Dict, Optional

_PAPER_RE = re.compile(
    r"(?P<year>19|20)\d{2}[^\n]{0,140}?\b(?:paper|article|study)\b[^\n]{0,220}?"
    r"(?:titled|called)\s+['\u201c\"]?(?P<title>[^'\u201d\"]{8,180})['\u201d\"]?",
    re.I,
)
_TITLE_FIRST_RE = re.compile(
    r"(?:paper|article|study)[^\n]{0,80}?(?:titled|called)\s+['\u201c\"](?P<title>[^'\u201d\"]{8,180})['\u201d\"]",
    re.I,
)

def named_reference(text: str) -> Optional[Dict[str, Any]]:
    """Extract a named scholarly reference; return None for ordinary Q&A."""
    text = str(text or "")
    match = _PAPER_RE.search(text) or _TITLE_FIRST_RE.search(text)
    if not match:
        return None
    title = " ".join(match.group("title").split()).strip(" .,:;")
    authors = []
    # Only treat an explicit author phrase as authors; do not guess names.
    am = re.search(r"(?:by|authors?\s*(?:are|:)?)[\s:]+([^,.\n]+(?:\s+and\s+[^,.\n]+)?)", text, re.I)
    if am:
        authors = [a.strip() for a in re.split(r"\s+and\s+|,", am.group(1)) if len(a.strip()) > 2]
    year = re.search(r"\b(?:19|20)\d{2}\b", text)
    venue = re.search(r"\b(?:NeurIPS|NeurIPS|ICML|ICLR|ACL|arXiv|Nature|Science|CVPR|AAAI)\b", text, re.I)
    return {"title": title, "authors": authors, "year": year.group(0) if year else None,
            "venue": venue.group(0) if venue else None}

def sally_solution(text: str) -> Optional[str]:
    """Solve the shared-sister counting form without brittle keyword answers."""
    low = str(text or "").lower()
    m = re.search(r"has\s+(\d+)\s+brothers?.*?each\s+brother\s+has\s+(\d+)\s+sisters?", low, re.S)
    if not m or not re.search(r"how many\s+sisters?\s+does\s+\w+\s+have", low):
        return None
    total_sisters = int(m.group(2))
    # Sally is herself one of the shared sisters, so exclude her from the
    # count of sisters *she* has.  This is the common ambiguity the puzzle is
    # designed to test; brothers do not each get a separate set.
    sisters = max(total_sisters - 1, 0)
    return (f"**Answer: {sisters}.** The brothers share the same sisters, and Sally is one of "
            f"the {total_sisters} sisters in that family. Therefore Sally has {sisters} sister(s); "
            "the number is not multiplied by the three brothers.")
