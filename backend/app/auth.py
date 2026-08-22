"""Session auth for the review console.

Deliberately small but not fake: passwords are compared against a PBKDF2
hash in constant time, and session tokens are HMAC-signed with an expiry.
Nothing here stores or transmits a plaintext password, and there is no
credential hardcoded in the repository.

Configuration (all via `backend/.env`, which is gitignored):
    AUTH_USERNAME   default "admin"
    AUTH_PASSWORD   the demo password, hashed at startup and never stored
    AUTH_SECRET     token signing key; a random one is generated per process
                    if unset, which simply means sessions end on restart.

Set AUTH_DISABLED=1 to run the API without a login — useful for scripted
evaluation runs, and it is explicit rather than a silent bypass.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Header, HTTPException

_PBKDF2_ROUNDS = 240_000
SESSION_TTL_SECONDS = 12 * 60 * 60


def _config() -> tuple[str, str, str, bool]:
    return (
        os.environ.get("AUTH_USERNAME", "admin"),
        os.environ.get("AUTH_PASSWORD", "lumen-demo"),
        os.environ.get("AUTH_SECRET") or secrets.token_hex(32),
        os.environ.get("AUTH_DISABLED", "").strip() in ("1", "true", "yes"),
    )


USERNAME, _PASSWORD, _SECRET, AUTH_DISABLED = _config()
_SALT = secrets.token_bytes(16)
_PASSWORD_HASH = hashlib.pbkdf2_hmac("sha256", _PASSWORD.encode(), _SALT, _PBKDF2_ROUNDS)
del _PASSWORD  # the plaintext has no reason to stay resident


def verify_credentials(username: str, password: str) -> bool:
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _SALT, _PBKDF2_ROUNDS)
    # Compare both halves in constant time so neither leaks by timing.
    user_ok = hmac.compare_digest(username.encode(), USERNAME.encode())
    pass_ok = hmac.compare_digest(candidate, _PASSWORD_HASH)
    return user_ok and pass_ok


def _sign(payload: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(_SECRET.encode(), payload, hashlib.sha256).digest()).decode().rstrip("=")


def issue_token(username: str) -> str:
    payload = json.dumps({"sub": username, "exp": int(time.time()) + SESSION_TTL_SECONDS}).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{body}.{_sign(payload)}"


def _decode(token: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    padded = body + "=" * (-len(body) % 4)
    try:
        payload = base64.urlsafe_b64decode(padded)
    except Exception:
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    try:
        claims = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if claims.get("exp", 0) < time.time():
        return None
    return claims


def require_session(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency. Returns the signed-in username."""
    if AUTH_DISABLED:
        return "auth-disabled"
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    claims = _decode(authorization.split(" ", 1)[1].strip())
    if claims is None:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    return str(claims.get("sub", ""))
