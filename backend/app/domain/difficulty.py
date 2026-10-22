import json
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.route import RouteType

_MAPPINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "difficulty_mappings.json"


@cache
def _load_mappings() -> dict:
    with _MAPPINGS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _metadata() -> dict[str, str]:
    table = _load_mappings()
    return {
        "mapping_version": table["version"],
        "mapping_source": table["source"],
        "mapping_citation": table["citation"],
    }


def _casefold_lookup(token: str, keys: list[str] | dict[str, object]) -> str | None:
    folded = token.casefold()
    for key in keys:
        if key.casefold() == folded:
            return key
    return None


def _canonical_scale(scale: str) -> str | None:
    aliases: dict[str, str] = _load_mappings()["scale_aliases"]
    if scale in aliases:
        return aliases[scale]
    return _casefold_lookup(scale, aliases)


def _allowed_mapped_huebler() -> list[str]:
    table = _load_mappings()
    scale_name = table["mapped_huebler_scale"]
    return table["scales"][scale_name]["order"]


class MappingConfidence(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNMAPPED = "unmapped"


class Difficulty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_type: RouteType
    original_value: str | None
    original_scale: str | None
    structured_scale: str | None
    structured_value: str | None
    mapped_huebler: str | None
    mapping_confidence: MappingConfidence
    mapping_source: str
    mapping_citation: str
    mapping_version: str

    @field_validator("structured_scale")
    @classmethod
    def structured_scale_must_be_known(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = _load_mappings()["allowed_structured_scales"]
        if value not in allowed:
            raise ValueError("structured_scale is not an allowed structured scale")
        return value

    @field_validator("mapped_huebler")
    @classmethod
    def mapped_huebler_must_be_in_table(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in _allowed_mapped_huebler():
            raise ValueError("mapped_huebler is not in the mapping table")
        return value

    @model_validator(mode="after")
    def check_difficulty_invariants(self) -> Self:
        unmapped = self.mapping_confidence is MappingConfidence.UNMAPPED
        if unmapped:
            if (
                self.structured_scale is not None
                or self.structured_value is not None
                or self.mapped_huebler is not None
            ):
                raise ValueError("unmapped difficulty cannot carry structured mapping fields")
            return self
        if self.structured_scale is None or self.structured_value is None:
            raise ValueError("mapped difficulty requires structured_scale and structured_value")
        if self.route_type is RouteType.KLETTERSTEIG:
            if self.mapped_huebler is None:
                raise ValueError("klettersteig mapping requires mapped_huebler")
        elif self.mapped_huebler is not None:
            raise ValueError("mapped_huebler is only set for klettersteig")
        return self


def map_difficulty(
    route_type: RouteType,
    original_value: str | None,
    original_scale: str | None,
) -> Difficulty:
    meta = _metadata()

    def unmapped(value: str | None, scale: str | None) -> Difficulty:
        return Difficulty(
            route_type=route_type,
            original_value=value,
            original_scale=scale,
            structured_scale=None,
            structured_value=None,
            mapped_huebler=None,
            mapping_confidence=MappingConfidence.UNMAPPED,
            **meta,
        )

    if original_value is None and original_scale is None:
        return unmapped(None, None)

    value = original_value.strip() if original_value is not None else None
    scale = original_scale.strip() if original_scale is not None else None
    if value is None or scale is None or value == "":
        return unmapped(value, scale)

    canonical = _canonical_scale(scale)
    allowed = _load_mappings()["allowed_scales_by_route_type"].get(route_type.value, [])
    if canonical is None or canonical not in allowed:
        return unmapped(value, scale)

    scale_data = _load_mappings()["scales"][canonical]
    entries: dict[str, dict] = scale_data["entries"]
    key = _casefold_lookup(value, entries)
    if key is None:
        return unmapped(value, scale)

    entry = entries[key]
    mapped = entry.get("mapped_huebler") if scale_data.get("assign_mapped_huebler") else None
    return Difficulty(
        route_type=route_type,
        original_value=value,
        original_scale=scale,
        structured_scale=canonical,
        structured_value=key,
        mapped_huebler=mapped,
        mapping_confidence=entry["confidence"],
        **meta,
    )


def is_harder(a: Difficulty, b: Difficulty) -> bool:
    table = _load_mappings()
    if a.route_type != b.route_type:
        raise TypeError("cannot compare difficulty across route types")
    if a.structured_scale != b.structured_scale:
        raise TypeError("cannot compare difficulty across structured scales")
    if (
        a.mapping_confidence is MappingConfidence.UNMAPPED
        or b.mapping_confidence is MappingConfidence.UNMAPPED
        or a.structured_scale is None
        or b.structured_scale is None
        or a.structured_value is None
        or b.structured_value is None
    ):
        raise TypeError("cannot compare unmapped difficulty")
    if a.structured_scale in table["incomparable_structured_scales"]:
        raise TypeError("cannot compare grades on a scale without an order table in this issue")
    order: list[str] = table["scales"][a.structured_scale]["order"]
    try:
        return order.index(a.structured_value) > order.index(b.structured_value)
    except ValueError as exc:
        raise TypeError("structured_value is not in the order table") from exc


from app.domain.route import Route

Route.model_rebuild(_types_namespace={"Difficulty": Difficulty})
