"""Atlas AI Gen-4 — Test Matrix for Research Intelligence & Signature Capabilities.

Verifies:
1. Research Continuity Engine: Objective tracking, decision recording, failed approach recall, brief synthesis
2. Experiment Intelligence Engine: Target leakage detection, temporal leakage detection, metric appropriateness, baseline evaluation
3. Evidence Ledger: Claim recording, contradiction detection, knowledge gap identification
4. Knowledge Connections Graph: Multi-source nodes, relations, and contradiction traversal
5. Adaptive Tool Intelligence: Tool intent selection (Python, Search, RAG, Experiment DB)
6. Honest Model Router: Provenance attribution, local vs cloud execution target tracking
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.research_continuity import research_continuity, ResearchContext
from backend.experiment_intelligence import experiment_intelligence
from backend.evidence_ledger import evidence_ledger, EvidenceType, VerificationStatus
from backend.knowledge_graph import knowledge_graph, RelationType
from backend.tool_intelligence import tool_intelligence, model_router
from backend.intelligence import execution_metadata


class TestGen4ResearchIntelligence(unittest.TestCase):
    def test_01_research_continuity_engine(self):
        """Verify long-term project context, decisions, and failed approach persistence."""
        pid = "test_proj_gen4_continuity"
        ctx = research_continuity.get_or_create_context(pid, "Project Quantum Orbit")
        self.assertIsNotNone(ctx)

        # Record objective
        obj = research_continuity.record_objective(pid, "Achieve 85% F1", "Train transformer on imbalanced sensor data")
        self.assertEqual(obj["title"], "Achieve 85% F1")

        # Record decision
        dec = research_continuity.record_decision(pid, "Use QLoRA 4-bit", "Workstation limited to 8GB VRAM")
        self.assertIn("8GB VRAM", dec["rationale"])

        # Record failed approach
        fail = research_continuity.record_failed_approach(pid, "Learning rate 1e-3", "Loss divergence / NaN", "Cap LR at 1.8e-4")
        self.assertEqual(fail["approach"], "Learning rate 1e-3")

        # Record experiment outcome
        exp = research_continuity.record_experiment_outcome(pid, "run_qlora_alpha32", {"lr": 1.8e-4}, {"loss": 0.9024}, "Converged cleanly")
        self.assertEqual(exp["name"], "run_qlora_alpha32")

        # Verify brief generation
        brief = research_continuity.build_continuity_prompt_brief(pid)
        self.assertIn("Project Quantum Orbit", brief)
        self.assertIn("Achieve 85% F1", brief)
        self.assertIn("Use QLoRA 4-bit", brief)
        self.assertIn("DO NOT REPEAT", brief)
        self.assertIn("Learning rate 1e-3", brief)

    def test_02_experiment_intelligence_target_leakage(self):
        """Verify detection of target leakage and recommendation generation."""
        features = ["transaction_amount", "merchant_category", "is_chargeback_confirmed", "user_age"]
        target = "is_fraud"

        critique = experiment_intelligence.critique_experiment(
            experiment_id="exp_fraud_audit",
            features=features,
            target=target,
            task_type="classification",
            chosen_metrics=["accuracy"],
            target_distribution={"fraud": 0.01, "legitimate": 0.99},
            baseline_name="None",
            baseline_score=None,
            proposed_score=0.998,
        )

        self.assertFalse(critique.is_valid)
        self.assertLess(critique.overall_confidence, 0.5)

        # Verify chargeback was flagged
        leaks = [l["feature_name"] for l in critique.detected_leakages]
        self.assertIn("is_chargeback_confirmed", leaks)

        # Verify accuracy on imbalanced data was critiqued
        self.assertFalse(critique.metric_critique["is_appropriate"])
        self.assertTrue(any("imbalanced" in f.lower() for f in critique.metric_critique["flaws"]))

        # Verify baseline critique
        self.assertFalse(critique.baseline_assessment["valid"])

    def test_03_experiment_intelligence_temporal_leakage(self):
        """Verify temporal leakage detection on shuffled time-series data."""
        features = ["open_price", "volume", "rsi_14"]
        target = "close_price"

        risks = experiment_intelligence.detect_data_leakage(
            features=features,
            target=target,
            split_method="random",
            is_time_series=True,
        )
        risk_names = [r.feature_name for r in risks]
        self.assertIn("global_split_strategy", risk_names)
        temporal_risk = next(r for r in risks if r.feature_name == "global_split_strategy")
        self.assertEqual(temporal_risk.risk_level, "CRITICAL")
        self.assertIn("TimeSeriesSplit", temporal_risk.recommendation)

    def test_04_evidence_ledger_and_contradictions(self):
        """Verify claim recording, contradiction flags, and knowledge gap detection."""
        cid = "session_test_evidence"
        claim_1 = evidence_ledger.record_claim(
            context_id=cid,
            text="Model achieved 83.3% accuracy on GSM8K evaluation.",
            evidence_type=EvidenceType.EXPERIMENT_RECORD,
            status=VerificationStatus.CONFIRMED,
            source_id="eval_report_gen3",
            confidence=0.98,
        )
        self.assertEqual(claim_1.status, VerificationStatus.CONFIRMED)

        claim_2 = evidence_ledger.record_claim(
            context_id=cid,
            text="Model failed all math questions on GSM8K.",
            evidence_type=EvidenceType.MODEL_INFERENCE,
            status=VerificationStatus.UNVERIFIED,
            source_id="user_claim",
            confidence=0.30,
        )

        # Flag contradiction
        flagged = evidence_ledger.flag_contradiction(
            cid, claim_1.id, claim_2.id, "Empirical logs show 83.3% accuracy, contradicting the failure claim."
        )
        self.assertTrue(flagged)
        self.assertEqual(claim_1.status, VerificationStatus.CONTRADICTED)
        self.assertEqual(claim_2.contradicting_claim_id, claim_1.id)

        # Detect knowledge gaps
        gaps = evidence_ledger.detect_knowledge_gaps(
            required_questions=["What is the quantum encryption key for the server?"],
            available_claims=[claim_1, claim_2],
        )
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["status"], "MISSING_EVIDENCE")

    def test_05_knowledge_connections_graph(self):
        """Verify knowledge graph nodes, edges, and contradiction traversal."""
        n1 = knowledge_graph.add_node("concept_qlora", "QLoRA 4-bit Quantization", "CONCEPT")
        n2 = knowledge_graph.add_node("dataset_scibench", "SciBench Reasoning", "DATASET")
        n3 = knowledge_graph.add_node("claim_convergence", "Instant 1-step Convergence Claim", "CLAIM")

        knowledge_graph.add_edge(n1.id, n2.id, RelationType.EVALUATES_ON)
        knowledge_graph.add_edge(n1.id, n3.id, RelationType.CONTRADICTS, evidence_id="exp_convergence_log")

        related = knowledge_graph.get_related_nodes(n1.id)
        self.assertEqual(len(related), 2)

        contradictions = knowledge_graph.find_contradictions()
        self.assertTrue(any(c["source"] == "QLoRA 4-bit Quantization" for c in contradictions))

    def test_06_adaptive_tool_intelligence(self):
        """Verify tool selection logic for math, search, experiments, and documents."""
        # Math query
        t_calc = tool_intelligence.select_tools("Calculate the square root of 5000 * 3.1415")
        self.assertTrue(any(t.tool_name == "python_calculator" for t in t_calc))

        # Real-time search query
        t_search = tool_intelligence.select_tools("What are the latest benchmark scores for DeepSeek-R1 published today?")
        self.assertTrue(any(t.tool_name == "web_search" for t in t_search))

        # Experiment store query
        t_exp = tool_intelligence.select_tools("Which model performed best across our experiments?", has_project=True)
        self.assertTrue(any(t.tool_name == "experiment_db" for t in t_exp))

        # Document RAG query
        t_rag = tool_intelligence.select_tools("According to the uploaded document, what was the learning rate?", has_attachments=True)
        self.assertTrue(any(t.tool_name == "document_rag" for t in t_rag))

    def test_07_honest_model_router_and_telemetry(self):
        """Verify model routing provenance and honest attribution."""
        # Multimodal images route to frontier vision model
        route_vision = model_router.route_request("Analyze this chart", has_vision_attachments=True)
        self.assertEqual(route_vision.execution_target, "cloud_frontier")
        self.assertIn("Multimodal", route_vision.selected_model)

        # Deep research routes to frontier reasoning
        route_deep = model_router.route_request("Deep comprehensive investigation", requires_deep_research=True)
        self.assertEqual(route_deep.execution_target, "cloud_frontier")

        # Execution metadata integration
        meta = execution_metadata("Explain how to prevent data leakage in ML experiments", {"intent": "EXPLANATION", "response": "Use TimeSeriesSplit."})
        self.assertIn("model_provenance", meta)
        self.assertIn("signature_intelligence", meta)
        self.assertTrue(meta["signature_intelligence"]["experiment_intelligence"])
        self.assertTrue(meta["signature_intelligence"]["research_continuity"])


if __name__ == "__main__":
    unittest.main()
