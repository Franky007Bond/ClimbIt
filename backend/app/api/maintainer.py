from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.maintainer_auth import clear_maintainer_cookie
from app.maintainer_auth import create_session_token
from app.maintainer_auth import read_maintainer_session
from app.maintainer_auth import set_maintainer_cookie
from app.maintainer_auth import verify_password

router = APIRouter(prefix="/maintainer", tags=["maintainer"])


class MaintainerLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class MaintainerSessionResponse(BaseModel):
    username: str


@router.post("/sessions", response_model=MaintainerSessionResponse)
def create_maintainer_session(
    body: MaintainerLoginRequest,
    request: Request,
    response: Response,
) -> MaintainerSessionResponse:
    if not verify_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_session_token(body.username.strip())
    set_maintainer_cookie(response, request, token)
    return MaintainerSessionResponse(username=body.username.strip())


@router.delete("/sessions", status_code=204)
def delete_maintainer_session(request: Request, response: Response) -> Response:
    if read_maintainer_session(request) is None:
        raise HTTPException(status_code=401, detail="No active maintainer session")
    clear_maintainer_cookie(response, request)
    response.status_code = 204
    return response


@router.get("/session", response_model=MaintainerSessionResponse)
def get_maintainer_session(request: Request) -> MaintainerSessionResponse:
    session = read_maintainer_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Maintainer authentication required")
    return MaintainerSessionResponse(username=session.username)
