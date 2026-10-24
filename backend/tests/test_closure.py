import inspect
from datetime import datetime, timedelta, timezone
from enum import Enum

import pytest
from pydantic import ValidationError

from app.domain.closure import (
    ClosureAssessment,
    ClosureReviewStatus,
    ClosureStatus,
    closure_planning_input,
    effective_closure_status,
)
from app.domain.route import (
    Assessment,
    Completeness,
    Provenance,
    Publication,
    Region,
    RegionCoverage,
    Route,
    RouteType,
    TransitAccessibility,
)


UTC = timezone.utc
CREATED = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
UPDATED = datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)
REVIEWED = datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)
EXPIRES = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
JUST_BEFORE = datetime(2026, 7, 15, 11, 59, 59, tzinfo=UTC)
AT_EXPIRY = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
JUST_AFTER = datetime(2026, 7, 15, 12, 0, 1, tzinfo=UTC)
DAY_BEFORE = datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC)
DAY_AFTER = datetime(2026, 7, 16, 0, 0, 0, tzinfo=UTC)
NAIVE = datetime(2026, 7, 15, 12, 0, 0)
BERLIN_OFFSET = timezone(timedelta(hours=2))


def _assessment(**overrides) -> ClosureAssessment:
    payload = {
        "status": ClosureStatus.ACTIVE,
        "source_url": "https://example.invalid/closure-notice",
        "owner": "maintainer",
        "review_status": ClosureReviewStatus.REVIEWED,
        "created_at": CREATED,
        "updated_at": UPDATED,
        "reviewed_at": REVIEWED,
        "expires_at": EXPIRES,
    }
    payload.update(overrides)
    return ClosureAssessment(**payload)


def _route(**overrides) -> Route:
    payload = {
        "name": "Hindelanger Klettersteig",
        "route_type": RouteType.ALPINE_HIKE,
        "region": Region(
            name="Allgäu", country="DE", coverage=RegionCoverage.SUPPORTED
        ),
        "publication": Publication.QUARANTINED,
        "duration_is_estimated": True,
        "season_months": set(),
        "description": "",
        "transit_accessibility": TransitAccessibility.UNKNOWN,
        "official_source_links": [],
        "provenance": Provenance.SEED,
        "completeness": Completeness.INCOMPLETE,
        "assessment": Assessment.UNASSESSED,
    }
    payload.update(overrides)
    return Route(**payload)


@pytest.mark.parametrize(
    "enum_cls, value",
    [
        (ClosureStatus, "none_known"),
        (ClosureStatus, "active"),
        (ClosureReviewStatus, "unreviewed"),
        (ClosureReviewStatus, "reviewed"),
    ],
)
def test_stored_enum_values_are_exact_strings(enum_cls: type[Enum], value: str) -> None:
    assert enum_cls(value).value == value


@pytest.mark.parametrize(
    "bad",
    ["expired", "open", "unknown"],
)
def test_closure_status_rejects_derived_and_alias_strings(bad: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        ClosureStatus(bad)


@pytest.mark.parametrize("bad", ["pending", "current", "stale"])
def test_closure_review_status_rejects_other_strings(bad: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        ClosureReviewStatus(bad)


def test_closure_enums_are_not_route_enums() -> None:
    assert ClosureStatus.__name__ == "ClosureStatus"
    assert ClosureReviewStatus.__name__ == "ClosureReviewStatus"
    assert ClosureStatus is not Publication
    assert ClosureStatus is not Assessment
    assert ClosureStatus is not Completeness
    assert ClosureReviewStatus is not Assessment
    assert {member.value for member in ClosureStatus} == {"none_known", "active"}
    assert {member.value for member in ClosureReviewStatus} == {
        "unreviewed",
        "reviewed",
    }


def test_assessment_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _assessment(ttl_hours=24)


def test_source_url_is_stored_string_without_fetch() -> None:
    url = "https://example.invalid/closure-notice"
    assessment = _assessment(source_url=url)
    assert assessment.source_url == url
    with pytest.raises(ValidationError):
        _assessment(source_url="ftp://example.invalid/x")
    with pytest.raises(ValidationError):
        _assessment(source_url="not-a-url")


def test_owner_rejects_empty_or_whitespace() -> None:
    with pytest.raises(ValidationError):
        _assessment(owner="")
    with pytest.raises(ValidationError):
        _assessment(owner="   ")


@pytest.mark.parametrize(
    "field", ["created_at", "updated_at", "expires_at", "reviewed_at"]
)
def test_naive_datetime_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        _assessment(**{field: NAIVE})


@pytest.mark.parametrize(
    "field", ["created_at", "updated_at", "expires_at", "reviewed_at"]
)
def test_non_utc_offset_is_rejected(field: str) -> None:
    shifted = datetime(2026, 7, 15, 12, 0, 0, tzinfo=BERLIN_OFFSET)
    with pytest.raises(ValidationError):
        _assessment(**{field: shifted})


def test_past_reviewed_at_constructs() -> None:
    past = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
    assessment = _assessment(
        created_at=past,
        updated_at=past,
        reviewed_at=past,
        expires_at=EXPIRES,
    )
    assert assessment.reviewed_at == past


def test_updated_at_before_created_at_invalid() -> None:
    with pytest.raises(ValidationError):
        _assessment(updated_at=datetime(2026, 6, 30, 0, 0, 0, tzinfo=UTC))


def test_expires_at_not_after_created_at_invalid() -> None:
    with pytest.raises(ValidationError):
        _assessment(expires_at=CREATED)
    with pytest.raises(ValidationError):
        _assessment(expires_at=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC))


def test_reviewed_requires_reviewed_at_within_clocks() -> None:
    with pytest.raises(ValidationError):
        _assessment(review_status=ClosureReviewStatus.REVIEWED, reviewed_at=None)
    with pytest.raises(ValidationError):
        _assessment(reviewed_at=datetime(2026, 6, 30, 0, 0, 0, tzinfo=UTC))
    with pytest.raises(ValidationError):
        _assessment(reviewed_at=datetime(2026, 7, 11, 0, 0, 0, tzinfo=UTC))
    with pytest.raises(ValidationError):
        _assessment(expires_at=REVIEWED)


def test_unreviewed_requires_reviewed_at_none() -> None:
    assessment = _assessment(
        review_status=ClosureReviewStatus.UNREVIEWED,
        reviewed_at=None,
    )
    assert assessment.reviewed_at is None
    with pytest.raises(ValidationError):
        _assessment(
            review_status=ClosureReviewStatus.UNREVIEWED,
            reviewed_at=REVIEWED,
        )


def test_construction_does_not_read_system_clock() -> None:
    import app.domain.closure as closure_mod

    source = inspect.getsource(closure_mod)
    assert "datetime.now" not in source
    _assessment()
    effective_closure_status(_assessment(), now=JUST_BEFORE)
    closure_planning_input(_route(), now=JUST_BEFORE)


def test_effective_status_does_not_mutate_stored_status() -> None:
    assessment = _assessment(status=ClosureStatus.ACTIVE)
    assert effective_closure_status(assessment, now=AT_EXPIRY) == "expired"
    assert assessment.status is ClosureStatus.ACTIVE
    assert assessment.status != "expired"


@pytest.mark.parametrize(
    "stored, now, expected",
    [
        (ClosureStatus.ACTIVE, JUST_BEFORE, "active"),
        (ClosureStatus.ACTIVE, AT_EXPIRY, "expired"),
        (ClosureStatus.ACTIVE, JUST_AFTER, "expired"),
        (ClosureStatus.NONE_KNOWN, JUST_BEFORE, "none_known"),
        (ClosureStatus.NONE_KNOWN, AT_EXPIRY, "expired"),
        (ClosureStatus.NONE_KNOWN, JUST_AFTER, "expired"),
        (ClosureStatus.ACTIVE, DAY_BEFORE, "active"),
        (ClosureStatus.ACTIVE, DAY_AFTER, "expired"),
        (ClosureStatus.NONE_KNOWN, DAY_BEFORE, "none_known"),
        (ClosureStatus.NONE_KNOWN, DAY_AFTER, "expired"),
    ],
)
def test_effective_closure_status_expiry_boundaries(
    stored: ClosureStatus, now: datetime, expected: str
) -> None:
    assessment = _assessment(status=stored, expires_at=EXPIRES)
    assert effective_closure_status(assessment, now=now) == expected


def test_effective_closure_status_rejects_naive_now() -> None:
    with pytest.raises((ValidationError, ValueError)):
        effective_closure_status(_assessment(), now=NAIVE)


def test_absence_is_not_none_known() -> None:
    missing = _route()
    reviewed_none_known = _route(
        closure_assessment=_assessment(status=ClosureStatus.NONE_KNOWN)
    )
    assert missing.closure_assessment is None
    assert reviewed_none_known.closure_assessment is not None
    assert missing.closure_assessment != reviewed_none_known.closure_assessment
    assert closure_planning_input(missing, now=JUST_BEFORE) == "unknown"
    assert closure_planning_input(reviewed_none_known, now=JUST_BEFORE) == "none_known"
    dumped = missing.model_dump()
    assert dumped["closure_assessment"] is None


@pytest.mark.parametrize(
    "assessment, now, expected",
    [
        (None, JUST_BEFORE, "unknown"),
        (
            dict(
                status=ClosureStatus.NONE_KNOWN,
                review_status=ClosureReviewStatus.UNREVIEWED,
                reviewed_at=None,
            ),
            JUST_BEFORE,
            "unknown",
        ),
        (
            dict(
                status=ClosureStatus.ACTIVE,
                review_status=ClosureReviewStatus.UNREVIEWED,
                reviewed_at=None,
            ),
            JUST_BEFORE,
            "unknown",
        ),
        (
            dict(
                status=ClosureStatus.NONE_KNOWN,
                review_status=ClosureReviewStatus.REVIEWED,
            ),
            JUST_BEFORE,
            "none_known",
        ),
        (
            dict(
                status=ClosureStatus.ACTIVE, review_status=ClosureReviewStatus.REVIEWED
            ),
            JUST_BEFORE,
            "active",
        ),
        (
            dict(
                status=ClosureStatus.NONE_KNOWN,
                review_status=ClosureReviewStatus.REVIEWED,
            ),
            AT_EXPIRY,
            "unknown",
        ),
        (
            dict(
                status=ClosureStatus.ACTIVE, review_status=ClosureReviewStatus.REVIEWED
            ),
            AT_EXPIRY,
            "unknown",
        ),
        (
            dict(
                status=ClosureStatus.ACTIVE, review_status=ClosureReviewStatus.REVIEWED
            ),
            JUST_AFTER,
            "unknown",
        ),
    ],
)
def test_planning_input_missing_unreviewed_or_expired_is_unknown(
    assessment: dict | None, now: datetime, expected: str
) -> None:
    nested = None if assessment is None else _assessment(**assessment)
    route = _route(closure_assessment=nested)
    result = closure_planning_input(route, now=now)
    assert result == expected
    assert result not in {"safe", "open", "green", "expired"}


def test_planning_input_does_not_compute_recommendation() -> None:
    result = closure_planning_input(_route(), now=JUST_BEFORE)
    assert result == "unknown"
    assert result not in {"green", "yellow", "red"}
