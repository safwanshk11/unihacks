from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import AUTH_DISABLED, SESSION_TTL_SECONDS, issue_token, require_session, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(credentials: Credentials):
    if not verify_credentials(credentials.username.strip(), credentials.password):
        # One message for both failure modes — saying which half was wrong
        # would let someone enumerate valid usernames.
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    return {
        "token": issue_token(credentials.username.strip()),
        "username": credentials.username.strip(),
        "expires_in": SESSION_TTL_SECONDS,
    }


@router.get("/me")
def me(username: str = Depends(require_session)):
    return {"username": username, "auth_disabled": AUTH_DISABLED}
