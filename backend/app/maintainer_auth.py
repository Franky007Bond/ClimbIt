from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

import bcrypt
from fastapi import HTTPException, Request, Response

MAINTAINER_COOKIE_NAME = "climbit_maintainer_session"
_SESSION_TTL_SECONDS = 60 * 60 * 12


@dataclass(frozen=True, slots=True)
class MaintainerSession:
    username: str


def _session_secret() -> str:
    secret = os.environ.get("MAINTAINER_SESSION_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail={"reason": "maintainer_session_unconfigured"},
        )
    return secret


def load_allowlist() -> dict[str, str]:
    raw = os.environ.get("MAINTAINER_ALLOWLIST", "[]")
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"reason": "maintainer_allowlist_invalid"},
        ) from exc
    if not isinstance(entries, list):
        raise HTTPException(
            status_code=503,
            detail={"reason": "maintainer_allowlist_invalid"},
        )
    allowlist: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        username = entry.get("username")
        password_hash = entry.get("password_bcrypt")
        if isinstance(username, str) and isinstance(password_hash, str):
            allowlist[username] = password_hash
    return allowlist


def verify_password(username: str, password: str) -> bool:
    allowlist = load_allowlist()
    stored_hash = allowlist.get(username)
    if stored_hash is None:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def _sign_payload(payload: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{digest}"


def _parse_signed_token(token: str, secret: str) -> MaintainerSession | None:
    if "." not in token:
        return None
    payload, digest = token.rsplit(".", 1)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    username, expires_at_raw = payload.split(":", 1)
    try:
        expires_at = int(expires_at_raw)
    except ValueError:
        return None
    if expires_at < int(time.time()):
        return None
    if not username:
        return None
    return MaintainerSession(username=username)


def create_session_token(username: str) -> str:
    secret = _session_secret()
    expires_at = int(time.time()) + _SESSION_TTL_SECONDS
    payload = f"{username}:{expires_at}"
    return _sign_payload(payload, secret)


def read_maintainer_session(request: Request) -> MaintainerSession | None:
    token = request.cookies.get(MAINTAINER_COOKIE_NAME)
    if not token:
        return None
    secret = os.environ.get("MAINTAINER_SESSION_SECRET", "").strip()
    if not secret:
        return None
    return _parse_signed_token(token, secret)


def set_maintainer_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=MAINTAINER_COOKIE_NAME,
        value=token,
        httponly=True,
        path="/",
        samesite="lax",
        secure=request.url.scheme == "https",
    )


def clear_maintainer_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=MAINTAINER_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


def require_maintainer(request: Request) -> MaintainerSession:
    session = read_maintainer_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Maintainer authentication required")
    return session
