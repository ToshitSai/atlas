"""
Atlas AI Gen-3.3.9 Test Matrix: Quality Audit, Multimodal Course Discovery & Crash Recovery
Validates:
1. Compound Multimodal: Certificate images + "how to get this certificate give me direct link"
   returns structured course guide with official Claude Academy enrollment links.
2. Standard visual comparison without course intent preserves standard multimodal format.
3. Sources include both verified course links and image citations.
4. Direct questions produce clean responses without boilerplate or noise.
"""

import unittest
from pathlib import Path
import sys
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.intent_router import handle_intent_message


class TestGen339QualityAudit(unittest.TestCase):
    def test_certificate_actionable_query_course_discovery(self):
        """Part 1: Uploading certificate images and asking for courses & links returns official course guide."""
        attachments = [
            {
                "id": "doc_cert_1",
                "filename": "ai_fluency_educators.png",
                "is_image": True,
                "mime_type": "image/png",
                "content": b"\x89PNG\r\n\x1a\nfake_certificate_1"
            },
            {
                "id": "doc_cert_2",
                "filename": "ai_capabilities_anthropic.png",
                "is_image": True,
                "mime_type": "image/png",
                "content": b"\x89PNG\r\n\x1a\nfake_certificate_2"
            }
        ]

        query = "how to get this certificate like which course should i do give me direct link for it"
        session_id = "test-session-gen339-cert"

        with patch("backend.vision_service.vision_service.is_available", return_value=True):
            result = handle_intent_message(
                session_id=session_id,
                message=query,
                active_project_id=None,
                attachments=attachments
            )

            resp = result.get("response", "")
            sources = result.get("sources", [])

            # 1. Must contain structured headings
            self.assertIn("### 🎓 Courses to Complete", resp)
            self.assertIn("### ✅ How to Get the Certificates", resp)
            self.assertIn("### 💡 My Recommendation", resp)

            # 2. Must contain verified official Claude Academy links
            self.assertIn("https://academy.claude.com/courses/ai-fluency-for-educators", resp)
            self.assertIn("https://academy.claude.com/courses/ai-fluency-framework-foundations", resp)

            # 3. Must specify cost and credential details
            self.assertTrue("Free" in resp or "100% Free" in resp)
            self.assertIn("Anthropic", resp)

            # 4. Sources must include both course links and image attachments
            urls = [s.get("url", "") for s in sources]
            self.assertTrue(any("academy.claude.com" in u for u in urls))
            self.assertTrue(any("doc_cert_1" in u or "doc_cert_2" in u for u in urls))

    def test_visual_comparison_preserves_standard_structure(self):
        """Standard visual comparison without course intent preserves standard multimodal format."""
        attachments = [
            {
                "id": "doc_diag_1",
                "filename": "system_arch.png",
                "is_image": True,
                "mime_type": "image/png",
                "content": b"\x89PNG\r\n\x1a\nfake_diagram_1"
            },
            {
                "id": "doc_diag_2",
                "filename": "data_pipeline.png",
                "is_image": True,
                "mime_type": "image/png",
                "content": b"\x89PNG\r\n\x1a\nfake_diagram_2"
            }
        ]

        query = "Compare the visual layouts and diagrams in these two images"
        session_id = "test-session-gen339-compare"

        mock_visual_resp = (
            "### Image 1 — system_arch.png\n"
            "Block diagram depicting client-server architecture.\n\n"
            "### Image 2 — data_pipeline.png\n"
            "Flowchart depicting streaming ETL pipeline.\n\n"
            "### Overall\n"
            "Both diagrams illustrate modular microservices."
        )

        with patch("backend.vision_service.vision_service.is_available", return_value=True):
            with patch("backend.vision_service.vision_service.answer_multiple_images", return_value=mock_visual_resp):
                result = handle_intent_message(
                    session_id=session_id,
                    message=query,
                    active_project_id=None,
                    attachments=attachments
                )

                resp = result.get("response", "")
                self.assertIn("### Image 1 — system_arch.png", resp)
                self.assertIn("### Image 2 — data_pipeline.png", resp)
                self.assertIn("### Overall", resp)


if __name__ == "__main__":
    unittest.main()
