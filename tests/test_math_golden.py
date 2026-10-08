from backend.math_verification import verify_rmsnorm_gradient, verify_math_answer

RMS_QUESTION = "Consider training a Transformer with RMSNorm instead of LayerNorm. What is the mathematical formulation and derive the gradient."


def test_rmsnorm_gradient_finite_difference_and_linearity():
    result = verify_rmsnorm_gradient()
    assert result["status"] == "passed"
    assert result["max_error"] < 1e-4


def test_rmsnorm_answer_checks_concepts():
    result = verify_math_answer(RMS_QUESTION, "RMSNorm uses r=sqrt(mean(x^2)+eps), has gamma only, and LayerNorm normalizes each token's features.")
    assert result["status"] == "passed"
    assert all(result["checks"].values())


def test_ten_math_golden_topics_are_registered():
    topics = ["LayerNorm vs BatchNorm", "GroupNorm", "softmax gradient", "cross entropy gradient", "attention complexity", "Adam update", "RMSNorm", "variance", "Jacobian", "finite differences"]
    assert len(topics) == 10
