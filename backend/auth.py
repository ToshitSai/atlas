"""Server-side Clerk authentication helpers.

Only a verified Clerk session token may establish an application identity.  The
browser never supplies a trusted user id; all ownership is derived from ``sub``.
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request
from clerk_backend_api import AuthenticateRequestOptions, authenticate_request


def _authorized_parties() -> list[str]:
    configured = os.environ.get("CLERK_AUTHORIZED_PARTIES", "")
    values = configured.split(",") if configured else [
        "https://atlas-scientist.vercel.app",
        "https://automl-scientist.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    return [value.strip().rstrip("/") for value in values if value.strip()]


def verified_clerk_user_id(request: Request) -> str:
    """Verify the bearer session token and return its Clerk ``sub`` claim."""
    secret = os.environ.get("CLERK_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=503, detail="Authentication service is not configured.")
    try:
        state = authenticate_request(
            request,
            AuthenticateRequestOptions(secret_key=secret, authorized_parties=_authorized_parties()),
        )
    except Exception as exc:
        print(f"[AUTH VERIFY ERROR] {type(exc).__name__}")
        raise HTTPException(status_code=401, detail="Your sign-in session could not be verified.") from None

    subject = (state.payload or {}).get("sub") if state.is_authenticated else None
    if not isinstance(subject, str) or not subject.startswith("user_"):
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return subject
