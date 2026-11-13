"""Atlas Resume Intelligence & Career Advisory Module.

Extracts structured sections from resumes (education, skills, projects,
experience, certifications), matches candidates to realistic roles based
strictly on demonstrated evidence, performs skills-gap analysis, and formats
natural, human-friendly responses.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


RESUME_KEYWORDS = {
    "resume", "cv", "curriculum vitae", "education", "experience", "projects",
    "skills", "certifications", "internship", "technologies", "b.tech", "cgpa",
    "gpa", "bachelor", "master", "coursework", "academic", "extracurricular"
}

ROLE_QUERY_TRIGGERS = {
    "role", "roles", "job", "jobs", "apply", "career", "careers", "position",
    "positions", "intern", "interns", "internship", "internships", "hire",
    "suitable", "fit", "opportunity", "opportunities", "eligible", "profile"
}


def is_resume_query_or_doc(
    query: str = "",
    filename: str = "",
    text: str = ""
) -> bool:
    """Detect if a query or uploaded document relates to resume analysis."""
    fn_lower = (filename or "").lower()
    q_lower = (query or "").lower()
    text_lower = (text or "").lower()

    if any(k in fn_lower for k in ("resume", "cv", "curriculum", "bio", "profile")):
        return True

    if "resume" in q_lower or "cv" in q_lower:
        return True

    if any(r in q_lower for r in ROLE_QUERY_TRIGGERS) and any(w in q_lower for w in ("my", "i", "can", "should", "fit", "based on", "profile", "background")):
        return True

    # Check document content markers
    matches = sum(1 for k in ("education", "experience", "projects", "skills", "internship", "b.tech", "bachelor") if k in text_lower)
    return matches >= 2


def parse_resume_content(text: str, filename: str = "") -> Dict[str, Any]:
    """Extract education, skills, projects, experience, and certifications."""
    cleaned = re.sub(r"\r\n", "\n", text).strip()
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

    # Extract name candidate from filename or first few non-header lines
    candidate_name = ""
    fn_clean = re.sub(r"[-_]+", " ", filename).strip()
    fn_clean = re.sub(r"\.(pdf|docx|txt|md)$", "", fn_clean, flags=re.I)
    fn_words = [w for w in fn_clean.split() if w.lower() not in ("resume", "cv", "latest", "updated", "final", "doc", "document")]
    if fn_words:
        candidate_name = " ".join(fn_words).title()
    elif lines:
        for line in lines[:3]:
            if len(line.split()) in (2, 3, 4) and not any(h in line.lower() for h in ("resume", "curriculum", "email", "phone", "http")):
                candidate_name = line.strip().title()
                break

    # Skill catalogs
    catalog = {
        "ai_ml": [
            "python", "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
            "transformers", "hugging face", "huggingface", "llm", "llms", "large language models",
            "rag", "retrieval augmented generation", "prompt engineering", "nlp",
            "natural language processing", "computer vision", "opencv", "langchain",
            "llamaindex", "deep learning", "machine learning", "generative ai", "genai",
            "fine-tuning", "lora", "qlora", "diffusion", "stable diffusion", "spacy", "nltk"
        ],
        "frontend": [
            "react", "react.js", "next.js", "nextjs", "vue", "vue.js", "angular",
            "javascript", "typescript", "html", "html5", "css", "css3", "tailwind",
            "tailwindcss", "bootstrap", "redux", "zustand", "vite", "webpack"
        ],
        "backend": [
            "fastapi", "flask", "django", "node.js", "nodejs", "express", "express.js",
            "rest", "restful api", "rest api", "graphql", "grpc", "c++", "cpp",
            "java", "c#", "golang", "go", "rust", "php", "ruby"
        ],
        "data_cloud": [
            "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
            "pandas", "numpy", "matplotlib", "seaborn", "tableau", "power bi",
            "docker", "kubernetes", "aws", "gcp", "google cloud", "azure", "git",
            "github", "linux", "ci/cd", "vercel", "supabase"
        ]
    }

    text_lower = cleaned.lower()
    detected_skills: Dict[str, List[str]] = {category: [] for category in catalog}

    for cat, terms in catalog.items():
        for term in terms:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text_lower):
                detected_skills[cat].append(term.title() if len(term) > 3 else term.upper())

    # Extract education mentions
    education = []
    edu_patterns = [
        r"(?:b\.?tech|bachelor|b\.?e\.?|b\.?s\.?|master|m\.?tech|m\.?s\.?|ph\.?d)[^\n,.]*",
        r"(?:computer science|information technology|artificial intelligence|data science|electronics)[^\n,.]*",
        r"(?:cgpa|gpa)[\s:]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)",
    ]
    for pat in edu_patterns:
        for match in re.finditer(pat, text_lower):
            matched_str = match.group(0).strip()
            if matched_str and matched_str not in education:
                education.append(matched_str.title())

    # Extract projects
    projects = []
    proj_header_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"^(?:academic\s+)?projects?\b", line.lower()):
            proj_header_idx = i
            break
    if proj_header_idx >= 0:
        for line in lines[proj_header_idx + 1: proj_header_idx + 15]:
            if re.search(r"^(?:experience|education|skills|certifications|extracurricular)\b", line.lower()):
                break
            if len(line) > 10 and not line.startswith("http"):
                projects.append(line)

    # Extract experience / internships
    experience = []
    exp_header_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"^(?:work\s+)?experience|internships?\b", line.lower()):
            exp_header_idx = i
            break
    if exp_header_idx >= 0:
        for line in lines[exp_header_idx + 1: exp_header_idx + 15]:
            if re.search(r"^(?:projects|education|skills|certifications|extracurricular)\b", line.lower()):
                break
            if len(line) > 10 and not line.startswith("http"):
                experience.append(line)

    # Extract certifications
    certifications = []
    for line in lines:
        if any(c in line.lower() for c in ("certified", "certification", "anthropic", "deeplearning.ai", "coursera", "aws certified", "google cloud", "hackathon")):
            if len(line) < 120 and line not in certifications:
                certifications.append(line)

    return {
        "candidate_name": candidate_name or "Candidate",
        "filename": filename,
        "raw_text": cleaned,
        "skills": detected_skills,
        "education": education[:4],
        "projects": projects[:5],
        "experience": experience[:5],
        "certifications": certifications[:4]
    }


def match_roles_for_resume(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Match candidate to concrete, realistic roles based strictly on demonstrated skills."""
    skills = parsed.get("skills", {})
    ai_skills = skills.get("ai_ml", [])
    fe_skills = skills.get("frontend", [])
    be_skills = skills.get("backend", [])
    dc_skills = skills.get("data_cloud", [])

    matched_roles: List[Dict[str, Any]] = []

    # 1. Generative AI / LLM Role
    genai_indicators = [s for s in ai_skills if s.lower() in ("llm", "llms", "rag", "prompt engineering", "generative ai", "genai", "transformers", "langchain")]
    if genai_indicators or ("Python" in ai_skills and "PyTorch" in ai_skills):
        reasons = []
        if genai_indicators:
            reasons.append(f"Hands-on experience with {', '.join(genai_indicators[:3])}")
        if "Python" in ai_skills:
            reasons.append("strong Python implementation foundation")
        matched_roles.append({
            "title": "Generative AI Intern / Junior GenAI Engineer",
            "why": f"Your background highlights {'; '.join(reasons)}. Companies deploying LLMs and RAG pipelines actively look for candidates with practical experimentation in prompt workflows and retrieval systems.",
            "strength": 0.95
        })

    # 2. AI / ML Intern Role
    if ai_skills or ("Python" in dc_skills and any(s in dc_skills for s in ("Pandas", "Numpy", "Scikit-Learn"))):
        reasons = [f"knowledge of {', '.join(ai_skills[:3]) if ai_skills else 'Python & data science libraries'}"]
        if "PyTorch" in ai_skills or "Tensorflow" in ai_skills:
            reasons.append("deep learning framework exposure")
        matched_roles.append({
            "title": "AI/ML Intern / Machine Learning Engineer Intern",
            "why": f"Supported by your {', '.join(reasons)}. Fits research teams and ML labs seeking candidates capable of prototyping models, processing datasets, and running structured experiments.",
            "strength": 0.90
        })

    # 3. Prompt Engineering / AI Applications
    if any(s.lower() in ("prompt engineering", "llm", "rag", "langchain") for s in ai_skills) or parsed.get("certifications"):
        certs = parsed.get("certifications", [])
        cert_mention = f" and certifications ({certs[0]})" if certs else ""
        matched_roles.append({
            "title": "Prompt Engineering Intern / AI Application Specialist",
            "why": f"Your skills in prompt design, LLM interaction{cert_mention} demonstrate practical capability to craft high-performing prompts, build evaluation loops, and integrate AI features into products.",
            "strength": 0.88
        })

    # 4. Frontend / Full-stack Junior Role
    if fe_skills:
        reasons = [f"UI development experience with {', '.join(fe_skills[:3])}"]
        if "Fastapi" in be_skills or "Node.Js" in be_skills:
            reasons.append(f"full-stack bridging with {be_skills[0]}")
        matched_roles.append({
            "title": "Junior Frontend Developer / React Intern",
            "why": f"Backed by your {', '.join(reasons)}. Positions you well for product engineering teams building modern web applications and AI client interfaces.",
            "strength": 0.85
        })

    # 5. Backend / Python Developer
    if be_skills or ("Python" in ai_skills and any(s in be_skills for s in ("Fastapi", "Flask", "Django"))):
        reasons = [f"experience with {', '.join(be_skills[:2]) if be_skills else 'Python API development'}"]
        if dc_skills:
            reasons.append(f"database/tooling knowledge ({dc_skills[0]})")
        matched_roles.append({
            "title": "Junior Backend Developer / Python Intern",
            "why": f"Supported by your {', '.join(reasons)}. Matches teams building high-throughput APIs, data pipelines, and service integrations.",
            "strength": 0.82
        })

    # 6. Data Analyst / Data Science Intern
    if any(s in dc_skills for s in ("Pandas", "Numpy", "Postgresql", "Sqlite", "Mysql")):
        matched_roles.append({
            "title": "Data Analyst Intern / Junior Data Scientist",
            "why": f"Demonstrated data handling with {', '.join([s for s in dc_skills if s in ('Pandas', 'Numpy', 'Postgresql', 'Sqlite')][:3])}. Fits organizations that extract business and product insights from large datasets.",
            "strength": 0.80
        })

    # Fallback to software engineering intern if few specific technologies were extracted
    if not matched_roles:
        matched_roles.append({
            "title": "Software Development Intern",
            "why": "Your academic coursework and foundational technical skills provide a solid base for junior software engineering and developer internship programs.",
            "strength": 0.75
        })

    # Sort by strength and return top 3-4
    matched_roles.sort(key=lambda r: r["strength"], reverse=True)
    return matched_roles[:4]


def identify_skill_gaps(parsed: Dict[str, Any]) -> List[str]:
    """Provide realistic, constructive suggestions for skills to improve."""
    skills = parsed.get("skills", {})
    all_skills_lower = {s.lower() for cat in skills.values() for s in cat}
    gaps = []

    if "docker" not in all_skills_lower and "kubernetes" not in all_skills_lower:
        gaps.append("Containerization (Docker): Package your AI models and APIs into containers to show production-readiness.")

    if not any(c in all_skills_lower for c in ("aws", "gcp", "azure")):
        gaps.append("Cloud Deployment (AWS / GCP): Deploy a live service with an active endpoint to demonstrate infrastructure know-how.")

    if "ci/cd" not in all_skills_lower:
        gaps.append("Automated Testing & CI/CD: Include GitHub Actions or pytest suites in your projects to show professional software discipline.")

    if not any(k in all_skills_lower for k in ("rag", "llamaindex", "langchain")):
        gaps.append("Vector Databases & Advanced RAG: Build a project using pgvector, Chroma, or Pinecone with semantic hybrid retrieval.")

    # Always ensure 2-3 genuine gaps
    if len(gaps) < 2:
        gaps.append("Production Monitoring: Add logging, tracing, or latency benchmarking to your AI application repositories.")

    return gaps[:3]


def generate_resume_advice_markdown(
    parsed: Dict[str, Any],
    query: str = "",
    source_filename: str = ""
) -> str:
    """Generate clean, natural markdown advice matching Section 5 format."""
    roles = match_roles_for_resume(parsed)
    gaps = identify_skill_gaps(parsed)
    candidate_name = parsed.get("candidate_name") or "you"
    wants_links = any(w in query.lower() for w in ("link", "links", "url", "where to apply", "opportunities", "platforms"))

    lines = [
        "### 🎯 Roles that match your resume",
        ""
    ]

    for i, role in enumerate(roles, 1):
        lines.append(f"**{i}. {role['title']}**")
        lines.append(f"Why it fits: {role['why']}")
        lines.append("")

    best_role = roles[0]
    lines.append("### ⭐ Best option to target first")
    lines.append(f"**{best_role['title']}** is your strongest entry point right now. Your demonstrated skills directly align with the core day-to-day requirements of this role, giving you an immediate competitive advantage in screening interviews.")
    lines.append("")

    lines.append("### 📈 Skills to improve")
    for gap in gaps:
        lines.append(f"- **{gap.split(':')[0]}**: {gap.split(':', 1)[1].strip() if ':' in gap else gap}")
    lines.append("")

    if wants_links or any(w in query.lower() for w in ("apply", "jobs", "roles", "find")):
        lines.append("### 🔗 Useful opportunities")
        lines.append("- [LinkedIn Jobs — AI & ML Internships](https://www.linkedin.com/jobs/search/?keywords=AI+Intern+OR+Machine+Learning+Intern): Active listings for student and graduate engineering roles.")
        lines.append("- [Wellfound (AngelList Talent)](https://wellfound.com/jobs): Premier platform for fast-growing AI startups looking for GenAI and backend interns.")
        lines.append("- [Y Combinator Work at a Startup](https://www.workatastartup.com/): Direct hiring pipeline for seed and Series-A AI companies.")
        lines.append("")

    return "\n".join(lines).strip()
