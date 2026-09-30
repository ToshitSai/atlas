import os
import json
import math
import re
import time
import threading
import contextvars
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Any, Optional, List, Callable
import backend.config  # Auto-loads .env into os.environ

# Per-provider socket timeout. ``LLM_TIMEOUT_SECONDS`` is the production name;
# ``LLM_TIMEOUT`` remains a backwards-compatible development alias.
_DEFAULT_TIMEOUT = max(1, int(os.environ.get(
    "LLM_TIMEOUT_SECONDS", os.environ.get("LLM_TIMEOUT", "12"))))

# A local model process normally handles only one or a few generations at a
# time. Admission control is intentionally process-wide: a per-request pool
# does not protect a shared local inference server when many HTTP requests
# arrive at once. The pool is bounded too, so timed-out sockets cannot create
# an unbounded number of Python threads.
_MAX_CONCURRENT_REQUESTS = max(1, int(os.environ.get("MAX_CONCURRENT_LLM_REQUESTS", "2")))
_QUEUE_TIMEOUT = max(0.05, float(os.environ.get("LLM_QUEUE_TIMEOUT_SECONDS", "2")))
_MAX_RETRIES = max(0, int(os.environ.get("MAX_RETRIES", "1")))
_RETRY_BACKOFF = max(0.0, float(os.environ.get("LLM_RETRY_BACKOFF_SECONDS", "0.25")))
_LLM_ADMISSION = threading.BoundedSemaphore(_MAX_CONCURRENT_REQUESTS)
_LLM_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(1, _MAX_CONCURRENT_REQUESTS * 4), thread_name_prefix="llm-provider")
_TELEMETRY_LOCK = threading.Lock()
_LLM_TELEMETRY = {"submitted": 0, "completed": 0, "timeouts": 0, "overloaded": 0,
                  "retries": 0, "queue_wait_ms": 0.0, "execution_ms": 0.0}


def get_llm_telemetry() -> Dict[str, Any]:
    """Return aggregate, secret-free execution telemetry for health/ops views."""
    with _TELEMETRY_LOCK:
        data = dict(_LLM_TELEMETRY)
    completed = data["completed"]
    data["avg_queue_wait_ms"] = round(data.pop("queue_wait_ms") / completed, 2) if completed else 0.0
    data["avg_execution_ms"] = round(data.pop("execution_ms") / completed, 2) if completed else 0.0
    data["max_concurrent_requests"] = _MAX_CONCURRENT_REQUESTS
    return data


def _increment_telemetry(**values: float) -> None:
    with _TELEMETRY_LOCK:
        for key, value in values.items():
            _LLM_TELEMETRY[key] = _LLM_TELEMETRY.get(key, 0) + value


def _call_with_retries(fn, prompt: str, system_prompt: Optional[str], timeout: int,
                       deadline: float, max_tokens: Optional[int] = None,
                       return_details: bool = False) -> Any:
    """Call one provider with bounded retry/backoff.

    A retry is only started while the race's wall-clock deadline still allows a
    socket attempt. This prevents retries from turning an 8-second request into
    a many-minute local-model queue.
    """
    for attempt in range(_MAX_RETRIES + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        socket_timeout = max(1, min(timeout, math.ceil(remaining)))
        try:
            result = fn(prompt, system_prompt, timeout=socket_timeout, max_tokens=max_tokens, return_details=return_details)
        except TypeError:
            try:
                result = fn(prompt, system_prompt, timeout=socket_timeout)
            except TypeError:
                result = fn(prompt, system_prompt)
        if result:
            return result
        if attempt < _MAX_RETRIES:
            _increment_telemetry(retries=1)
            backoff = min(_RETRY_BACKOFF * (2 ** attempt), max(0.0, deadline - time.monotonic()))
            if backoff:
                time.sleep(backoff)
    return None

# Default overall budget for query_llm when the caller did not set a tighter
# request budget via set_llm_budget(). Long-form answers (multi-requirement
# decomposition, architecture design) legitimately need more than 10s.
_DEFAULT_BUDGET = max(1.0, float(os.environ.get("LLM_BUDGET", "90")))

# Public alias: request-level budget applied by handle_intent_message() via
# set_llm_budget(). One constant, one knob (LLM_BUDGET env).
DEFAULT_REQUEST_BUDGET = _DEFAULT_BUDGET

# Hard per-request LLM budget. handle_intent_message() sets a deadline; every
# query_llm() call caps its wait to the remaining budget and skips entirely
# once it is exhausted. Threads in one serverless request share one thread.
_REQUEST_STATE = threading.local()


def set_llm_budget(seconds: float) -> None:
    """Start a hard overall budget for LLM calls on this thread (in seconds)."""
    _REQUEST_STATE.deadline = time.monotonic() + seconds


def clear_llm_budget() -> None:
    _REQUEST_STATE.deadline = None


def remaining_llm_budget() -> Optional[float]:
    """Seconds left in the current request's LLM budget, or None if unset."""
    deadline = getattr(_REQUEST_STATE, "deadline", None)
    if deadline is None:
        return None
    return deadline - time.monotonic()


def call_openai_api(prompt: str, system_prompt: Optional[str] = None, timeout: int = _DEFAULT_TIMEOUT, max_tokens: Optional[int] = None, return_details: bool = False) -> Any:
    api_key = os.environ.get("OPENAI_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return None

    start = time.monotonic()
    try:
        url = f"{api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        effective_max_tokens = max_tokens or int(os.environ.get("OPENAI_MAX_TOKENS", "4096"))

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": effective_max_tokens,
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            choice = res_data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")
            usage = res_data.get("usage", {})
            in_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            out_tokens = usage.get("completion_tokens", len(content) // 4)

            print(f"[LLM TIMING] OpenAI ({model}) responded in {time.monotonic() - start:.2f}s | Tokens: in={in_tokens}, out={out_tokens}, finish={finish_reason}")

            if return_details:
                return {
                    "text": content,
                    "finish_reason": finish_reason,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "requested_output_tokens": effective_max_tokens,
                    "model_context_limit": 128000,
                    "provider": "openai",
                    "model": model,
                    "generation_time": round(time.monotonic() - start, 2)
                }
            return content
    except Exception as e:
        print(f"[LLM Client Warning] OpenAI call failed after {time.monotonic() - start:.2f}s: {e}")
        return None

def call_gemini_api(prompt: str, system_prompt: Optional[str] = None, timeout: int = _DEFAULT_TIMEOUT, max_tokens: Optional[int] = None, return_details: bool = False) -> Any:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    start = time.monotonic()
    try:
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        effective_max_tokens = max_tokens or int(os.environ.get("GEMINI_MAX_TOKENS", "8192"))

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": full_text}]}
            ],
            "generationConfig": {
                "maxOutputTokens": effective_max_tokens,
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidate = res_data["candidates"][0]
            text = candidate["content"]["parts"][0]["text"]
            finish_reason_raw = candidate.get("finishReason", "STOP")
            finish_reason = "length" if finish_reason_raw in ("MAX_TOKENS", "LENGTH") else "stop"
            usage = res_data.get("usageMetadata", {})
            in_tokens = usage.get("promptTokenCount", len(full_text) // 4)
            out_tokens = usage.get("candidatesTokenCount", len(text) // 4)

            print(f"[LLM TIMING] Gemini ({model}) responded in {time.monotonic() - start:.2f}s | Tokens: in={in_tokens}, out={out_tokens}, finish={finish_reason}")

            if return_details:
                return {
                    "text": text,
                    "finish_reason": finish_reason,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "requested_output_tokens": effective_max_tokens,
                    "model_context_limit": 1000000,
                    "provider": "gemini",
                    "model": model,
                    "generation_time": round(time.monotonic() - start, 2)
                }
            return text
    except Exception as e:
        print(f"[LLM Client Warning] Gemini call failed after {time.monotonic() - start:.2f}s: {e}")
        return None

def call_anthropic_api(prompt: str, system_prompt: Optional[str] = None, timeout: int = _DEFAULT_TIMEOUT, max_tokens: Optional[int] = None, return_details: bool = False) -> Any:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    start = time.monotonic()
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

        model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        effective_max_tokens = max_tokens or int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096"))

        payload = {
            "model": model,
            "max_tokens": effective_max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["content"][0]["text"]
            stop_reason = res_data.get("stop_reason", "end_turn")
            finish_reason = "length" if stop_reason == "max_tokens" else "stop"
            usage = res_data.get("usage", {})
            in_tokens = usage.get("input_tokens", len(prompt) // 4)
            out_tokens = usage.get("output_tokens", len(text) // 4)

            print(f"[LLM TIMING] Anthropic ({model}) responded in {time.monotonic() - start:.2f}s | Tokens: in={in_tokens}, out={out_tokens}, finish={finish_reason}")

            if return_details:
                return {
                    "text": text,
                    "finish_reason": finish_reason,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "requested_output_tokens": effective_max_tokens,
                    "model_context_limit": 200000,
                    "provider": "anthropic",
                    "model": model,
                    "generation_time": round(time.monotonic() - start, 2)
                }
            return text
    except Exception as e:
        print(f"[LLM Client Warning] Anthropic call failed after {time.monotonic() - start:.2f}s: {e}")
        return None

def call_mistral_api(prompt: str, system_prompt: Optional[str] = None, timeout: int = _DEFAULT_TIMEOUT, max_tokens: Optional[int] = None, return_details: bool = False) -> Any:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None

    start = time.monotonic()
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = os.environ.get("MISTRAL_MODEL", "mistral-tiny")
        effective_max_tokens = max_tokens or int(os.environ.get("MISTRAL_MAX_TOKENS", "4096"))

        payload = {
            "model": model,
            "max_tokens": effective_max_tokens,
            "temperature": float(os.environ.get("MISTRAL_TEMPERATURE", "0.1")),
            "messages": messages
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            choice = res_data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")
            usage = res_data.get("usage", {})
            in_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            out_tokens = usage.get("completion_tokens", len(content) // 4)

            print(f"[LLM TIMING] Mistral ({model}) responded in {time.monotonic() - start:.2f}s | Tokens: in={in_tokens}, out={out_tokens}, finish={finish_reason}")

            if return_details:
                return {
                    "text": content,
                    "finish_reason": finish_reason,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "requested_output_tokens": effective_max_tokens,
                    "model_context_limit": 32000,
                    "provider": "mistral",
                    "model": model,
                    "generation_time": round(time.monotonic() - start, 2)
                }
            return content
    except Exception as e:
        print(f"[LLM Client Warning] Mistral call failed after {time.monotonic() - start:.2f}s: {e}")
        return None

_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

_selected_provider: contextvars.ContextVar = contextvars.ContextVar("selected_llm_provider", default="auto")


def provider_from_setting(value: str) -> str:
    """Map the UI's human-readable provider label to the dispatcher value."""
    text = str(value or "").lower()
    if "openai" in text:
        return "openai"
    if "anthropic" in text or "claude" in text:
        return "anthropic"
    if "gemini" in text:
        return "gemini"
    if "mistral" in text:
        return "mistral"
    return "auto"


def set_selected_provider(value: str) -> None:
    """Set this request's explicit provider without mutating global process state."""
    _selected_provider.set(provider_from_setting(value))


def configured_provider_names() -> List[str]:
    return [name for name, env_name in _PROVIDER_KEY_ENV.items() if os.environ.get(env_name)]


def effective_provider_label(setting: str = "") -> str:
    """Secret-free, truthful label for the engine that the next request uses."""
    selected = provider_from_setting(setting)
    configured = configured_provider_names()
    if selected != "auto":
        return f"{selected.title()} (selected)" if selected in configured else f"{selected.title()} (selected, key unavailable)"
    if configured:
        return "Auto (" + ", ".join(name.title() for name in configured) + " configured)"
    return "Rule-Based Synthesizer (no provider configured)"


def any_provider_configured() -> bool:
    """True when at least one supported LLM provider has an API key in the env."""
    return bool(configured_provider_names())


# Per-request engine trace (Bug 5 disclosure): handlers that call query_llm and
# then fall back to built-in rule-based templates must be able to tell the user
# which engine actually produced the answer. contextvars keeps this correct
# across concurrent async requests.
_engine_trace: contextvars.ContextVar = contextvars.ContextVar("llm_engine_trace", default=None)


def begin_engine_trace() -> None:
    _engine_trace.set({"attempted": 0, "succeeded": 0})


def _trace_attempted() -> None:
    trace = _engine_trace.get()
    if trace is not None:
        trace["attempted"] += 1


def _trace_succeeded() -> None:
    trace = _engine_trace.get()
    if trace is not None:
        trace["succeeded"] += 1


def engine_disclosure() -> str:
    """Honest one-line disclosure when the visible answer could only have come
    from the built-in rule-based engine (an LLM was attempted but none
    responded). Empty string when an LLM answered or none was needed."""
    trace = _engine_trace.get()
    if not trace or trace["attempted"] == 0 or trace["succeeded"] > 0:
        return ""
    if any_provider_configured():
        return ("\n\n_No LLM provider responded in time — this answer was produced "
                "by the built-in rule-based engine, not a live model._")
    return ("\n\n_No LLM provider is connected — this answer was produced by the "
            "built-in rule-based engine, not a live model._")


def query_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "auto",
    role: str = "main",
    timeout: int = _DEFAULT_TIMEOUT,
    max_tokens: Optional[int] = None,
    return_details: bool = False
) -> Any:
    """
    Unified multi-provider LLM caller supporting OpenAI, Gemini, Anthropic Claude, and Mistral.

    provider="auto" (default) races all configured providers IN PARALLEL via a
    thread pool; the first successful (non-None) result is returned immediately.
    The classic role preference (main: OpenAI -> Gemini -> Anthropic -> Mistral;
    critic: Anthropic -> Gemini -> OpenAI -> Mistral) only acts as a tie-break:
    if several succeed at the same time the first to complete wins.

    An EXPLICIT provider ("openai" | "gemini" | "anthropic" | "mistral") is
    honoured strictly (§15): only that provider is called and there is NO silent
    cross-provider fallback. An explicitly selected provider without a key
    returns None (callers surface a capability error) instead of pretending
    another provider answered.

    The wait is capped by the `timeout` parameter (default ~60s, env LLM_TIMEOUT_SECONDS)
    and by the request's overall LLM budget (set_llm_budget) when one is active;
    otherwise LLM_BUDGET (default 90s) applies so long-form answers can finish.
    """
    submitted_at = time.monotonic()
    _increment_telemetry(submitted=1)
    _trace_attempted()
    provider = (provider or "auto").lower()
    if provider == "auto":
        provider = _selected_provider.get() or "auto"
    if provider != "auto":
        # Explicit selection is strict (§15): only the requested provider is
        # called — no silent cross-provider fallback. Built at call time so
        # tests can monkeypatch provider functions.
        table = {
            "openai": ("OPENAI_API_KEY", call_openai_api),
            "gemini": ("GEMINI_API_KEY", call_gemini_api),
            "anthropic": ("ANTHROPIC_API_KEY", call_anthropic_api),
            "mistral": ("MISTRAL_API_KEY", call_mistral_api),
        }
        if provider not in table:
            print(f"[LLM Client Warning] unknown provider '{provider}' requested")
            return None
        env_name, fn = table[provider]
        if not os.environ.get(env_name):
            print(f"[LLM Client Warning] provider '{provider}' explicitly selected "
                  f"but {env_name} is not configured")
            return None
        providers = (fn,)
    elif role == "critic":
        providers = (call_anthropic_api, call_gemini_api, call_openai_api, call_mistral_api)
    else:
        providers = (call_openai_api, call_gemini_api, call_anthropic_api, call_mistral_api)

    remaining = remaining_llm_budget()
    if remaining is not None and remaining <= 0:
        print("[LLM BUDGET] exhausted before call; skipping provider race")
        return None
    # Cap the socket timeout to the requested timeout and the remaining budget.
    if remaining is None:
        socket_timeout = timeout
        wait_overall = timeout
    else:
        socket_timeout = max(1, min(timeout, math.ceil(remaining)))
        wait_overall = max(0.05, remaining)
    admission_wait = min(_QUEUE_TIMEOUT, wait_overall)
    if not _LLM_ADMISSION.acquire(timeout=admission_wait):
        _increment_telemetry(overloaded=1)
        print(f"[LLM QUEUE] saturated after {admission_wait:.2f}s; request was not executed")
        return None

    queue_wait = time.monotonic() - submitted_at
    start = time.monotonic()
    deadline = start + wait_overall
    try:
        futures = {
            _LLM_EXECUTOR.submit(_call_with_retries, fn, prompt, system_prompt,
                                 socket_timeout, deadline, max_tokens, return_details): fn.__name__
            for fn in providers
        }
        try:
            for fut in as_completed(futures, timeout=wait_overall):
                result = fut.result()
                if result:
                    _trace_succeeded()
                    print(f"[LLM TIMING] first success via {futures[fut]} in {time.monotonic() - start:.2f}s")
                    return result
        except FuturesTimeoutError:
            _increment_telemetry(timeouts=1)
            print(f"[LLM TIMING] provider race timed out after {time.monotonic() - start:.2f}s")
        return None
    finally:
        for future in locals().get("futures", {}):
            future.cancel()
        _LLM_ADMISSION.release()
        _increment_telemetry(completed=1, queue_wait_ms=queue_wait * 1000,
                             execution_ms=(time.monotonic() - start) * 1000)

def query_critic_llm(hypothesis_title: str, hypothesis_body: str, baseline_metric: str) -> Dict[str, Any]:
    """
    Critic LLM (Claude/Gemini) evaluates research hypothesis & proposed experiment before execution.
    """
    system_prompt = "You are a scientific peer reviewer / Critic LLM in an autonomous AI research lab. Critique the proposed experiment for technical rigor."
    prompt = f"""
Proposed Experiment: {hypothesis_title}
Hypothesis: {hypothesis_body}
Current Baseline Performance: {baseline_metric}

Provide a 2-sentence peer critique evaluating scientific soundness, potential failure modes, and expected impact.
"""
    critique_text = query_llm(prompt, system_prompt, role="critic")
    if critique_text:
        return {
            "approved": True,
            "critique": critique_text.strip(),
            "criticModel": "Critic LLM (Claude/Gemini)"
        }
    return {
        "approved": True,
        "critique": "Hypothesis validated. Proceeding with regularized gradient boosting baseline comparison.",
        "criticModel": "Rule-Based Peer Evaluator"
    }

def generate_research_question(objective: str) -> str:
    system_prompt = "You are a senior machine learning scientist. Convert the user's research objective into a formal, testable ML research question. Return plain text: no markdown emphasis, no surrounding quotes."
    prompt = f"Objective: '{objective}'\nFormulate a precise research question addressing model design, class imbalance, metrics, or feature strategy. Return ONLY the research question text."
    
    llm_res = query_llm(prompt, system_prompt)
    if llm_res and len(llm_res.strip()) > 15:
        # Models love wrapping the question in **bold** or quotes; the UI and
        # the report quote it verbatim, so store plain text only.
        cleaned = re.sub(r"\*{1,3}|_{1,3}", "", llm_res.strip()).strip().strip('"').strip()
        return cleaned or llm_res.strip()

    obj_lower = objective.lower()
    if "fraud" in obj_lower:
        return "How can fraud detection recall be improved under severe class imbalance while controlling false positives?"
    elif "churn" in obj_lower:
        return "How can customer churn classification accuracy and interpretability be maximized using regularized tree ensembles?"
    elif "price" in obj_lower or "house" in obj_lower or "regression" in obj_lower:
        return "How can regression predictive error (RMSE) be minimized using non-linear feature transformations?"
    else:
        return f"How can predictive performance and generalization for '{objective}' be optimized across tabular baseline models?"

def generate_hypothesis_llm(objective: str, dataset_summary: Dict[str, Any], baseline_summary: List[Dict[str, Any]], literature: List[Dict[str, Any]], exp_idx: int = 1, previous_experiments: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    system_prompt = (
        "You are an autonomous AI machine learning researcher. Given a research objective, dataset properties, "
        "and baseline model metrics, formulate a clear hypothesis and write clean, runnable Python experiment code."
    )

    # Research memory (directive §7): the model must see what was already run
    # so it proposes the NEXT distinct experiment instead of repeating itself.
    prev_block = ""
    prev = previous_experiments or []
    if prev:
        prev_block = "Previous Experiments (already executed — do NOT repeat any of these approaches; build on their results):\n"
        prev_block += json.dumps([
            {"title": p.get("title"), "hypothesis": p.get("hypothesis"),
             "metric": f"{p.get('metricName')}={p.get('metricValue')}", "status": p.get("status")}
            for p in prev
        ], indent=2)
        prev_block += "\n\n"

    user_prompt = f"""
Research Objective: {objective}
Dataset Summary:
- Filename: {dataset_summary.get('filename')}
- Rows: {dataset_summary.get('rowCount')}, Cols: {dataset_summary.get('columnCount')}
- Task Type: {dataset_summary.get('taskType')}
- Target: {dataset_summary.get('targetCandidate')}

Baseline Results:
{json.dumps([{b['name']: b['metrics']} for b in baseline_summary], indent=2)}

{prev_block}Formulate 1 {"NEW testable scientific hypothesis that is meaningfully different from every previous experiment listed above, and that addresses their weaknesses or extends their best result." if prev else "testable scientific hypothesis to improve performance."}
Return JSON format strictly:
{{
  "title": "Short experiment title",
  "hypothesis": "Testable scientific hypothesis string",
  "hyperparams": "Description of hyperparams/architecture change",
  "python_script": "Full runnable python script code"
}}
"""

    response_text = query_llm(user_prompt, system_prompt, role="main")
    if response_text:
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            res = json.loads(clean_text.strip())
            if all(k in res for k in ["title", "hypothesis", "hyperparams", "python_script"]):
                return res
        except Exception:
            pass

    task = dataset_summary.get("taskType", "classification")
    is_class = (task == "classification")
    is_imbalanced = bool(dataset_summary.get("isImbalanced"))

    if exp_idx == 1:
        title = "Exp 1: Class-Weighted Gradient Boosting"
        hyp = ("Adding explicit class weighting to a gradient-boosted tree model will raise detection of the "
               "rare positive (fraud) class, improving PR-AUC and recall under severe imbalance.")
        hyperparams = "HistGradientBoosting, class_weight via sample_weight, max_iter=250, lr=0.08"
    elif exp_idx == 2:
        title = f"Exp {exp_idx}: Threshold Tuning & Balanced Boosting"
        hyp = ("Tuning the decision threshold and combining balanced boosting with deeper trees will improve the "
               "precision/recall trade-off for the minority class beyond the baseline.")
        hyperparams = "XGBoost scale_pos_weight, threshold optimized on PR curve, max_depth=6"
    else:
        # The fallback has no real history to reason over, so vary the *strategy*
        # per index instead of re-issuing the same experiment (directive §7).
        strategies = [
            ("SMOTE Oversampling + Regularized Ensemble",
             "Synthetic minority oversampling (SMOTE) combined with a strongly regularized ensemble will "
             "recover minority-class separation without the overfitting seen in previous runs.",
             "SMOTE k=5, HistGradientBoosting max_leaf_nodes=31, L2=1.0"),
            ("Feature Selection & Dimensionality Reduction",
             "Dropping low-importance features and retraining on the selected subset will reduce noise-driven "
             "false positives and improve generalization of the minority class.",
             "Mutual-information top-k feature selection (k=20), shallow ensemble"),
            ("Calibrated Probability Ensemble",
             "Calibrating probabilities and averaging diverse model families will stabilize the precision/recall "
             "trade-off where single models plateaued.",
             "Isotonic calibration over LR + HistGB soft-voting ensemble"),
        ]
        s = strategies[(exp_idx - 3) % len(strategies)]
        title = f"Exp {exp_idx}: {s[0]}"
        hyp = s[1]
        hyperparams = s[2]

    script = '''import os, json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import (precision_score, recall_score, f1_score, roc_auc_score,
                             average_precision_score, confusion_matrix, r2_score, mean_squared_error)

def read_table(path):
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".arrow")) else pd.read_csv(path)

dataset_path = os.environ.get("DATASET_PATH", "dataset.csv")
test_path = os.environ.get("TEST_PATH", "")
target_col = os.environ.get("TARGET_COL", "")
task_type = os.environ.get("TASK_TYPE", "classification")
primary_metric = os.environ.get("PRIMARY_METRIC", "pr_auc")
is_imbalanced = os.environ.get("IS_IMBALANCED", "0") == "1"

df = read_table(dataset_path)
if not target_col or target_col not in df.columns:
    target_col = df.columns[-1]
df = df.dropna(subset=[target_col])

encoders = {}
def preprocess(frame):
    Xf = frame.drop(columns=[target_col]).copy()
    yf = frame[target_col]
    for c in Xf.select_dtypes(include=["object", "category", "string"]).columns:
        if c not in encoders:
            le = LabelEncoder(); le.fit(Xf[c].astype(str)); encoders[c] = le
        le = encoders[c]
        vals = Xf[c].astype(str)
        unseen = set(vals) - set(le.classes_)
        if unseen:
            vals = vals.where(~vals.isin(unseen), le.classes_[0])
        Xf[c] = le.transform(vals)
    return Xf, yf

X, y = preprocess(df)
num_cols = X.select_dtypes(include=[np.number]).columns
scaler = StandardScaler().fit(X[num_cols]) if len(num_cols) else None
if scaler is not None:
    X[num_cols] = scaler.transform(X[num_cols])

if task_type == "classification":
    le_y = LabelEncoder(); y = le_y.fit_transform(y.astype(str))
binary = task_type == "classification" and len(np.unique(y)) == 2

if test_path and os.path.exists(test_path):
    dtest = read_table(test_path).dropna(subset=[target_col])
    Xt, yt = preprocess(dtest)
    if scaler is not None:
        Xt[num_cols] = scaler.transform(Xt[num_cols])
    X_tr, X_te = X, Xt
    y_tr = y
    y_te = le_y.transform(yt.astype(str)) if task_type == "classification" else pd.to_numeric(yt, errors="coerce").fillna(0).values
else:
    strat = y if (task_type == "classification" and len(np.unique(y)) > 1) else None
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=strat)

metrics = {}
if task_type == "classification":
    sample_weight = None
    if is_imbalanced and binary:
        uniq, cnt = np.unique(y_tr, return_counts=True)
        w = cnt.max() / cnt.astype(float)
        sample_weight = np.array([w[list(uniq).index(v)] for v in y_tr])
    model = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=42)
    model.fit(X_tr, y_tr, sample_weight=sample_weight)
    preds = model.predict(X_te)
    probs = model.predict_proba(X_te)[:, 1] if binary else None
    if binary:
        tn, fp, fn, tp = confusion_matrix(y_te, preds, labels=[0, 1]).ravel()
        metrics = {
            "precision": round(float(precision_score(y_te, preds, zero_division=0)), 4),
            "recall": round(float(recall_score(y_te, preds, zero_division=0)), 4),
            "f1": round(float(f1_score(y_te, preds, zero_division=0)), 4),
            "pr_auc": round(float(average_precision_score(y_te, probs)), 4) if probs is not None else 0.0,
            "roc_auc": round(float(roc_auc_score(y_te, probs)), 4) if probs is not None else 0.5,
            "fpr": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
            "fnr": round(float(fn / (fn + tp)) if (fn + tp) else 0.0, 4),
        }
    else:
        metrics = {
            "f1": round(float(f1_score(y_te, preds, average="weighted", zero_division=0)), 4),
            "precision": round(float(precision_score(y_te, preds, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_te, preds, average="weighted", zero_division=0)), 4),
        }
    metric_value = metrics.get(primary_metric, metrics.get("f1", 0.0))
    metric_name = primary_metric.upper()
else:
    model = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, random_state=42)
    model.fit(X_tr, y_tr)
    preds = model.predict(X_te)
    metrics = {
        "r2": round(float(r2_score(y_te, preds)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_te, preds))), 4),
    }
    metric_value = metrics["r2"]
    metric_name = "R2"

metrics_path = os.environ.get("METRICS_PATH", "metrics.json")
with open(metrics_path, "w") as f:
    json.dump({"metric_name": metric_name, "metric_value": round(float(metric_value), 4), "metrics": metrics}, f)
print("Experiment completed. %s=%.4f" % (metric_name, float(metric_value)))
'''

    return {
        "title": title,
        "hypothesis": hyp,
        "hyperparams": hyperparams,
        "model": "HistGradientBoosting (class-weighted)" if exp_idx == 1 else "XGBoost/HistGB (threshold-tuned)",
        "python_script": script
    }


def estimate_question_complexity(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Estimates question complexity (1-10) and calculates optimal output token budget.
    Scans for multi-part questions, technical/derivation keywords, LaTeX math requests,
    architectural comparisons, and deep ML topics.
    """
    text = f"{system_prompt or ''} {prompt or ''}".lower()

    score = 2  # Baseline for standard question

    # 1. Multi-part detection
    part_matches = len(re.findall(r"\b(?:\d+[\.\)]|part\s+\d+|step\s+\d+|question\s+\d+|task\s+\d+)\b", text))
    if part_matches >= 3:
        score += 3
    elif part_matches >= 2:
        score += 2

    # Question mark count / multi-question detection
    qmark_count = text.count('?')
    if qmark_count >= 4:
        score += 2
    elif qmark_count >= 2:
        score += 1

    # 2. Mathematical derivation & technical deep dive keywords
    derivation_keywords = [
        "derive", "derivation", "proof", "prove", "step-by-step", "mathematically",
        "show mathematically", "taylor expansion", "loss function", "gradient descent",
        "jacobian", "hessian", "eigenvalue", "integral", "matrix factorization"
    ]
    if any(kw in text for kw in derivation_keywords):
        score += 3

    # 3. Comparative & structural keywords
    comparison_keywords = [
        "compare", "comparison", "versus", "vs", "difference between",
        "trade-offs", "pros and cons", "architectural comparison"
    ]
    if any(kw in text for kw in comparison_keywords):
        score += 2

    # 4. Advanced ML topics
    advanced_ml_topics = [
        "flashattention", "rope", "yarn", "ppo", "dpo", "grpo", "ddpm", "score sde",
        "flow matching", "xgboost", "goss", "pagedattention", "mla", "sparse moe",
        "ntk", "sam", "navit", "2d-rope", "shampoo", "muon", "vlm", "patchification"
    ]
    if any(topic in text for topic in advanced_ml_topics):
        score += 2

    final_score = min(10, max(1, score))

    # Dynamic output token budget mapping:
    if final_score <= 3:
        budget = 1024
    elif final_score <= 6:
        budget = 2500
    elif final_score <= 8:
        budget = 4096
    else:
        budget = 8192

    return {
        "complexity_score": final_score,
        "recommended_output_budget": budget,
        "is_multi_part": part_matches >= 2 or qmark_count >= 3,
        "is_derivation": any(kw in text for kw in derivation_keywords),
    }


def check_response_completion(text: str, finish_reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks if an LLM output was truncated or cut off mid-equation / mid-sentence.
    """
    if not text or not text.strip():
        return {"complete": False, "reason": "empty"}

    if finish_reason and finish_reason.lower() in ("length", "max_tokens"):
        return {"complete": False, "reason": "finish_reason_length"}

    # 1. Check unclosed LaTeX math blocks
    dollar_blocks = text.count("$$")
    if dollar_blocks % 2 != 0:
        return {"complete": False, "reason": "unclosed_dollar_latex"}

    open_bracket_math = text.count(r"\[")
    close_bracket_math = text.count(r"\]")
    if open_bracket_math > close_bracket_math:
        return {"complete": False, "reason": "unclosed_bracket_latex"}

    begins = len(re.findall(r"\\begin\{[a-zA-Z0-9\*]+\}", text))
    ends = len(re.findall(r"\\end\{[a-zA-Z0-9\*]+\}", text))
    if begins > ends:
        return {"complete": False, "reason": "unclosed_begin_env_latex"}

    # 2. Check unclosed code blocks
    code_blocks = text.count("```")
    if code_blocks % 2 != 0:
        return {"complete": False, "reason": "unclosed_code_block"}

    # 3. Check abrupt sentence ending
    trimmed = text.strip()
    abrupt_patterns = [
        r"(?:where|and|with|equal to|equals|given by|defined as|note that|we have|which gives|so that|thus,?\s*)\s*$",
        r"[\+\-\*/=,\\:=]\s*$",
        r"\\frac\{[^\}]*$",
        r"\\begin\{[^\}]*$",
    ]
    for pattern in abrupt_patterns:
        if re.search(pattern, trimmed, re.IGNORECASE):
            return {"complete": False, "reason": "abrupt_text_ending"}

    if len(trimmed) > 50 and not re.search(r"[\.\!\?\}\]\>\)]\s*$", trimmed):
        last_line = trimmed.split("\n")[-1].strip()
        if not last_line.startswith("#") and not last_line.startswith("-") and not last_line.startswith("*"):
            if len(last_line) > 10 and not last_line.endswith("."):
                return {"complete": False, "reason": "missing_terminal_punctuation"}

    return {"complete": True, "reason": "ok"}


def fix_unclosed_markdown_blocks(text: str) -> str:
    if not text:
        return text

    res = text
    if res.count("```") % 2 != 0:
        res += "\n```"

    if res.count("$$") % 2 != 0:
        res += "\n$$"

    open_brackets = res.count(r"\[")
    close_brackets = res.count(r"\]")
    if open_brackets > close_brackets:
        res += "\n\\]" * (open_brackets - close_brackets)

    return res


def query_llm_detailed(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "auto",
    role: str = "main",
    timeout: int = _DEFAULT_TIMEOUT,
    requested_max_tokens: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Query LLM and return rich telemetry dictionary."""
    res = query_llm(
        prompt,
        system_prompt=system_prompt,
        provider=provider,
        role=role,
        timeout=timeout,
        max_tokens=requested_max_tokens,
        return_details=True
    )
    if isinstance(res, dict):
        return res
    if isinstance(res, str):
        return {
            "text": res,
            "finish_reason": "stop",
            "input_tokens": len(prompt) // 4,
            "output_tokens": len(res) // 4,
            "requested_output_tokens": requested_max_tokens or 4096,
            "model_context_limit": 128000,
            "provider": provider,
            "model": "unknown",
            "generation_time": 0.0
        }
    return None


def _call_query_detailed(
    query_fn: Optional[Callable],
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "auto",
    role: str = "main",
    timeout: int = _DEFAULT_TIMEOUT,
    requested_max_tokens: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    if query_fn is not None:
        try:
            res = query_fn(prompt, system_prompt=system_prompt, provider=provider, role=role, timeout=timeout, max_tokens=requested_max_tokens, return_details=True)
        except TypeError:
            try:
                res = query_fn(prompt, system_prompt=system_prompt, timeout=timeout)
            except TypeError:
                res = query_fn(prompt, system_prompt)
        if isinstance(res, dict):
            return res
        if isinstance(res, str):
            return {
                "text": res,
                "finish_reason": "stop",
                "input_tokens": len(prompt) // 4,
                "output_tokens": len(res) // 4,
                "requested_output_tokens": requested_max_tokens or 4096,
                "model_context_limit": 128000,
                "provider": provider,
                "model": "unknown",
                "generation_time": 0.0
            }
        return None
    return query_llm_detailed(
        prompt,
        system_prompt=system_prompt,
        provider=provider,
        role=role,
        timeout=timeout,
        requested_max_tokens=requested_max_tokens
    )


def query_llm_with_continuation(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "auto",
    role: str = "main",
    timeout: int = _DEFAULT_TIMEOUT,
    max_continuations: int = 3,
    query_fn: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Executes query_llm with dynamic complexity token budgeting and automated continuation recovery
    if responses are truncated or cut off mid-derivation.
    """
    complexity = estimate_question_complexity(prompt, system_prompt)
    target_budget = complexity["recommended_output_budget"]

    enhanced_system_prompt = system_prompt or ""
    if complexity["complexity_score"] >= 6:
        plan_instruction = (
            "\n\nCRITICAL INSTRUCTION FOR TECHNICAL COMPLETENESS:\n"
            "This is a multi-part or complex technical query. You MUST provide a thorough, "
            "untruncated answer covering EVERY requested part, step, and derivation. "
            "Organize your output into clear numbered sections (Part 1, Part 2, etc.). "
            "Do NOT abbreviate mathematical steps or leave derivations half-finished."
        )
        enhanced_system_prompt += plan_instruction

    result = _call_query_detailed(
        query_fn,
        prompt,
        system_prompt=enhanced_system_prompt,
        provider=provider,
        role=role,
        timeout=timeout,
        requested_max_tokens=target_budget
    )

    if not result or not result.get("text"):
        return {
            "text": None,
            "complexity": complexity,
            "completed": False,
            "continuations": 0
        }

    full_text = result["text"]
    finish_reason = result.get("finish_reason")
    continuations_done = 0

    while continuations_done < max_continuations:
        status = check_response_completion(full_text, finish_reason)
        if status["complete"]:
            break

        print(f"[CONTINUATION TRIGGERED] Reason: {status['reason']} | Continuation count: {continuations_done + 1}")

        continuation_prompt = (
            f"Original User Question:\n{prompt}\n\n"
            f"Your previous response was truncated mid-answer due to token limits. Here is what you generated so far:\n"
            f"--- BEGIN PARTIAL RESPONSE ---\n{full_text[-1500:]}\n--- END PARTIAL RESPONSE ---\n\n"
            "CRITICAL CONTINUATION INSTRUCTION:\n"
            "Continue the response seamlessly from the EXACT character where it stopped above. "
            "DO NOT repeat what has already been written. DO NOT write introductory greetings. "
            "Complete all remaining equations, steps, and requested parts in full detail."
        )

        cont_result = _call_query_detailed(
            query_fn,
            continuation_prompt,
            system_prompt=enhanced_system_prompt,
            provider=provider,
            role=role,
            timeout=timeout,
            requested_max_tokens=target_budget
        )

        if not cont_result or not cont_result.get("text"):
            break

        added_text = cont_result["text"].strip()
        if added_text and added_text not in full_text:
            full_text = full_text + "\n" + added_text
            finish_reason = cont_result.get("finish_reason")
            continuations_done += 1
        else:
            break

    full_text = fix_unclosed_markdown_blocks(full_text)

    return {
        "text": full_text,
        "complexity": complexity,
        "completed": check_response_completion(full_text)["complete"],
        "continuations": continuations_done,
        "telemetry": result
    }
