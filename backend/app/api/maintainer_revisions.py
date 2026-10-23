from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.maintainer_auth import MaintainerSession
from app.maintainer_auth import require_maintainer
from app.repositories.revision_review import RevisionNotFound
from app.repositories.revision_review import RevisionNotPending
from app.repositories.revision_review import approve_pending_revision
from app.repositories.revision_review import field_diffs
from app.repositories.revision_review import get_revision_record
from app.repositories.revision_review import list_pending_revisions
from app.repositories.revision_review import RevisionReviewError
from app.repositories.revision_review import propose_revert_revision
from app.repositories.revision_review import reject_pending_revision

router = APIRouter(prefix="/maintainer/revisions", tags=["maintainer"])


class PendingRevisionItem(BaseModel):
    revision_id: uuid.UUID
    route_id: uuid.UUID
    route_name: str
    revision_number: int
    created_at: str
    author_kind: str
    changed_keys: list[str]


class FieldDiffItem(BaseModel):
    field: str
    before: object | None
    after: object | None


class RevertRequest(BaseModel):
    target_revision_number: int | None = None


class RevertResponse(BaseModel):
    revision_id: uuid.UUID
    revision_number: int
    application_status: str


class RevisionDetailResponse(BaseModel):
    revision_id: uuid.UUID
    route_id: uuid.UUID
    application_status: str
    revision_number: int
    created_at: str
    author_kind: str
    field_diffs: list[FieldDiffItem]


@router.get("/pending", response_model=list[PendingRevisionItem])
def get_pending_revisions(
    session: Session = Depends(get_db_session),
    _maintainer: MaintainerSession = Depends(require_maintainer),
) -> list[PendingRevisionItem]:
    return [
        PendingRevisionItem(
            revision_id=item.revision_id,
            route_id=item.route_id,
            route_name=item.route_name,
            revision_number=item.revision_number,
            created_at=item.created_at.isoformat(),
            author_kind=item.author_kind,
            changed_keys=item.changed_keys,
        )
        for item in list_pending_revisions(session)
    ]


@router.get("/{revision_id}", response_model=RevisionDetailResponse)
def get_revision_detail(
    revision_id: uuid.UUID,
    session: Session = Depends(get_db_session),
    _maintainer: MaintainerSession = Depends(require_maintainer),
) -> RevisionDetailResponse:
    try:
        revision = get_revision_record(session, revision_id)
    except RevisionNotFound as exc:
        raise HTTPException(status_code=404, detail="Revision not found") from exc
    diffs = field_diffs(revision.before_snapshot, revision.after_snapshot)
    return RevisionDetailResponse(
        revision_id=revision.id,
        route_id=revision.route_id,
        application_status=revision.application_status,
        revision_number=revision.revision_number,
        created_at=revision.created_at.isoformat(),
        author_kind=revision.author_kind,
        field_diffs=[
            FieldDiffItem(field=diff.field, before=diff.before, after=diff.after)
            for diff in diffs
        ],
    )


@router.post("/{revision_id}/approve", status_code=204)
def approve_revision(
    revision_id: uuid.UUID,
    session: Session = Depends(get_db_session),
    maintainer: MaintainerSession = Depends(require_maintainer),
) -> None:
    try:
        approve_pending_revision(
            session,
            revision_id,
            maintainer_username=maintainer.username,
        )
    except RevisionNotFound as exc:
        raise HTTPException(status_code=404, detail="Revision not found") from exc
    except RevisionNotPending as exc:
        raise HTTPException(status_code=409, detail="Revision is not pending") from exc
    session.commit()


@router.post("/{revision_id}/revert", response_model=RevertResponse, status_code=201)
def revert_revision(
    revision_id: uuid.UUID,
    body: RevertRequest,
    session: Session = Depends(get_db_session),
    maintainer: MaintainerSession = Depends(require_maintainer),
) -> RevertResponse:
    try:
        anchor = get_revision_record(session, revision_id)
    except RevisionNotFound as exc:
        raise HTTPException(status_code=404, detail="Revision not found") from exc
    try:
        new_revision_id, revision_number = propose_revert_revision(
            session,
            anchor.route_id,
            target_revision_number=body.target_revision_number,
            maintainer_username=maintainer.username,
        )
    except RevisionNotFound as exc:
        raise HTTPException(status_code=404, detail="Revision not found") from exc
    except RevisionReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    return RevertResponse(
        revision_id=new_revision_id,
        revision_number=revision_number,
        application_status="pending",
    )


@router.post("/{revision_id}/reject", status_code=204)
def reject_revision(
    revision_id: uuid.UUID,
    session: Session = Depends(get_db_session),
    _maintainer: MaintainerSession = Depends(require_maintainer),
) -> None:
    try:
        reject_pending_revision(session, revision_id)
    except RevisionNotFound as exc:
        raise HTTPException(status_code=404, detail="Revision not found") from exc
    except RevisionNotPending as exc:
        raise HTTPException(status_code=409, detail="Revision is not pending") from exc
    session.commit()
