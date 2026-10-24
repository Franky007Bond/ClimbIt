from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    HttpUrl,
    TypeAdapter,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from app.domain.route import Route

_HTTP_URL = TypeAdapter(HttpUrl)

PlanningInput = Literal["unknown", "none_known", "active"]
EffectiveStatus = Literal["none_known", "active", "expired"]


class ClosureStatus(StrEnum):
    NONE_KNOWN = "none_known"
    ACTIVE = "active"


class ClosureReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("datetime must be timezone-aware with offset +00:00")
    return value


class ClosureAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ClosureStatus
    source_url: str
    owner: str
    review_status: ClosureReviewStatus
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    expires_at: datetime

    @field_validator("source_url")
    @classmethod
    def source_url_must_be_http(cls, value: str) -> str:
        _HTTP_URL.validate_python(value)
        return value

    @field_validator("owner")
    @classmethod
    def owner_non_empty_after_strip(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("owner must be non-empty after strip")
        return value

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_be_utc_when_set(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return value
        return _require_aware_utc(value)

    @model_validator(mode="after")
    def check_record_clock_invariants(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be before created_at")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if self.review_status is ClosureReviewStatus.REVIEWED:
            if self.reviewed_at is None:
                raise ValueError(
                    "reviewed_at is required when review_status is reviewed"
                )
            if self.reviewed_at < self.created_at:
                raise ValueError("reviewed_at must not be before created_at")
            if self.reviewed_at > self.updated_at:
                raise ValueError("reviewed_at must not be after updated_at")
            if self.expires_at <= self.reviewed_at:
                raise ValueError("expires_at must be after reviewed_at")
        elif self.reviewed_at is not None:
            raise ValueError(
                "reviewed_at must be None when review_status is unreviewed"
            )
        return self


def effective_closure_status(
    assessment: ClosureAssessment, now: datetime
) -> EffectiveStatus:
    _require_aware_utc(now)
    if now >= assessment.expires_at:
        return "expired"
    return assessment.status


def closure_planning_input(route: "Route", now: datetime) -> PlanningInput:
    _require_aware_utc(now)
    assessment = route.closure_assessment
    if assessment is None:
        return "unknown"
    if assessment.review_status is not ClosureReviewStatus.REVIEWED:
        return "unknown"
    if effective_closure_status(assessment, now) == "expired":
        return "unknown"
    return assessment.status
