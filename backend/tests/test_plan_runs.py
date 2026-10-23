import os

import pytest

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.domain.plan_run import PlanRun
from app.models.plan_run import PlanRunRecord
from app.repositories.plan_runs import create_plan_run
from app.repositories.plan_runs import get_plan_run
from app.repositories.plan_runs import new_plan_run_id
from app.repositories.plan_runs import plan_run_created_at
from app.seed import seed
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def test_stored_plan_run_round_trips_result(migrated_test_database: str) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    run_id = new_plan_run_id()
    created_at = plan_run_created_at()
    result_snapshot = {
        "recommendation": "yellow",
        "confidence": "medium",
        "weather_status": "ok",
    }
    run = PlanRun(
        id=run_id,
        route_id=route_id,
        created_at=created_at,
        input_snapshot={"plan_date": "2026-07-15", "route_id": str(route_id)},
        source_timestamps={"weather": created_at, "closure": None},
        rules_version="plan-rules-2026.10.1",
        mapping_version="difficulty-map-2026.10.1",
        adapter_versions={"weather": "mock-1", "transit": "mock-1"},
        explanation=["Sample explanation line."],
        result=result_snapshot,
    )
    SessionLocal = create_sessionmaker(_operator_url(migrated_test_database))
    with SessionLocal() as session:
        seed(session)
        create_plan_run(session, run)
        session.commit()
        loaded = get_plan_run(session, run_id)
    assert loaded is not None
    assert loaded.result == result_snapshot
    assert loaded.input_snapshot == run.input_snapshot
    assert loaded.rules_version == run.rules_version
    assert loaded.mapping_version == run.mapping_version
    assert loaded.adapter_versions == run.adapter_versions
    assert loaded.explanation == run.explanation
    assert loaded.source_timestamps["weather"] == created_at
    assert loaded.source_timestamps["closure"] is None


def test_plan_run_rows_are_append_only(migrated_test_database: str) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    run = PlanRun(
        id=new_plan_run_id(),
        route_id=route_id,
        created_at=plan_run_created_at(),
        input_snapshot={},
        source_timestamps={},
        rules_version="plan-rules-2026.10.1",
        mapping_version="difficulty-map-2026.10.1",
        adapter_versions={},
        explanation=[],
        result={"recommendation": "unknown"},
    )
    SessionLocal = create_sessionmaker(_operator_url(migrated_test_database))
    with SessionLocal() as session:
        seed(session)
        create_plan_run(session, run)
        session.commit()
        record = session.get(PlanRunRecord, run.id)
        with pytest.raises(RuntimeError, match="append-only"):
            record.result = {"recommendation": "green"}
            session.commit()
