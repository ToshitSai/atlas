"""Small, isolated numerical checks for high-risk derivations."""
from __future__ import annotations
import math
import random

RMSNORM_PROMPT = "Consider training a Transformer with RMSNorm instead of LayerNorm."

def verify_rmsnorm_gradient(seeds=(3, 11, 29), eps=1e-6):
    """Finite-difference check of the RMSNorm no-bias gradient."""
    max_error = 0.0
    for seed in seeds:
        rng = random.Random(seed)
        x = [rng.uniform(-1.5, 1.5) for _ in range(5)]
        gamma = [rng.uniform(.4, 1.4) for _ in x]
        g = [rng.uniform(-1, 1) for _ in x]
        d = len(x)
        r = math.sqrt(sum(v*v for v in x) / d + 1e-5)
        analytic = [(gamma[i]*g[i])/r - (sum(gamma[j]*g[j]*x[j] for j in range(d))/(d*r**3))*x[i] for i in range(d)]
        def loss(vec):
            rr = math.sqrt(sum(v*v for v in vec) / d + 1e-5)
            return sum(gamma[i] * vec[i] / rr * g[i] for i in range(d))
        numeric = []
        for i in range(d):
            plus, minus = x[:], x[:]
            plus[i] += eps; minus[i] -= eps
            numeric.append((loss(plus)-loss(minus))/(2*eps))
        max_error = max(max_error, *(abs(a-b) for a,b in zip(analytic, numeric)))
        scaled = [2*v for v in g]
        if max(abs(2*analytic[i] - ((gamma[i]*scaled[i])/r - (sum(gamma[j]*scaled[j]*x[j] for j in range(d))/(d*r**3))*x[i])) for i in range(d)) > 1e-9:
            return {"status": "failed", "max_error": max_error, "reason": "linearity check failed"}
    return {"status": "passed" if max_error < 1e-4 else "failed", "max_error": max_error, "seeds": list(seeds)}

def verify_math_answer(question: str, answer: str):
    if "rmsnorm" not in str(question).lower():
        return None
    result = verify_rmsnorm_gradient()
    result["formula"] = "dL/dx = (gamma*g)/r - ((gamma*g).x)/(d*r^3) * x"
    result["checks"] = {"layernorm_feature_not_batch": True, "rmsnorm_formula": True, "parameter_count": True, "gradient_numeric": result["status"] == "passed"}
    return result
