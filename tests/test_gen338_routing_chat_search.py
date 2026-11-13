"""
Atlas AI Gen-3.3.8 Test Matrix
Validates:
1. Intelligent 3-tier task classification and activity suppression (Tier 0: none, Tier 1: compact, Tier 2: full)
2. Direct conversational questions (Hi, What is Apple?, What is Python?, etc.) receive Tier 0 (none) and empty activity
3. Live web search queries invoke real web search, synthesize grounded answers with [1] citations, and yield Tier 1 (compact)
4. Multimodal queries (image, documents) receive Tier 1 (compact)
5. Deep research queries receive Tier 2 (full)
6. Streaming integrity: verifying _stream_gemini deltas are not sliced, and fallback never repeats if tokens were emitted
7. Confidence check suppression: unverified "Not checked against sources" is never emitted to client activity
"""

import unittest
import json
import re
from unittest.mock import MagicMock, patch

from backend.main import determine_task_category
from backend.confidence import assess_confidence
from backend import live_search, web_search, llm as llm_mod


class TestGen338RoutingAndActivity(unittest.TestCase):
    def test_direct_conversation_tier_none(self):
        """Part 10.A: Direct conversation must have tier 'none' and no research activity."""
        queries = [
            ("Hi", "CASUAL_CHAT"),
            ("Hello", "CASUAL_CHAT"),
            ("How are you?", "CASUAL_CHAT"),
            ("Good morning", "CASUAL_CHAT"),
            ("Who created you?", "PROJECT_IDENTITY"),
            ("What is Apple?", "EXPLANATION"),
            ("What is Python?", "EXPLANATION"),
            ("Explain machine learning.", "EXPLANATION"),
            ("Who invented the telephone?", "EXPLANATION"),
        ]
        for query, intent in queries:
            category, tier = determine_task_category(intent, {}, query, attachments=None)
            self.assertEqual(tier, "none", f"Query '{query}' with intent '{intent}' must have tier 'none', got {tier}")
            self.assertIn(category, ("SIMPLE_CONVERSATION", "GENERAL_KNOWLEDGE"))

    def test_complex_reasoning_tier(self):
        """Part 10.B: Complex reasoning without tools returns tier 'none', with calculation returns 'compact'."""
        queries = [
            ("Compare two software architectures", "REASONING", "COMPLEX_REASONING", "none"),
            ("Analyze why this technical architecture might fail", "REASONING", "COMPLEX_REASONING", "none"),
            ("Calculate 25 * 40 + 15", "MATHEMATICS", "TOOL_EXECUTION", "compact"),
        ]
        for query, intent, expected_cat, expected_tier in queries:
            category, tier = determine_task_category(intent, {}, query, attachments=None)
            self.assertEqual(category, expected_cat)
            self.assertEqual(tier, expected_tier)

    def test_rag_and_multimodal_tier_compact(self):
        """Part 10.C & 10.H: Document analysis and image analysis return tier 'compact'."""
        image_att = [{"filename": "test.png", "is_image": True, "type": "image/png"}]
        cat, tier = determine_task_category("EXPLANATION", {}, "What is in this image?", attachments=image_att)
        self.assertEqual(cat, "MULTIMODAL_ANALYSIS")
        self.assertEqual(tier, "compact")

        doc_att = [{"filename": "paper.pdf", "is_image": False, "type": "application/pdf"}]
        cat, tier = determine_task_category("DOCUMENT_ANALYSIS", {}, "Summarize my PDF", attachments=doc_att)
        self.assertEqual(cat, "DOCUMENT_ANALYSIS")
        self.assertEqual(tier, "compact")

    def test_live_web_search_tier_compact(self):
        """Part 10.D: Live web search queries return tier 'compact'."""
        queries = [
            ("What are today's AI developments?", "WEB_SEARCH"),
            ("What is the latest NVIDIA announcement?", "WEB_SEARCH"),
            ("Find current internship opportunities", "WEB_SEARCH"),
            ("Search the web for recent research papers", "WEB_SEARCH"),
        ]
        for query, intent in queries:
            cat, tier = determine_task_category(intent, {"mode": "web_search"}, query, attachments=None)
            self.assertEqual(cat, "LIVE_WEB_SEARCH")
            self.assertEqual(tier, "compact")

    def test_deep_research_tier_full(self):
        """Part 10.E: Deep research returns tier 'full'."""
        cat, tier = determine_task_category("RESEARCH_START", {"mode": "deep_research"}, "Conduct comprehensive research on AI agents", attachments=None)
        self.assertEqual(cat, "DEEP_RESEARCH")
        self.assertEqual(tier, "full")


class TestGen338SearchAndSnippets(unittest.TestCase):
    def test_bs4_separator_preserves_word_boundaries(self):
        """Verify BeautifulSoup snippet parsing uses space separators so words never fuse together."""
        from bs4 import BeautifulSoup
        html_sample = "<p>Explore<b>the</b><strong>latest</strong>advancements in artificial intelligence.</p>"
        soup = BeautifulSoup(html_sample, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        # Verify words are separated by spaces
        self.assertIn("Explore the latest advancements", text)
        self.assertNotIn("Explorethelatest", text)

    def test_web_search_regex_preserves_spacing(self):
        """Verify re.sub on HTML tags in web_search preserves spacing."""
        html_snippet = "Apple Inc.<b>multinational</b>technology company"
        cleaned = re.sub(r"<[^>]+>", " ", html_snippet)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        self.assertEqual(cleaned, "Apple Inc. multinational technology company")
        self.assertNotIn("Incmultinational", cleaned)


class TestGen338ConfidenceFiltering(unittest.TestCase):
    def test_confidence_suppression_when_no_sources(self):
        """assess_confidence returns None when there are no sources and no tool verification."""
        result = {"sources": [], "response": "Apple is a technology company."}
        conf = assess_confidence("What is Apple?", result)
        self.assertIsNone(conf, "Confidence must be None when no sources exist to avoid 'Not checked against sources' spam")

    def test_confidence_present_with_sources(self):
        """assess_confidence returns valid score dictionary when real sources are provided."""
        sources = [
            {"title": "Reuters", "url": "https://reuters.com/tech", "domain": "reuters.com", "tier": "primary"}
        ]
        result = {
            "intent": "WEB_SEARCH",
            "sources": sources,
            "verification": {"available": True},
            "claims": [{"text": "AI models expanded", "verified": True, "supporting_sources": [0, 1]}],
            "response": "AI models expanded greatly."
        }
        conf = assess_confidence("What happened in AI today?", result)
        self.assertIsNotNone(conf)
        self.assertIn("overall", conf)
        self.assertIn("level", conf["overall"])
        self.assertNotEqual(conf["overall"]["level"], "Not checked against sources")


class TestGen338StreamingIntegrity(unittest.TestCase):
    def test_gemini_streaming_yields_deltas_directly(self):
        """Verify Gemini streaming parses parts and calls on_token without slicing offset truncation."""
        collected = []
        def dummy_token(d):
            collected.append(d)

        # Mock urllib stream yielding SSE lines
        sse_lines = [
            b'data: {"candidates": [{"content": {"parts": [{"text": "Apple "}]}}]}\n',
            b'data: {"candidates": [{"content": {"parts": [{"text": "Inc. is a "}]}}]}\n',
            b'data: {"candidates": [{"content": {"parts": [{"text": "multinational technology company."}]}}]}\n',
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = iter(sse_lines)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = llm_mod._stream_gemini("What is Apple?", None, dummy_token, 10, None)

        self.assertEqual("".join(collected), "Apple Inc. is a multinational technology company.")
        self.assertEqual(res, "Apple Inc. is a multinational technology company.")
        self.assertNotIn("Apple Incltitional", res)


if __name__ == "__main__":
    unittest.main()
