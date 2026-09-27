import os
import json
import re
from typing import Dict, Any, Optional

# Path to configured project identity JSON file
CONFIG_PATH_1 = os.path.join(os.path.dirname(__file__), "config", "project_identity.json")
CONFIG_PATH_2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "project_identity.json")

# Default identity fallback if config file is missing
DEFAULT_IDENTITY = {
    "project": {
        "name": "AI Scientist",
        "type": "AI research assistant",
        "description": "AI Scientist is a general-purpose AI assistant with autonomous deep research, reasoning, machine learning, and software execution capabilities.",
        "website": "https://github.com/ToshitSai/automl-scientist",
        "github": "https://github.com/ToshitSai/automl-scientist",
        "creator": {
            "name": "Toshit Sai Galam",
            "role": "Founder / Creator",
            "education": "B.Tech CSE (AI/ML)",
            "focus": "AI, machine learning, software engineering, and autonomous AI research",
            "bio": "Toshit Sai Galam is a B.Tech Computer Science student specializing in Artificial Intelligence and Machine Learning. He is developing AI Scientist as a general-purpose AI assistant with autonomous research capabilities.",
            "projects": ["AI Scientist"],
            "website": "",
            "github": "https://github.com/ToshitSai",
            "linkedin": ""
        }
    }
}


def load_project_identity() -> Dict[str, Any]:
    """Loads and returns the project identity from configuration files, or fallback if unreadable."""
    for path in [CONFIG_PATH_1, CONFIG_PATH_2]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "project" in data and "creator" in data["project"]:
                        return data
            except Exception as e:
                print(f"[PROJECT IDENTITY LOAD WARNING]: {e}")
    return DEFAULT_IDENTITY


def get_public_creator_profile() -> Dict[str, Any]:
    """Returns ONLY public, sanitized creator profile fields. Never exposes private data."""
    raw = load_project_identity().get("project", {}).get("creator", {})
    allowed_keys = {"name", "role", "education", "focus", "bio", "projects", "website", "github", "linkedin"}
    return {k: raw[k] for k in allowed_keys if k in raw}


def get_public_project_info() -> Dict[str, Any]:
    """Returns ONLY public project identity fields."""
    raw = load_project_identity().get("project", {})
    return {
        "name": raw.get("name", "AI Scientist"),
        "type": raw.get("type", "AI research assistant"),
        "description": raw.get("description", ""),
        "website": raw.get("website", ""),
        "github": raw.get("github", ""),
        "creator": get_public_creator_profile()
    }


# --------------------------------------------------------------------------- #
# Patterns & Semantic Matching
# --------------------------------------------------------------------------- #

# Explicit queries about ChatGPT / OpenAI (Must NOT route to AI Scientist creator)
CHATGPT_OPENAI_RE = re.compile(
    r"\b(who (created|built|made|founded|developed)\s+(chatgpt|openai|gpt|gpt-4|gpt-3\.5|gpt-4o|dall-e|sam altman))\b"
    r"|\b(what is (openai|chatgpt))\b"
    r"|\b(tell me about (openai|chatgpt))\b"
    r"|\b(who is (sam altman|greg brockman|ilya sutskever))\b",
    re.IGNORECASE
)

PROVIDER_NAME_RE = re.compile(
    r"\b(mistral\s+ai|openai|anthropic|google|deepmind|gemini|claude|chatgpt|gpt(?:-\d+(?:\.\d+)?)?)\b",
    re.IGNORECASE,
)

PROVIDER_IDENTITY_LEAK_RE = re.compile(
    r"\b(?:i am|i'm|i am an|i'm an|my specific version was|this version was|this assistant was|this ai was)"
    r"\s+(?:created|built|developed|founded|made|trained|launched)\s+by\s+"
    r"(?:mistral\s+ai|openai|anthropic|google|deepmind|gemini|claude|chatgpt|gpt)\b"
    r"|\b(?:mistral\s+ai|openai|anthropic|google|deepmind|gemini|claude|chatgpt)\s+(?:created|built|developed|founded|made|trained|launched)\s+(?:me|you|this\s+(?:assistant|app|ai|project)|ai\s+scientist)\b",
    re.IGNORECASE,
)

# Queries about underlying model powering AI Scientist
MODEL_POWER_RE = re.compile(
    r"\b(what (model|llm|engine|architecture)\s+(powers|drives|runs|is behind)\s+(you|ai scientist))\b"
    r"|\b(what model powers you)\b"
    r"|\b(what model are you based on)\b"
    r"|\b(are you (powered by|using|run on)\s+(mistral|openai|gemini|anthropic|claude|gpt))\b"
    r"|\b(are you (chatgpt|gpt-4|openai|a gpt|an openai model))\b"
    r"|\b(what llm are you using)\b",
    re.IGNORECASE
)

# Creator / Founder / Builder of AI Scientist ("you" / "u")
CREATOR_RE = re.compile(
    r"\b(who('s|\s+(is|was|are|were))\s+(the\s+|your\s+|ur\s+|a\s+)?(founder|creator|author|builder|developer|maker|owner|designer)\s*(of\s+(you|u|ai scientist|this project|this assistant|this app|this platform|this bot|this ai))?)\b"
    r"|\b(who\s+(created|built|made|founded|developed|designed|authored|started|established)\s+(you|u|this assistant|this app|this platform|ai scientist|this project|this bot|this ai|this))\b"
    r"|\b(who('s|\s+is)\s+behind\s+(you|u|this project|ai scientist|this assistant|this platform|this app|this bot|this ai))\b"
    r"|\b(who\s+(owns|started|established)\s+(you|u|ai scientist|this project|this assistant|this app|this bot))\b"
    r"|\b(who('s|\s+is)\s+the\s+(creator|founder|author|builder|developer|maker|owner|designer)\b)"
    r"|\b(what\s+is\s+(the\s+name\s+of\s+)?(your|ur)?\s*creator'?s\s+name)\b"
    r"|\b(who\s+is\s+toshit(\s+sai)?(\s+galam)?)\b",
    re.IGNORECASE
)

HALLUCINATED_IDENTITY_PATTERNS = [
    re.compile(r"\b(large language model,?\s+(developed|created|trained)\s+by\s+google)\b", re.IGNORECASE),
    re.compile(r"\b(developed\s+by\s+google)\b", re.IGNORECASE),
    re.compile(r"\b(created\s+by\s+google)\b", re.IGNORECASE),
    re.compile(r"\b(trained\s+by\s+google)\b", re.IGNORECASE),
    re.compile(r"\b(i am a large language model,?\s+developed by openai)\b", re.IGNORECASE),
    re.compile(r"\b(i am chatgpt)\b", re.IGNORECASE),
    re.compile(r"\b(i'm chatgpt)\b", re.IGNORECASE),
    re.compile(r"\b(i am mistral|i'm mistral|i am claude|i'm claude|i am gemini|i'm gemini)\b", re.IGNORECASE),
]


def _build_authoritative_project_identity_response() -> str:
    """Return the canonical AI Scientist project identity response."""
    info = get_public_project_info()
    creator = info["creator"]
    return (
        f"AI Scientist was created by **{creator['name']}**.\n\n"
        f"He is a {creator['education']} student specializing in Artificial Intelligence and Machine Learning "
        f"and is developing AI Scientist as a general-purpose AI assistant with autonomous research capabilities.\n\n"
        f"AI Scientist is designed to combine conversational AI, reasoning, tools, and deep autonomous research."
    )


def _response_has_provider_identity_leak(response_text: str) -> bool:
    """Generic safety check: reject provider self-identification when the user is asking about AI Scientist."""
    if not response_text:
        return False
    text = response_text.strip()
    if not text:
        return False

    if PROVIDER_IDENTITY_LEAK_RE.search(text):
        return True

    if re.search(r"\b(?:i am|i'm)\s+(?:mistral\s+ai|openai|anthropic|gemini|google|deepmind|claude|chatgpt|gpt)\b", text, re.IGNORECASE):
        return True

    for pattern in HALLUCINATED_IDENTITY_PATTERNS:
        if pattern.search(text):
            return True

    provider_claims = re.findall(
        r"\b(?:mistral\s+ai|openai|anthropic|google|deepmind|gemini|claude|chatgpt|gpt)\b",
        text,
        re.IGNORECASE,
    )
    if not provider_claims:
        return False

    if re.search(r"\b(?:created|built|developed|founded|made|trained|launched)\b.*\b(?:me|you|this|ai scientist)\b", text, re.IGNORECASE):
        return True

    return False


def sanitize_llm_identity_hallucinations(response_text: str, user_message: str = "") -> str:
    """Reject provider identity leakage only for an AI Scientist identity question.

    Provider names can occur legitimately in an answer about a third party or a
    technical topic.  Replacing such an answer with the creator profile would
    turn unrelated questions into a stale identity response.
    """
    if CHATGPT_OPENAI_RE.search(user_message):
        return response_text

    if not is_identity_intent(user_message):
        return response_text

    if _response_has_provider_identity_leak(response_text):
        return _build_authoritative_project_identity_response()

    return response_text

# Follow-up questions about the creator (education, background, projects)
CREATOR_STUDY_RE = re.compile(
    r"\b(what\s+(does|did)\s+(he|she|they|your creator|toshit)\s+(study|studied|major in))\b"
    r"|\b(what\s+is\s+(his|her|their|your creator'?s)\s+(education|degree|qualification|qualification))\b"
    r"|\b(where\s+does\s+he\s+study)\b",
    re.IGNORECASE
)

CREATOR_BACKGROUND_RE = re.compile(
    r"\b(what\s+is\s+(his|her|their|your creator'?s)\s+(background|focus|specialization|experience))\b"
    r"|\b(what\s+is\s+(he|she|they|your creator|toshit)\s+working\s+on)\b"
    r"|\b(what\s+are\s+(his|her|their|your creator'?s)\s+focus\s+areas)\b",
    re.IGNORECASE
)

CREATOR_PROJECTS_RE = re.compile(
    r"\b(what\s+projects\s+has\s+(he|she|they|your creator|toshit)\s+(built|created|made|developed))\b"
    r"|\b(what\s+has\s+(he|she|they|your creator|toshit)\s+built)\b"
    r"|\b(where\s+can\s+i\s+see\s+(his|her|their|your creator'?s)\s+(work|github|projects))\b",
    re.IGNORECASE
)

PROJECT_INFO_RE = re.compile(
    r"\b(what\s+is\s+ai\s+scientist)\b"
    r"|\b(tell\s+me\s+about\s+ai\s+scientist)\b"
    r"|\b(what\s+does\s+ai\s+scientist\s+do)\b"
    r"|\b(what\s+is\s+the\s+purpose\s+of\s+ai\s+scientist)\b",
    re.IGNORECASE
)

SELF_RE = re.compile(r"^\s*(?:who|what)\s+(?:are|is)\s+(?:you|this assistant|this ai)\s*\??\s*$", re.I)


def identity_system_instruction() -> str:
    """Authoritative, config-derived instruction for any LLM answer path."""
    info = get_public_project_info()
    creator = info["creator"].get("name")
    creator_clause = f"Its configured public creator is {creator}." if creator else "Its creator profile is not configured."
    return (
        f"You are the assistant operating inside the {info['name']} application. "
        f"The application identity is authoritative. "
        f"{creator_clause} When the user asks who created, founded, built, developed, or owns {info['name']}, "
        "answer using the configured AI Scientist project profile. Do not substitute the identity of the underlying "
        "language model provider. The underlying model/provider is an implementation detail unless the user explicitly asks about it. "
        "Never invent creator information. If creator information is not configured, say that it is not available. "
        "For 'who are you', answer as AI Scientist, not as Mistral/ChatGPT/OpenAI/Claude/Gemini."
    )


def configured_model_identity() -> Optional[str]:
    """Return only explicitly configured provider/model information."""
    providers = (("OPENAI", "OPENAI_API_KEY", "OPENAI_MODEL"),
                 ("Gemini", "GEMINI_API_KEY", "GEMINI_MODEL"),
                 ("Anthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
                 ("Mistral", "MISTRAL_API_KEY", "MISTRAL_MODEL"))
    for provider, key, model in providers:
        if os.environ.get(key):
            return f"{provider} / {os.environ.get(model, 'configured default')}"
    return None


def classify_identity_query(message: str) -> Optional[str]:
    """
    Categorizes message into an identity sub-type:
    - None if NOT an identity query or if explicitly asking about ChatGPT/OpenAI.
    - "CREATOR" for founder/creator of AI Scientist.
    - "CREATOR_STUDY" for education follow-up.
    - "CREATOR_BACKGROUND" for focus/background follow-up.
    - "CREATOR_PROJECTS" for projects/work follow-up.
    - "PROJECT_INFO" for what is AI Scientist.
    - "MODEL_POWER" for underlying model question.
    """
    msg = message.strip()

    # If the user is explicitly asking about ChatGPT / OpenAI, do NOT intercept as AI Scientist identity
    if CHATGPT_OPENAI_RE.search(msg):
        return None

    if MODEL_POWER_RE.search(msg):
        return "MODEL_POWER"

    if SELF_RE.search(msg):
        return "SELF"

    if CREATOR_RE.search(msg):
        return "CREATOR"

    if CREATOR_STUDY_RE.search(msg):
        return "CREATOR_STUDY"

    if CREATOR_BACKGROUND_RE.search(msg):
        return "CREATOR_BACKGROUND"

    if CREATOR_PROJECTS_RE.search(msg):
        return "CREATOR_PROJECTS"

    if PROJECT_INFO_RE.search(msg):
        return "PROJECT_INFO"

    return None


def is_identity_intent(message: str) -> bool:
    """Returns True if the message is a project/creator identity query."""
    return classify_identity_query(message) is not None


def handle_identity_response(message: str, last_topic: Optional[str] = None) -> Dict[str, Any]:
    """Generates natural response for project/creator identity queries."""
    sub_type = classify_identity_query(message)
    info = get_public_project_info()
    creator = info["creator"]

    if sub_type == "CREATOR":
        response_text = (
            f"{info['name']} was created by **{creator['name']}**.\n\n"
            f"He is a {creator['education']} student specializing in Artificial Intelligence and Machine Learning "
            f"and is developing {info['name']} as a general-purpose AI assistant with autonomous research capabilities.\n\n"
            f"{info['name']} is designed to combine conversational AI, reasoning, tools, and deep autonomous research."
        )

    elif sub_type == "CREATOR_STUDY":
        response_text = (
            f"**{creator['name']}** is pursuing a **{creator['education']}** degree (Computer Science Engineering "
            f"specializing in Artificial Intelligence and Machine Learning)."
        )

    elif sub_type == "CREATOR_BACKGROUND":
        response_text = (
            f"**{creator['name']}**'s primary focus areas are **{creator['focus']}**.\n\n"
            f"{creator['bio']}"
        )

    elif sub_type == "CREATOR_PROJECTS":
        projects_list = ", ".join(creator.get("projects", [info['name']]))
        github_link = f" (GitHub: {creator['github']})" if creator.get("github") else ""
        response_text = (
            f"**{creator['name']}** is the founder and lead developer of **{info['name']}**.\n\n"
            f"Key Projects: {projects_list}{github_link}."
        )

    elif sub_type == "PROJECT_INFO":
        response_text = (
            f"**{info['name']}** is a {info['type']} created by **{creator['name']}**.\n\n"
            f"{info['description']}\n\n"
            f"Key Capabilities:\n"
            f"- **Autonomous Research Loop**: Planning, literature review, baseline training, hypothesis generation, and experiment execution.\n"
            f"- **General Assistance**: Answering questions across mathematics, coding, logic, and general knowledge.\n"
            f"- **Dataset Discovery**: Integrating directly with Hugging Face Hub for real dataset inspection and analysis."
        )

    elif sub_type == "MODEL_POWER":
        model = configured_model_identity()
        response_text = (f"{info['name']} is the application created by **{creator['name']}**. "
                         + (f"Its currently configured model/provider is **{model}**."
                            if model else "I don't have access to the exact configured underlying model information right now."))

    elif sub_type == "SELF":
        response_text = f"I'm **{info['name']}**, a {info['type']} created by **{creator['name']}**. {info['description']}"

    else:
        # Fallback if unhandled sub_type
        response_text = (
            f"I don't have that specific information in my public creator profile."
        )

    return {
        "intent": "PROJECT_IDENTITY",
        "taskType": "identity",
        "response": response_text,
        "action": "NONE",
        "projectId": None,
        "pendingAction": None,
        "lastTopic": "ai scientist identity"
    }
