import os
import shutil
import tempfile
import asyncio
import json
import traceback
import csv
import random
import sys
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import backend.config
from database.store import store
from backend import hf_datasets as hf

app = FastAPI(title="AutoML Scientist Engine API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def reconcile_interrupted_runs():
    """Startup reconciliation: pipeline runs live in background threads of the
    previous process, so after a restart any project still marked
    QUEUED / IN_PROGRESS / RUNNING is a ghost run. Mark those FAILED (with an
    explicit log + event) so they can be honestly resumed or discarded."""
    try:
        reconciled = store.reconcile_stale_runs()
        if reconciled:
            print(f"[STARTUP RECONCILIATION] Marked interrupted run(s) as FAILED: {', '.join(reconciled)}")
    except Exception as exc:
        print(f"[STARTUP RECONCILIATION WARNING]: {exc}")

def get_datasets_dir():
    local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_datasets")
    try:
        os.makedirs(local_dir, exist_ok=True)
        test_file = os.path.join(local_dir, ".writable_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return local_dir
    except Exception:
        tmp_dir = os.path.join(tempfile.gettempdir(), "automl_scientist_datasets")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

DATASETS_DIR = get_datasets_dir()

def _generate_auto_benchmark_dataset(path: str):
    """Generates a realistic credit card fraud detection benchmark dataset using pure Python stdlib."""
    import csv
    import random

    rng = random.Random(42)
    n_samples = 300
    n_fraud = 25

    rows = []
    headers = ['transaction_id', 'time_seconds', 'amount', 'v1', 'v2', 'v3', 'v4', 'is_fraud']

    # Non-fraud samples
    for i in range(n_samples - n_fraud):
        tx_id = f"tx_{i:04d}"
        t_sec = round(rng.uniform(0, 86400), 2)
        amt = round(rng.expovariate(1.0 / 50.0), 2)
        v1 = round(rng.gauss(0, 1), 4)
        v2 = round(rng.gauss(0, 1), 4)
        v3 = round(rng.gauss(0, 1), 4)
        v4 = round(rng.gauss(0, 1), 4)
        rows.append([tx_id, t_sec, amt, v1, v2, v3, v4, 0])

    # Fraud samples (distinct distributions)
    for i in range(n_fraud):
        tx_id = f"tx_{n_samples - n_fraud + i:04d}"
        t_sec = round(rng.choice([rng.uniform(0, 18000), rng.uniform(72000, 86400)]), 2)
        amt = round(rng.expovariate(1.0 / 300.0), 2)
        v1 = round(rng.gauss(-2.5, 1.5), 4)
        v2 = round(rng.gauss(2.0, 1.2), 4)
        v3 = round(rng.gauss(-3.0, 1.8), 4)
        v4 = round(rng.gauss(2.8, 1.1), 4)
        rows.append([tx_id, t_sec, amt, v1, v2, v3, v4, 1])

    rng.shuffle(rows)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def safe_docker_check() -> bool:
    try:
        from sandbox.runner import is_docker_available
        return is_docker_available()
    except Exception:
        return False

# Global Exception Handler to ensure ALL errors are returned as JSON
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc) or "An unexpected server error occurred."
    print(f"[API ERROR] {request.method} {request.url.path}: {error_msg}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_msg,
            "code": "INTERNAL_SERVER_ERROR",
            "path": request.url.path
        }
    )

@app.get("/api/health")
def health_check():
    """Health check endpoint for API dependencies."""
    from backend.llm import get_llm_telemetry
    llm_configured = bool(os.environ.get("OPENAI_API_KEY"))
    docker_ready = safe_docker_check()
    return {
        "status": "healthy",
        "api": True,
        "database": True,
        "llm": llm_configured,
        "docker": docker_ready,
        "llmExecution": get_llm_telemetry(),
    }

@app.get("/api/config")
def config_status():
    """Returns system configuration status without exposing secrets."""
    from backend.llm import get_llm_telemetry
    return {
        "openai": {
            "configured": bool(os.environ.get("OPENAI_API_KEY"))
        },
        "database": {
            "configured": True,
            "type": "File-backed JSON Store"
        },
        "docker": {
            "available": safe_docker_check()
        },
        "llmExecution": get_llm_telemetry(),
        "search": {
            "provider": os.environ.get("SEARCH_PROVIDER", "auto")
        },
    }

@app.get("/api/settings")
def get_settings():
    st = store.get_settings()
    docker_ready = safe_docker_check()
    st["dockerAvailable"] = docker_ready
    st["sandboxMode"] = "Docker Sandbox (Isolated Container)" if docker_ready else "Process Sandbox (Subprocess isolation)"
    # Bug 5 disclosure: the stored settings can say "Not configured" while the
    # deployment actually has provider API keys in its environment (the engine
    # then really is LLM-driven). Report the truthful effective state.
    from backend import llm as llm_mod
    env_keys = llm_mod.any_provider_configured()
    st["apiKeySet"] = bool(st.get("apiKeySet")) or env_keys
    if env_keys and (not st.get("llmProvider") or st.get("llmProvider") == "Not configured"):
        st["llmProvider"] = "Auto (provider API key detected)"
    st["mlRuntimeAvailable"] = not hf.ml_runtime_missing()
    return st

@app.post("/api/settings")
def update_settings(payload: dict):
    store.update_settings(payload)
    return {"status": "ok", "settings": store.get_settings()}

@app.post("/api/chat")
async def chat_endpoint(payload: dict):
    """
    Conversational AI Chat Endpoint powered by Intent Router.
    Routes incoming user messages into intents (CONFIRM_PENDING_ACTION, EXPLANATION, RESEARCH_START, RESEARCH_FOLLOWUP, RESEARCH_CONTROL, REPORT_REQUEST, TECHNICAL_DETAILS, CASUAL_CHAT).
    Ensures casual chat does NOT mutate research state or create unwanted projects.
    """
    from backend.intent_router import handle_intent_message
    message = payload.get("message", "").strip()
    active_project_id = payload.get("projectId")
    conversation_id = payload.get("conversationId", "default-session")
    request_id = str(payload.get("requestId") or "")
    user_message_id = str(payload.get("messageId") or "")
    import uuid
    response_message_id = str(uuid.uuid4())

    # Safe correlation diagnostics: never log message text, prompts, or secrets.
    print(
        f"[CHAT REQUEST] conversation_id={conversation_id} "
        f"message_id={user_message_id or 'generated'} request_id={request_id or 'generated'}"
    )
    payload_pending_action = payload.get("pendingAction")
    payload_last_topic = payload.get("lastTopic")

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    store.record_message(
        conversation_id, "user", message, research_id=active_project_id,
        message_id=user_message_id or None,
    )

    from backend import llm as llm_mod
    from backend.research_modes import (
        AUTONOMOUS as AUTONOMOUS_MODE,
        make_activity, resolve_mode, set_session_mode,
        mode_requested_in_message, selection_decision,
    )
    llm_mod.begin_engine_trace()

    # Research mode resolution (directive §2): explicit request field wins,
    # then an in-chat switch ("switch to autonomous mode"), then the session
    # choice, then the persisted app setting. Default stays GUIDED.
    sess_for_mode = store.get_session(conversation_id)
    requested_mode = payload.get("researchMode")
    mode_msg_mode = mode_requested_in_message(message)
    effective_mode = resolve_mode(
        requested_mode,
        sess_for_mode,
        store.get_settings(),
    )
    if mode_msg_mode:
        effective_mode = mode_msg_mode
        set_session_mode(conversation_id, mode_msg_mode)
    elif requested_mode:
        set_session_mode(conversation_id, requested_mode)
    # An explicit in-chat mode switch short-circuits everything else (no LLM
    # call, no accidental project mutation). The response still carries the
    # full correlation contract so the UI can match it to the request.
    if mode_msg_mode:
        mode_reply = (
            f"Research mode set to {mode_msg_mode.title()}. "
            + {
                "AUTONOMOUS": "I'll now select datasets and run experiments on my own, pausing only when a real decision needs you.",
                "GUIDED": "I'll check with you before important steps like choosing a dataset.",
                "MANUAL": "You steer — I'll propose each stage and wait for your go-ahead.",
            }[mode_msg_mode]
        )
        store.record_message(
            conversation_id, "assistant", mode_reply,
            intent="MODE_SWITCH", message_id=response_message_id,
        )
        return {
            "intent": "MODE_SWITCH",
            "response": mode_reply,
            "action": "SET_RESEARCH_MODE",
            "researchMode": mode_msg_mode,
            "projectId": active_project_id,
            "pendingAction": None,
            "activity": [make_activity(request_id, user_message_id, "PLANNING", "completed", f"Research mode set to {mode_msg_mode}")],
            "requestId": request_id or None,
            "responseToMessageId": user_message_id or None,
            "messageId": response_message_id,
            "conversationId": conversation_id,
        }
    res = handle_intent_message(
        message=message, 
        active_project_id=active_project_id, 
        session_id=conversation_id,
        payload_pending_action=payload_pending_action,
        payload_last_topic=payload_last_topic
    )
    action = res.get("action")

    # Bug 5 disclosure: if the handler tried an LLM and none responded, the
    # visible text necessarily came from the built-in rule-based engine — say so.
    if action in (None, "NONE") and res.get("response"):
        disclosure = llm_mod.engine_disclosure()
        if disclosure and disclosure.strip() not in res["response"]:
            res["response"] = res["response"] + disclosure

    if action == "START_RESEARCH":
        # Dataset discovery — mode-aware. We NEVER auto-train on a randomly
        # generated dataset during normal chat. In AUTONOMOUS mode a
        # clearly-best candidate is selected and the pipeline continues on its
        # own; in GUIDED (default) the user approves. In both modes the same
        # candidate comparison and ranking runs first.
        research_goal = res.get("researchQuery") or message
        hf_ref = res.get("hfRef") or hf.parse_hf_reference(message)
        request_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
        job_id = f"job-{uuid.uuid4().hex[:12]}"

        try:
            if hf_ref.get("kind") == "specific":
                repo_id = hf_ref["repo_id"]
                info = hf.inspect_dataset(repo_id)
                cand = _info_to_candidate(info)
                cand["userSelected"] = True
                cand["score"], cand["reasons"] = hf.score_candidate(cand, research_goal)
                cand["reasons"] = ["You linked this dataset directly, so I'll use it exactly as provided."] + cand["reasons"]
                # A user-linked dataset IS the explicit human decision — the
                # pipeline starts in every mode without further approval.
                linked_project_id = _approve_dataset(repo_id, research_goal)["projectId"]
                res.update({
                    "action": "START_RESEARCH",
                    "researchQuery": research_goal,
                    "candidates": [cand],
                    "recommendation": cand,
                    "projectId": linked_project_id,
                    "response": (
                        f"I recognized the Hugging Face dataset you linked: {repo_id}.\n\n"
                        f"It has {cand.get('featureCount') or 'several'} features, a clear "
                        f"'{cand.get('targetColumn')}' target, and a {cand.get('license') or 'declared'} license. "
                        f"I've loaded it and started the research pipeline."
                    ),
                })
            else:
                # A bare discovery URL (https://huggingface.co/datasets) means
                # "find me datasets" — search with a generic ML goal instead of
                # the literal URL text.
                if hf_ref.get("kind") == "general":
                    research_goal = "machine learning"
                lead = f"I'll look for datasets that could help {research_goal.lower().rstrip('.')}.\n\n"
                search_activity = []
                search_activity.append(make_activity(request_id, job_id, "PLANNING", "completed", "Research goal understood"))
                search_activity.append(make_activity(request_id, job_id, "DATASET_SEARCH", "running", "Finding relevant datasets"))
                try:
                    cands = hf.search_datasets(research_goal, limit=6)
                except Exception as search_err:
                    # Directive §13: say the source failed and try to continue
                    # honestly — never silently return an unrelated result.
                    print(f"[DATASET SEARCH ERROR]: {search_err}")
                    search_activity.append(make_activity(request_id, job_id, "DATASET_SEARCH", "failed", "Dataset search failed — trying another approach"))
                    res.update({
                        "action": "NONE",
                        "response": (
                            "Dataset search failed. I'll try another source. "
                            "Meanwhile, you can paste a specific dataset URL "
                            "(https://huggingface.co/datasets/owner/name) and I'll load it directly."
                        ),
                        "researchQuery": research_goal,
                        "activity": search_activity,
                    })
                else:
                    search_activity.append(make_activity(request_id, job_id, "DATASET_SEARCH", "completed", f"Found {len(cands)} candidate datasets"))
                    search_activity.append(make_activity(request_id, job_id, "DATASET_EVALUATION", "running", "Comparing datasets"))
                    comp = hf.compare_and_recommend(cands, research_goal, top_n=4)
                    rec = comp.get("recommendation")
                    if rec:
                        try:
                            info = hf.inspect_dataset(rec["repoId"])
                            rec["rowCountPreview"] = info.get("rowCount")
                            rec["targetColumn"] = info.get("targetColumn")
                            rec["featureCount"] = info.get("featureCount")
                            rec["minorityClassPct"] = info.get("minorityClassPct")
                            rec["classDistribution"] = info.get("classDistribution")
                            rec["splits"] = [s for s in (info.get("availableSplits") or {}).keys() if s in ("train", "test", "validation")]
                        except Exception as inspect_err:
                            print(f"[DATASET INSPECT WARNING]: {inspect_err}")
                    search_activity.append(make_activity(request_id, job_id, "DATASET_EVALUATION", "completed", "Dataset comparison complete"))

                    decision = selection_decision(comp, effective_mode)
                    search_activity.append(make_activity(request_id, job_id, "DATASET_SELECTED", "running", "Selecting a dataset"))

                    # A deployment without the ML runtime (e.g. the Vercel
                    # serverless bundle) can search and compare datasets but
                    # physically cannot train. Pausing there is a GENUINE
                    # constraint (§11), not an unnecessary stop: selecting a
                    # dataset and then failing to load it would be dishonest.
                    missing_runtime = hf.ml_runtime_missing()
                    if decision["decision"] == "AUTO_SELECT" and missing_runtime:
                        decision = {
                            "decision": "ASK_USER",
                            "dataset": decision["dataset"],
                            "reason": "the ML runtime for training is not available in this deployment",
                        }
                        if rec:
                            reason = (rec['reasons'][0] if rec['reasons']
                                      else 'it fits the task well').lower().rstrip('.')
                            if reason.split(' ', 1)[0] in ('matches', 'has', 'is', 'uses', 'contains'):
                                reason = f"it {reason}"
                            summary = (
                                f"I found {len(comp['candidates'])} relevant datasets.\n\n"
                                f"I'd select {rec['repoId']} because {reason}. However, this deployment can't run the "
                                "training pipeline (no ML runtime installed), so I need you to approve the dataset — "
                                "runs execute where the full engine is available (locally or via Docker)."
                            )
                        else:
                            summary = "I couldn't find a suitable dataset automatically."
                        search_activity.append(make_activity(request_id, job_id, "WAITING_FOR_USER", "waiting", "Waiting for your dataset choice"))
                        res.update({
                            "action": "RECOMMEND_DATASETS",
                            "researchQuery": research_goal,
                            "candidates": comp["candidates"],
                            "recommendation": rec,
                            "selectionMode": effective_mode,
                            "response": lead + summary,
                        })

                    elif decision["decision"] == "AUTO_SELECT":
                        # Directive §3: clearly-best candidate -> select it and
                        # CONTINUE. The cards stay available as information, and
                        # the user can still override with another dataset.
                        chosen = decision["dataset"]
                        search_activity.append(make_activity(
                            request_id, job_id, "DATASET_SELECTED", "completed",
                            f"Selected {chosen.get('repoId')}"))
                        try:
                            approved = _approve_dataset(chosen["repoId"], research_goal)
                            summary = (
                                f"Found {len(comp['candidates'])} relevant datasets.\n\n"
                                f"Selected {chosen['repoId']} because {str(decision['reason']).lower().rstrip('.')}.\n\n"
                                "I'm analyzing the data and training the first models now — you can watch the progress below. "
                                "If you'd rather use a different dataset, pick one of the cards and I'll continue from there."
                            )
                            res.update({
                                "action": "START_RESEARCH",
                                "researchQuery": research_goal,
                                "candidates": comp["candidates"],
                                "recommendation": chosen,
                                "selectedDataset": chosen.get("repoId"),
                                "selectionMode": "AUTONOMOUS",
                                "projectId": approved["projectId"],
                                "project": approved.get("project"),
                                "response": lead + summary,
                            })
                        except Exception as auto_err:
                            print(f"[AUTONOMOUS DATASET ERROR]: {auto_err}")
                            search_activity.append(make_activity(request_id, job_id, "DATASET_SELECTED", "failed", "Could not load the selected dataset"))
                            res.update({
                                "action": "NONE",
                                "researchQuery": research_goal,
                                "candidates": comp["candidates"],
                                "recommendation": rec,
                                "response": (
                                    f"I selected {chosen['repoId']} but couldn't load it ({auto_err}). "
                                    "You can pick another dataset below and I'll continue from there."
                                ),
                            })
                    else:
                        # GUIDED/MANUAL, or a genuine near-tie/no-fit in
                        # AUTONOMOUS mode: pause and ask (§11/§14) — the ONLY
                        # legitimate WAITING_FOR_USER for dataset selection.
                        if rec:
                            reason = (rec['reasons'][0] if rec['reasons']
                                      else 'it fits the task well').lower().rstrip('.')
                            if reason.split(' ', 1)[0] in ('matches', 'has', 'is', 'uses', 'contains'):
                                reason = f"it {reason}"
                            if decision["decision"] == "ASK_USER" and effective_mode == AUTONOMOUS_MODE:
                                summary = (
                                    f"I found {len(comp['candidates'])} strong candidates. The choice affects the experiment.\n\n"
                                    f"I'd start with {rec['repoId']} because {reason}, but several options are close — "
                                    "which dataset should I use?"
                                )
                            else:
                                summary = (
                                    f"I recommend starting with {rec['repoId']} because {reason}.\n\n"
                                    "Choose a dataset below to continue."
                                )
                        else:
                            summary = (
                                "I couldn't find a suitable dataset automatically. "
                                "Try rephrasing with the core topic (e.g. \"customer churn\" instead of "
                                "\"optimize churn prediction for imbalanced data\"), or paste a dataset URL "
                                "(https://huggingface.co/datasets/owner/name) and I'll load it directly."
                            )
                        search_activity.append(make_activity(request_id, job_id, "WAITING_FOR_USER", "waiting", "Waiting for your dataset choice"))
                        res.update({
                            "action": "RECOMMEND_DATASETS",
                            "researchQuery": research_goal,
                            "candidates": comp["candidates"],
                            "recommendation": rec,
                            "response": lead + summary,
                        })
                    res["activity"] = search_activity
        except Exception as disc_err:
            print(f"[DATASET DISCOVERY ERROR]: {disc_err}")
            res.update({
                "action": "NONE",
                "response": (
                    f"I tried to search Hugging Face for suitable datasets but ran into a problem: {disc_err}. "
                    f"You can paste a specific dataset URL (e.g. https://huggingface.co/datasets/owner/name) and I'll load it directly."
                ),
            })

    elif action == "APPROVE_DATASET":
        # Confirmation of a previously recommended dataset.
        repo_id = res.get("repoId")
        if repo_id:
            try:
                approved = _approve_dataset(repo_id, res.get("researchQuery") or message)
                res.update(approved)
            except Exception as approve_err:
                print(f"[DATASET APPROVE ERROR]: {approve_err}")
                res.update({
                    "action": "NONE",
                    "pendingAction": None,
                    "response": f"I couldn't start that dataset run: {approve_err}",
                })

    # A safe, compact post-hoc work summary. It contains only completed,
    # observable application actions — never model reasoning, prompts, or keys.
    # Mode-aware discovery above may have already built REAL activity events
    # (with stage/status per the event contract); those take precedence.
    labels = None
    if not res.get("activity"):
        activity_by_intent = {
            "MATHEMATICS": ["Understanding the problem", "Solving with the math tool", "Checking the result", "Preparing the explanation"],
            "CURRENT_INFORMATION": ["Checking current information", "Verifying the result", "Preparing the answer"],
            "CODING": ["Understanding requirements", "Writing the code", "Preparing the answer"],
            "EXPLANATION": ["Understanding your question", "Preparing the answer"],
            "ENTITY_INFORMATION": ["Understanding your question", "Preparing the answer"],
        }
        labels = activity_by_intent.get(res.get("intent"), ["Understanding your question", "Preparing the answer"])
        if res.get("action") == "RECOMMEND_DATASETS":
            labels = ["Understanding the research objective", "Searching datasets", "Preparing dataset options"]
        elif res.get("action") == "START_RESEARCH":
            labels = ["Understanding the research goal", "Selecting the dataset", "Starting the research pipeline"]
    if labels:
        res["activity"] = [{"id": f"{request_id or 'request'}-{i}", "label": label, "status": "completed"} for i, label in enumerate(labels)]
    else:
        for i, ev in enumerate(res.get("activity") or []):
            ev.setdefault("id", f"{request_id or 'request'}-{i}")

    store.record_message(
        conversation_id, "assistant", res.get("response", ""),
        intent=res.get("intent"), topic=res.get("lastTopic"),
        research_id=res.get("projectId") or active_project_id,
        pending_action=res.get("pendingAction"),
        message_id=response_message_id,
    )

    res.update({
        "requestId": request_id or None,
        "responseToMessageId": user_message_id or None,
        "messageId": response_message_id,
        "conversationId": conversation_id,
    })
    print(
        f"[CHAT RESPONSE] conversation_id={conversation_id} "
        f"response_to_message_id={user_message_id or 'unknown'} "
        f"request_id={request_id or 'unknown'} intent={res.get('intent')}"
    )
    return res


def _info_to_candidate(info: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a full inspect_dataset() result into a comparison card shape."""
    return {
        "repoId": info.get("repoId"),
        "author": info.get("author"),
        "name": info.get("name"),
        "downloads": info.get("downloads"),
        "likes": info.get("likes"),
        "license": info.get("license"),
        "sizeCategory": info.get("sizeCategory"),
        "format": info.get("format"),
        "taskCategories": info.get("taskCategories"),
        "topics": info.get("topics"),
        "description": info.get("description"),
        "url": info.get("url"),
        "revision": info.get("revision"),
        "rowCountPreview": info.get("rowCount"),
        "targetColumn": info.get("targetColumn"),
        "featureCount": info.get("featureCount"),
        "minorityClassPct": info.get("minorityClassPct"),
        "classDistribution": info.get("classDistribution"),
        "splits": [s for s in (info.get("availableSplits") or {}).keys() if s in ("train", "test", "validation")],
    }


def _approve_dataset(repo_id: str, research_goal: str, budget: int = 60, max_experiments: int = 5) -> Dict[str, Any]:
    """Download the approved dataset, create a project, and launch the real pipeline."""
    import uuid
    from agents.orchestrator import run_research_pipeline_async

    missing = hf.ml_runtime_missing()
    if missing:
        # Fail fast with an honest, actionable message instead of letting a raw
        # ModuleNotFoundError bubble up mid-download ("No module named 'pandas'").
        raise RuntimeError(hf.ml_runtime_message(missing))

    dl = hf.download_dataset(repo_id)
    project_id = f"proj-{uuid.uuid4().hex[:6]}"

    meta = {
        "source": "huggingface",
        "url": dl["url"],
        "repoId": dl["repoId"],
        "license": dl.get("license"),
        "revision": dl.get("revision"),
        "splits": list(dl.get("splits", {}).keys()),
        "splitStrategy": ("Dataset's own provided train/test split"
                          if dl.get("testPath") else "Stratified 80/20 train/test split (seed 42)"),
        "description": None,
    }

    store.create_project(
        project_id=project_id,
        name=f"Research: {research_goal[:35]}",
        objective=research_goal,
        dataset_name=repo_id,
        budget=budget,
        provider="Heuristic / Rule-based",
        max_experiments=max_experiments,
        # Persist the launch context so the run can be resumed (relaunched)
        # after a server restart without re-downloading the dataset.
        dataset_path=dl["primaryPath"],
        test_path=dl.get("testPath"),
        dataset_meta=meta,
    )

    try:
        run_research_pipeline_async(project_id, dl["primaryPath"], meta, dl.get("testPath"))
    except Exception as err:
        print(f"[APPROVE LAUNCH WARNING]: {err}")
        store.add_agent_log(project_id, "RESEARCH_ORCHESTRATOR", f"Launch error: {err}", "FAILED")
        store.update_project(project_id, {"status": "FAILED", "errorDetail": str(err)})

    return {
        "action": "START_RESEARCH",
        "projectId": project_id,
        "project": store.get_project(project_id),
        "dataset": {
            "repoId": repo_id,
            "url": dl["url"],
            "splits": dl.get("rowCounts"),
            "targetColumn": dl.get("targetColumn"),
            "license": dl.get("license"),
            "revision": dl.get("revision"),
        },
        "response": f"Approved. I've loaded {repo_id} and I'm now analyzing it and training the first models.",
    }

@app.get("/api/datasets/search")
def datasets_search(q: str = Query(..., description="Research goal / search query"), limit: int = Query(6)):
    """Search Hugging Face for candidate datasets and rank them for the goal."""
    try:
        cands = hf.search_datasets(q, limit=limit)
        comp = hf.compare_and_recommend(cands, q, top_n=4)
        return {"success": True, "goal": q, **comp}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Dataset search failed: {e}")

@app.post("/api/datasets/inspect")
def datasets_inspect(payload: dict):
    """Inspect a specific dataset (by URL or repo id) and return REAL metadata."""
    ref = payload.get("url") or payload.get("repoId") or ""
    parsed = hf.parse_hf_reference(ref)
    # Trust the parser: it already recognises both HF URLs and bare "owner/name"
    # repo ids as kind=='specific'. Anything else (non-HF URLs, the bare
    # /datasets discovery page, free text) is a client error, not an upstream
    # failure — so return 400 instead of attempting a fetch that would 502.
    repo_id = parsed.get("repo_id")
    if parsed.get("kind") != "specific" or not repo_id:
        raise HTTPException(status_code=400, detail="Please provide a specific dataset URL like https://huggingface.co/datasets/owner/name or a repo id like owner/name")
    try:
        info = hf.inspect_dataset(repo_id)
        return {"success": True, "info": info, "card": _info_to_candidate(info)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Dataset inspection failed: {e}")

@app.post("/api/datasets/approve")
def datasets_approve(payload: dict):
    """User approved a dataset: download it, create a project, launch the real pipeline."""
    repo_id = payload.get("repoId")
    if not repo_id:
        raise HTTPException(status_code=400, detail="repoId is required to approve a dataset.")
    missing = hf.ml_runtime_missing()
    if missing:
        raise HTTPException(status_code=422, detail=hf.ml_runtime_message(missing))
    research_goal = payload.get("researchQuery") or f"Improve modeling on {repo_id}"
    budget = int(payload.get("budget", 60))
    max_experiments = int(payload.get("maxExperiments", 5))
    try:
        return {"success": True, **_approve_dataset(repo_id, research_goal, budget, max_experiments)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Dataset approval/loading failed: {e}")

@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    """Return the stored per-message history for a conversation (section 3)."""
    return store.get_messages(conversation_id)


@app.post("/api/files/analyze")
async def analyze_file(file: UploadFile = File(...)):
    """Parse a supported upload and return only evidence actually extracted."""
    from backend.file_analysis import parse_file_bytes
    try:
        content = await file.read()
        parsed = parse_file_bytes(file.filename or "", content)
        text = parsed.pop("text")
        return {"success": True, "filename": os.path.basename(file.filename or ""),
                **parsed, "textPreview": text[:4000], "charactersExtracted": len(text)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/projects")
def list_projects():
    return store.list_projects()

@app.post("/api/research")
async def start_research(
    objective: str = Form(...),
    budget: int = Form(60),
    llm_provider: str = Form("Heuristic / Rule-based"),
    max_experiments: int = Form(5),
    file: Optional[UploadFile] = File(None)
):
    try:
        # Validate Research Objective
        obj_clean = objective.strip()
        meaningless_inputs = ["hi", "hello", "test", "demo", "run", "a", "asdf", "123", "hey", "testing", "objective"]
        if len(obj_clean) < 10 or obj_clean.lower() in meaningless_inputs:
            raise HTTPException(
                status_code=400,
                detail="Please enter a meaningful machine-learning research objective. (e.g. 'Improve fraud detection while increasing recall and controlling false positives.')"
            )

        missing = hf.ml_runtime_missing()
        if missing:
            # The pipeline cannot download data, train, or report without the ML
            # stack. Creating a project here would just produce a run that dies
            # silently, so refuse up front with the honest reason.
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": hf.ml_runtime_message(missing),
                    "code": "ML_RUNTIME_UNAVAILABLE",
                },
            )

        import uuid
        project_id = f"proj-{uuid.uuid4().hex[:6]}"
        dataset_path = None
        dataset_name = "Not provided"

        if file and file.filename:
            dataset_name = file.filename
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in {".csv", ".parquet", ".json"}:
                raise HTTPException(status_code=400, detail="Research datasets must be CSV, Parquet, or JSON files.")
            content = await file.read()
            if len(content) > 100 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Research dataset exceeds the 100 MB upload limit.")
            dataset_path = os.path.join(DATASETS_DIR, f"{project_id}{ext}")
            with open(dataset_path, "wb") as buffer:
                buffer.write(content)
        else:
            dataset_name = "Auto: credit_card_fraud_benchmark.csv"
            dataset_path = os.path.join(DATASETS_DIR, f"{project_id}_auto.csv")
            _generate_auto_benchmark_dataset(dataset_path)

        project = store.create_project(
            project_id=project_id,
            name=f"Research: {objective[:35]}",
            objective=objective,
            dataset_name=dataset_name,
            budget=budget,
            provider=llm_provider,
            max_experiments=max_experiments,
            dataset_path=dataset_path,
            test_path=None,
            dataset_meta=None,
        )

        try:
            # A research run may download data, train several baselines and run
            # generated experiments. It must not occupy the normal HTTP request
            # (or a Vercel function) until completion. The project row and SSE
            # endpoint are the durable/status surface; the worker updates them.
            from agents.orchestrator import run_research_pipeline_async
            launched = run_research_pipeline_async(project_id, dataset_path)
            if not launched:
                raise RuntimeError("Research run was not queued because it is already active.")
        except Exception as orchestrator_err:
            print(f"[ORCHESTRATOR LAUNCH ERROR]: {orchestrator_err}")
            store.add_agent_log(project_id, "RESEARCH_ORCHESTRATOR", f"Launch error: {orchestrator_err}", "FAILED")
            store.update_project(project_id, {"status": "FAILED", "errorDetail": str(orchestrator_err)})

        updated_project = store.get_project(project_id) or project

        return {"success": True, "status": updated_project.get("status", "COMPLETED"), "projectId": project_id, "project": updated_project}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[START RESEARCH ERROR]: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "RESEARCH_START_FAILED"
            }
        )

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.post("/api/projects/{project_id}/control")
def set_control_signal(project_id: str, payload: dict):
    if not store.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    signal = payload.get("signal", "RUN") # "STOP", "PAUSE", "RUN"
    if signal == "RUN" and store.get_project(project_id):
        # Resuming a run whose pipeline thread is gone (server restart, crash)
        # relaunches the pipeline from the stored dataset path; a live (paused)
        # run is just unpaused.
        from agents.orchestrator import resume_pipeline
        resume = resume_pipeline(project_id)
        return {"status": "ok", "resume": resume, "project": store.get_project(project_id)}
    store.set_control_signal(project_id, signal)
    return {"status": "ok", "project": store.get_project(project_id)}

@app.get("/api/projects/{project_id}/stream")
async def stream_project_events(project_id: str):
    """
    Server-Sent Events (SSE) streaming endpoint for live research telemetry.
    """
    async def event_generator():
        last_log_count = 0
        while True:
            proj = store.get_project(project_id)
            if not proj:
                yield f"data: {json.dumps({'error': 'Project not found'})}\n\n"
                break

            logs = proj.get("agentLogs", [])
            if len(logs) > last_log_count:
                new_logs = logs[last_log_count:]
                last_log_count = len(logs)
                event_payload = {
                    "projectId": project_id,
                    "status": proj.get("status"),
                    "activeAgent": proj.get("activeAgent"),
                    "stageStates": proj.get("stageStates"),
                    "researchQuestion": proj.get("researchQuestion"),
                    "experimentsCount": proj.get("experimentsCount"),
                    "bestMetric": proj.get("bestMetric"),
                    "computeUsed": proj.get("computeUsed"),
                    "newLogs": new_logs,
                    "events": proj.get("events", [])
                }
                yield f"data: {json.dumps(event_payload)}\n\n"

            if proj.get("status") in ["COMPLETED", "FAILED", "STOPPED"]:
                yield f"data: {json.dumps({'event': 'finished', 'status': proj.get('status')})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/projects/{project_id}/dataset")
def get_dataset_report(project_id: str):
    report = store.get_dataset_report(project_id)
    if not report:
        return JSONResponse(status_code=200, content=None)
    return report

@app.get("/api/projects/{project_id}/baselines")
def get_baselines(project_id: str):
    return store.get_baselines(project_id)

@app.get("/api/projects/{project_id}/tree")
def get_tree_nodes(project_id: str):
    return store.get_tree_nodes(project_id)

@app.get("/api/projects/{project_id}/error-analysis")
def get_error_analysis(project_id: str):
    analysis = store.get_error_analysis(project_id)
    if not analysis:
        return JSONResponse(status_code=200, content=None)
    return analysis

@app.get("/api/projects/{project_id}/literature")
def get_literature(project_id: str):
    return store.get_literature(project_id)

@app.get("/api/projects/{project_id}/report")
def get_report(project_id: str):
    report = store.get_report(project_id)
    return {"report": report}

@app.get("/api/projects/{project_id}/report/download")
def download_report(project_id: str, fmt: str = Query("md")):
    proj = store.get_project(project_id)
    report_md = store.get_report(project_id) or "Report not generated yet."

    if fmt == "json":
        data = {
            "project": proj,
            "reportMarkdown": report_md,
            "dataset": store.get_dataset_report(project_id),
            "baselines": store.get_baselines(project_id),
            "tree": store.get_tree_nodes(project_id),
            "errorAnalysis": store.get_error_analysis(project_id)
        }
        return Response(content=json.dumps(data, indent=2), media_type="application/json", headers={"Content-Disposition": f"attachment; filename=Research_Report_{project_id}.json"})
    else:
        return Response(content=report_md, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=Research_Report_{project_id}.md"})
