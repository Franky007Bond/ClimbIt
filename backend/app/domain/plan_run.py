from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanRunVersions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules_version: str
    mapping_version: str
    adapter_versions: dict[str, str]


class PlanRun(BaseModel):
    """Immutable stored plan run per spec section 4.6."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    route_id: uuid.UUID
    created_at: datetime
    input_snapshot: dict[str, Any]
    source_timestamps: dict[str, datetime | None]
    rules_version: str
    mapping_version: str
    adapter_versions: dict[str, str]
    explanation: list[str] = Field(default_factory=list)
    result: dict[str, Any]
