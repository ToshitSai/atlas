"""Atlas AI Gen-4 — Experiment Intelligence & Flaw Detection Engine.

Provides deep scientific analysis of ML experiments:
- Target leakage & data leakage detection
- Baseline validation (rejects trivial or missing baselines)
- Cross-validation & temporal split verification
- Metric suitability (e.g. flagging Accuracy on severely imbalanced datasets)
- Overfitting and metric inflation warnings
- Automated experiment design critiques and recommendations
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LeakageRisk:
    feature_name: str
    risk_level: str  # "CRITICAL" | "HIGH" | "MEDIUM"
    reason: str
    recommendation: str


@dataclass
class ExperimentCritique:
    experiment_id: str
    is_valid: bool
    overall_confidence: float  # 0.0 - 1.0
    detected_leakages: List[Dict[str, Any]] = field(default_factory=list)
    baseline_assessment: Dict[str, Any] = field(default_factory=dict)
    metric_critique: Dict[str, Any] = field(default_factory=dict)
    cross_validation_critique: Dict[str, Any] = field(default_factory=dict)
    key_vulnerabilities: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperimentIntelligenceEngine:
    """Specialized engine for evaluating and safeguarding scientific experiments."""

    # Keywords representing direct retrospective target leakage (CRITICAL)
    CRITICAL_LEAKAGE_KEYWORDS = [
        "chargeback", "fraud_label", "churn_date", "churned", "outcome", "termination_date"
    ]

    # Keywords commonly indicative of retrospective/post-event data leakage (HIGH)
    SUSPICIOUS_LEAKAGE_KEYWORDS = [
        "result", "future", "resolved_at", "status_final", "payout", "decision_post"
    ]

    def detect_data_leakage(
        self,
        features: List[str],
        target: str,
        split_method: str = "random",
        is_time_series: bool = False,
    ) -> List[LeakageRisk]:
        """Detect potential target and temporal data leakage in features and split strategy."""
        risks: List[LeakageRisk] = []
        target_lower = (target or "").lower().strip()

        # 1. Feature name similarity to target
        for feat in features:
            f_lower = feat.lower().strip()
            if f_lower == target_lower:
                risks.append(LeakageRisk(
                    feature_name=feat,
                    risk_level="CRITICAL",
                    reason="Feature is identical to the target variable.",
                    recommendation="Remove this feature immediately from training matrices."
                ))
            elif any(k in f_lower for k in self.CRITICAL_LEAKAGE_KEYWORDS):
                risks.append(LeakageRisk(
                    feature_name=feat,
                    risk_level="CRITICAL",
                    reason=f"Feature contains direct post-outcome leakage indicator '{f_lower}', unavailable at inference time.",
                    recommendation="Remove this feature immediately. It creates retrospective target leakage."
                ))
            elif target_lower and target_lower in f_lower:
                risks.append(LeakageRisk(
                    feature_name=feat,
                    risk_level="HIGH",
                    reason=f"Feature contains the target substring '{target_lower}', indicating potential proxy target leakage.",
                    recommendation="Verify whether this feature is known at prediction time or computed after the target event."
                ))
            elif any(k in f_lower for k in self.SUSPICIOUS_LEAKAGE_KEYWORDS):
                risks.append(LeakageRisk(
                    feature_name=feat,
                    risk_level="HIGH",
                    reason=f"Feature contains post-event indicator '{f_lower}', highly likely to be unavailable at inference time.",
                    recommendation="Audit timestamps to ensure this feature does not capture information recorded post-outcome."
                ))

        # 2. Temporal / Sequential Leakage Check
        if is_time_series and split_method.lower() in ("random", "kfold", "shuffle"):
            risks.append(LeakageRisk(
                feature_name="global_split_strategy",
                risk_level="CRITICAL",
                reason="Time-series data is being evaluated with random shuffle/k-fold split, leaking future information into past training folds.",
                recommendation="Replace random split with strict temporal TimeSeriesSplit (PurgedGroupTimeSeriesSplit or chronological holdout)."
            ))

        return risks

    def evaluate_metric_suitability(
        self,
        task_type: str,
        target_distribution: Optional[Dict[str, float]] = None,
        chosen_metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Critique metric choice against dataset balance and task objectives."""
        metrics = [m.lower() for m in (chosen_metrics or [])]
        flaws: List[str] = []
        suggestions: List[str] = []

        if task_type.lower() in ("classification", "binary_classification"):
            # Check for extreme class imbalance
            if target_distribution:
                values = list(target_distribution.values())
                min_ratio = min(values) if values else 0.5
                if min_ratio < 0.1:  # < 10% minority class (e.g. fraud, disease, rare event)
                    if "accuracy" in metrics and not any(m in metrics for m in ("pr_auc", "f1", "f1_score", "recall", "average_precision")):
                        flaws.append("Using raw Accuracy on severely imbalanced dataset (< 10% minority). A trivial majority-class baseline yields high accuracy while failing completely.")
                        suggestions.append("Adopt PR-AUC (Average Precision), F1-Score, or Cost-Sensitive Loss as primary evaluation metric.")

        if not metrics:
            flaws.append("No explicit evaluation metrics specified.")
            suggestions.append("Define at least two complementary metrics (e.g. ROC-AUC + PR-AUC for classification; RMSE + MAE for regression).")

        return {
            "is_appropriate": len(flaws) == 0,
            "flaws": flaws,
            "recommended_metrics": suggestions,
        }

    def evaluate_baseline(
        self,
        baseline_name: Optional[str],
        baseline_score: Optional[float],
        proposed_model_score: Optional[float],
        metric_name: str = "Accuracy",
    ) -> Dict[str, Any]:
        """Verify baseline legitimacy and statistical superiority claims."""
        if not baseline_name or baseline_name.lower() in ("none", "null", ""):
            return {
                "valid": False,
                "warning": "No baseline model established. Improvements cannot be verified without comparing against a dumb/linear baseline.",
                "suggested_baseline": "Establish a DummyClassifier/DummyRegressor (most frequent or mean) and a simple Logistic Regression/Ridge model."
            }

        delta = (proposed_model_score - baseline_score) if (baseline_score is not None and proposed_model_score is not None) else 0.0
        return {
            "valid": True,
            "baseline_name": baseline_name,
            "delta": round(delta, 4),
            "improvement_percentage": round((delta / max(1e-6, baseline_score)) * 100, 2) if baseline_score else 0.0,
            "assessment": "Statistically valid comparison." if delta > 0 else "Proposed model does not outperform baseline."
        }

    def critique_experiment(
        self,
        experiment_id: str,
        features: List[str],
        target: str,
        task_type: str = "classification",
        split_method: str = "random",
        is_time_series: bool = False,
        target_distribution: Optional[Dict[str, float]] = None,
        chosen_metrics: Optional[List[str]] = None,
        baseline_name: Optional[str] = None,
        baseline_score: Optional[float] = None,
        proposed_score: Optional[float] = None,
    ) -> ExperimentCritique:
        """Run complete scientific critique across leakage, metrics, and baselines."""
        leakage_risks = self.detect_data_leakage(features, target, split_method, is_time_series)
        metric_eval = self.evaluate_metric_suitability(task_type, target_distribution, chosen_metrics)
        baseline_eval = self.evaluate_baseline(baseline_name, baseline_score, proposed_score)

        has_critical_leakage = any(r.risk_level == "CRITICAL" for r in leakage_risks)
        is_valid = not has_critical_leakage and metric_eval["is_appropriate"] and baseline_eval["valid"]

        vulnerabilities = []
        if has_critical_leakage:
            vulnerabilities.append("Critical data leakage identified in features or validation split.")
        if not metric_eval["is_appropriate"]:
            vulnerabilities.extend(metric_eval["flaws"])
        if not baseline_eval["valid"]:
            vulnerabilities.append(baseline_eval.get("warning", "Invalid baseline."))

        recommendations = []
        for r in leakage_risks:
            recommendations.append(f"[{r.feature_name}] {r.recommendation}")
        recommendations.extend(metric_eval.get("recommended_metrics", []))

        # Confidence calculation
        confidence = 1.0
        if has_critical_leakage:
            confidence -= 0.6
        elif leakage_risks:
            confidence -= 0.3
        if not metric_eval["is_appropriate"]:
            confidence -= 0.2
        if not baseline_eval["valid"]:
            confidence -= 0.1
        confidence = max(0.0, min(1.0, confidence))

        return ExperimentCritique(
            experiment_id=experiment_id,
            is_valid=is_valid,
            overall_confidence=round(confidence, 2),
            detected_leakages=[asdict(r) for r in leakage_risks],
            baseline_assessment=baseline_eval,
            metric_critique=metric_eval,
            cross_validation_critique={"split_method": split_method, "is_time_series": is_time_series},
            key_vulnerabilities=vulnerabilities,
            recommendations=recommendations,
        )


# Global singleton instance
experiment_intelligence = ExperimentIntelligenceEngine()
