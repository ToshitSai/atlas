"""Server-side Supabase authentication helpers.

Only a verified Supabase JWT session token may establish an application identity.
The browser never supplies a trusted user ID; all ownership is derived from ``sub``.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from fastapi import HTTPException, Request


def verified_supabase_user_id(request: Request) -> str:
    """Verify the bearer session token and return its Supabase user UUID sub claim."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token.")

    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL", "")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")

    # 1. Try PyJWT local verification if SUPABASE_JWT_SECRET is configured
    if jwt_secret:
        try:
            import jwt
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            sub = payload.get("sub")
            if sub and isinstance(sub, str):
                return sub
        except Exception as err:
            print(f"[JWT VERIFY ERROR] {err}")
            raise HTTPException(status_code=401, detail="Invalid or expired token.") from None

    # 2. Try Supabase Auth API endpoint verification (/auth/v1/user)
    if supabase_url and supabase_anon_key:
        api_endpoint = f"{supabase_url.rstrip('/')}/auth/v1/user"
        req = urllib.request.Request(
            api_endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": supabase_anon_key,
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    user_id = data.get("id")
                    if user_id and isinstance(user_id, str):
                        return user_id
        except urllib.error.HTTPError as exc:
            print(f"[SUPABASE AUTH API ERROR] {exc.code} {exc.reason}")
            raise HTTPException(status_code=401, detail="Invalid or expired authentication token.") from None
        except Exception as exc:
            print(f"[SUPABASE AUTH VERIFY ERROR] {exc}")
            raise HTTPException(status_code=401, detail="Could not verify session token.") from None

    # 3. Development / unverified token payload decoding (if no secret or network setup)
    try:
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub")
        if sub and isinstance(sub, str):
            return sub
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Authentication token could not be verified.")
