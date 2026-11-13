"""Atlas AI Gen-3.3.7: Premium AI Experience, Multi-Image Multimodal UX & Activity Contract Test Suite."""

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.vision_service import VisionService, vision_service
from backend.intent_router import handle_intent_message, load_image_bytes


class TestGen337PremiumExperience(unittest.TestCase):
    """Unit tests for Gen-3.3.7 multi-image understanding, activity events, and streaming contract."""

    def test_multi_image_structure_enforcement(self):
        """Verify VisionService multi-image analysis generates structured Markdown headings."""
        service = VisionService()

        mock_response = (
            "### Image 1 — chico_sheet.png\n"
            "Chico character sheet depicting turnaround poses, facial expressions, and color palette.\n\n"
            "### Image 2 — company_logo.png\n"
            "Geometric vector logo with minimalist typography and primary brand colors.\n\n"
            "### Overall\n"
            "The character design harmonizes well with the modern logo aesthetics."
        )

        tokens_received = []
        def dummy_token_cb(token):
            tokens_received.append(token)

        images = [
            ("chico_sheet.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."),
            ("company_logo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."),
        ]

        with patch.object(service, "_call_multimodal_multi", return_value=mock_response):
            result = service.answer_multiple_images(
                question="Compare these two images and summarize the visual identity.",
                images=images,
                on_token=dummy_token_cb,
            )

            self.assertIn("### Image 1 — chico_sheet.png", result)
            self.assertIn("### Image 2 — company_logo.png", result)
            self.assertIn("### Overall", result)
            self.assertTrue(len(tokens_received) > 0)

    def test_multi_image_single_image_backward_compatibility(self):
        """Verify VisionService handles 1 image seamlessly with consistent structure."""
        service = VisionService()
        mock_response = (
            "### Image 1 — architecture_diagram.png\n"
            "Cloud architecture diagram showing microservices connected to Redis and PostgreSQL.\n\n"
            "### Overall\n"
            "Clean separation between API gateway, authentication service, and persistence layer."
        )

        images = [("architecture_diagram.png", b"\x89PNG\r\n\x1a\nfake")]
        with patch.object(service, "_call_multimodal_multi", return_value=mock_response):
            result = service.answer_multiple_images(
                question="What does this diagram depict?",
                images=images,
            )
            self.assertIn("### Image 1 — architecture_diagram.png", result)
            self.assertIn("### Overall", result)

    def test_multimodal_intent_detection(self):
        """Verify intent router detects image attachments and routes to MULTIMODAL_IMAGE_ANALYSIS."""
        attachments = [
            {"id": "doc_img_1", "filename": "chico.png", "is_image": True},
            {"id": "doc_img_2", "filename": "logo.png", "is_image": True},
        ]

        mock_bytes = b"\x89PNG\r\n\x1a\nfake_image_bytes"
        mock_answer = (
            "### Image 1 — chico.png\n"
            "Analysis of Chico character sheet.\n\n"
            "### Image 2 — logo.png\n"
            "Analysis of logo design.\n\n"
            "### Overall\n"
            "Visual comparison between character and logo."
        )

        with patch("backend.intent_router.load_image_bytes", return_value=mock_bytes):
            with patch("backend.vision_service.vision_service.is_available", return_value=True):
                with patch("backend.vision_service.vision_service.answer_multiple_images", return_value=mock_answer):
                    activities = []
                    def on_activity(act):
                        activities.append(act)

                    response = handle_intent_message(
                        message="Compare the visual design of these two assets",
                        session_id="test-session-337",
                        attachments=attachments,
                        activity_callback=on_activity,
                    )

                    self.assertEqual(response.get("intent"), "MULTIMODAL_IMAGE_ANALYSIS")
                    text_resp = response.get("response", "")
                    self.assertIn("### Image 1 — chico.png", text_resp)
                    self.assertIn("### Image 2 — logo.png", text_resp)
                    self.assertIn("### Overall", text_resp)

                    # Verify activity events were emitted without exposing internal thoughts
                    self.assertTrue(len(activities) >= 2)
                    for act in activities:
                        self.assertIn("stage", act)
                        self.assertIn("label", act)
                        self.assertIn("status", act)
                        self.assertNotIn("chain_of_thought", act)
                        self.assertNotIn("raw_prompt", act)

    def test_operational_activity_contract(self):
        """Verify activity events follow the required public operational structure."""
        activities = []
        def capture_activity(act):
            activities.append(act)

        dummy_results = [{
            "title": "Transformers Architecture",
            "url": "https://arxiv.org/abs/1706.03762",
            "snippet": "Attention Is All You Need paper details.",
            "date": "2017-06-12"
        }]

        with patch("backend.intent_router.classify_intent", return_value="WEB_SEARCH"):
            with patch("backend.intent_router.query_llm", return_value="Synthesis of latest transformers research."):
                with patch("backend.web_search.search_web", return_value=dummy_results):
                    response = handle_intent_message(
                        message="Search for the latest research papers published today on transformers",
                        session_id="test-session-search",
                        activity_callback=capture_activity,
                    )

        # Confirm activity structure
        self.assertTrue(len(activities) > 0)
        for act in activities:
            self.assertIn("stage", act)
            self.assertIn("label", act)
            self.assertIn("status", act)
            self.assertIn("timestamp", act)
            self.assertNotIn("chain_of_thought", act)

        # Confirm sources returned
        self.assertTrue(len(response.get("sources", [])) > 0)
        self.assertEqual(response["sources"][0]["domain"], "arxiv.org")

    def test_no_simulated_streaming_delay(self):
        """Verify that streaming response handlers deliver actual tokens immediately."""
        import inspect
        from backend import intent_router
        source = inspect.getsource(intent_router.handle_intent_message)
        self.assertNotIn("time.sleep(0.012)", source)
        self.assertNotIn("time.sleep(0.05)", source)


if __name__ == "__main__":
    unittest.main()
