from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.closure import PlanningInput
from app.domain.closure import closure_planning_input
from app.domain.route import Route


@dataclass(frozen=True, slots=True)
class PlanClosureInput:
    planning_value: PlanningInput
    source_timestamp: datetime | None
    hard_blocker: bool


def build_plan_closure_input(route: Route, now: datetime) -> PlanClosureInput:
    assessment = route.closure_assessment
    if assessment is None:
        return PlanClosureInput(
            planning_value="unknown",
            source_timestamp=None,
            hard_blocker=False,
        )
    planning_value = closure_planning_input(route, now)
    hard_blocker = planning_value == "active"
    source_timestamp = assessment.reviewed_at or assessment.updated_at
    return PlanClosureInput(
        planning_value=planning_value,
        source_timestamp=source_timestamp,
        hard_blocker=hard_blocker,
    )
