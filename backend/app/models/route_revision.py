from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.models.route import Base


class RouteRevisionRecord(Base):
    __tablename__ = "route_revisions"
    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "revision_number",
            name="uq_route_revisions_route_id_revision_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    author_kind: Mapped[str] = mapped_column(Text, nullable=False)
    author_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    application_status: Mapped[str] = mapped_column(Text, nullable=False)


_APPEND_ONLY_ERROR = "route revision rows are append-only"


@event.listens_for(RouteRevisionRecord, "before_update")
def _reject_route_revision_update(_mapper, _connection, _target) -> None:
    raise RuntimeError(_APPEND_ONLY_ERROR)


@event.listens_for(RouteRevisionRecord, "before_delete")
def _reject_route_revision_delete(_mapper, _connection, _target) -> None:
    raise RuntimeError(_APPEND_ONLY_ERROR)
