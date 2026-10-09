"""Lightweight semantic decomposition for mixed chat requests."""
from __future__ import annotations
import re

def decompose(message: str) -> dict:
    text = str(message or '').strip()
    parts = [p.strip() for p in re.split(r'(?m)(?=^\s*(?:part\s*)?\d+\s*[\).:-]\s+)', text, flags=re.I) if p.strip()]
    if len(parts) < 2:
        parts = [p.strip() for p in re.split(r'(?:\n\s*|\s+)\d+[\).:-]\s+(?=[A-Za-z])', text) if p.strip()]
    tasks = []
    for idx, part in enumerate(parts or [text], 1):
        low = part.lower()
        math = bool(re.search(r'\b(calculate|compute|derive|probability|posterior|prior|equation|gradient|\d+\s*[+*\-/]\s*\d+)\b', low))
        web = bool(re.search(r'\b(search|latest|current|live|web|announcements?|news|sources?|citations?)\b', low))
        kind = 'mathematical_reasoning' if math and not web else 'live_web_research' if web else 'general_answer'
        tasks.append({'id': f'part_{idx}', 'type': kind, 'requires_web_search': web, 'text': part})
    return {'tasks': tasks, 'mixed': len(tasks) > 1}

def bayes_prior_shift(text: str):
    nums = [float(x) for x in re.findall(r'(?<![\w.])0?\.\d+(?:\d+)?', text)]
    if len(nums) < 3: return None
    prior, new_prior, posterior = nums[:3]
    old_odds = posterior / (1 - posterior); likelihood = old_odds / (prior / (1 - prior))
    new_odds = likelihood * (new_prior / (1 - new_prior)); result = new_odds / (1 + new_odds)
    return {'prior': prior, 'new_prior': new_prior, 'posterior': posterior, 'value': result,
            'text': f"Bayesian prior-shift calculation: old odds = {posterior:.8g}/{1-posterior:.8g}; likelihood ratio = {likelihood:.8g}; new odds = {new_odds:.8g}; recalibrated posterior = {result:.10f} ({result*100:.4f}%)."}
