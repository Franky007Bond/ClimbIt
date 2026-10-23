from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Text
from sqlalchemy import Uuid
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.models.route import Base

_APPEND_ONLY_ERROR = "plan run rows are append-only"


class PlanRunRecord(Base):
    __tablename__ = "plan_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_timestamps: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rules_version: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_version: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[list] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)


@event.listens_for(PlanRunRecord, "before_update")
def _reject_plan_run_update(_mapper, _connection, _target) -> None:
    raise RuntimeError(_APPEND_ONLY_ERROR)


@event.listens_for(PlanRunRecord, "before_delete")
def _reject_plan_run_delete(_mapper, _connection, _target) -> None:
    raise RuntimeError(_APPEND_ONLY_ERROR)
