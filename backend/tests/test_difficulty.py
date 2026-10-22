import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.difficulty import (
    Difficulty,
    MappingConfidence,
    is_harder,
    map_difficulty,
)
from app.domain.route import RouteType

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MAPPINGS_PATH = _BACKEND_ROOT / "app" / "data" / "difficulty_mappings.json"
_DIFFICULTY_PY = _BACKEND_ROOT / "app" / "domain" / "difficulty.py"


def _table() -> dict:
    return json.loads(_MAPPINGS_PATH.read_text(encoding="utf-8"))


def test_mapping_file_is_utf8_json_with_metadata() -> None:
    table = _table()
    assert isinstance(table["version"], str)
    assert table["version"]
    assert isinstance(table["source"], str)
    assert table["source"]
    assert isinstance(table["citation"], str)
    assert table["citation"]
    aliases = table["scale_aliases"]
    assert aliases["huebler"] == "huebler"
    assert aliases["Huebler"] == "huebler"
    assert aliases["Hübler"] == "huebler"


def test_k1_k6_table_rows_are_exact_in_json() -> None:
    entries = _table()["scales"]["k1_k6"]["entries"]
    expected = {
        "K1": "A",
        "K2": "B",
        "K3": "C",
        "K4": "D",
        "K5": "E",
        "K6": "F",
    }
    for token, letter in expected.items():
        assert entries[token]["mapped_huebler"] == letter
        assert entries[token]["confidence"] == "exact"


def test_python_mapping_reads_json_and_has_no_grade_literals() -> None:
    source = _DIFFICULTY_PY.read_text(encoding="utf-8")
    assert "json.load" in source
    tree = ast.parse(source)
    constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    table = _table()
    forbidden: set[str] = set()
    for scale in table["scales"].values():
        forbidden.update(scale["order"])
        forbidden.update(scale["entries"])
        for entry in scale["entries"].values():
            mapped = entry.get("mapped_huebler")
            if isinstance(mapped, str):
                forbidden.add(mapped)
    overlap = constants & forbidden
    assert overlap == set()


@pytest.mark.parametrize("bad", ["unknown", "safe", "exact-ish"])
def test_mapping_confidence_rejects_other_strings(bad: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        MappingConfidence(bad)


def test_mapping_confidence_values_are_exact() -> None:
    assert MappingConfidence.EXACT.value == "exact"
    assert MappingConfidence.APPROXIMATE.value == "approximate"
    assert MappingConfidence.UNMAPPED.value == "unmapped"


def test_difficulty_forbids_extra_and_has_no_rank_fields() -> None:
    mapped = map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler")
    with pytest.raises(ValidationError):
        Difficulty.model_validate({**mapped.model_dump(), "rank": 1})
    for name in ("rank", "numeric", "numeric_value", "comparable_rank"):
        assert name not in Difficulty.model_fields
        assert name not in mapped.model_dump()


@pytest.mark.parametrize("route_type", list(RouteType))
def test_missing_data_is_unmapped_never_a_stand_in_grade(route_type: RouteType) -> None:
    result = map_difficulty(route_type, None, None)
    assert result.mapping_confidence is MappingConfidence.UNMAPPED
    assert result.structured_scale is None
    assert result.structured_value is None
    assert result.mapped_huebler is None
    assert result.original_value is None
    assert result.original_scale is None
    assert result.mapping_version == _table()["version"]
    assert result.mapping_source == _table()["source"]
    assert result.mapping_citation == _table()["citation"]
    dumped = result.model_dump()
    for stand_in in ("A", "K1", "T1", "exact"):
        assert stand_in not in dumped.values()


@pytest.mark.parametrize("letter", ["A", "B", "C", "D", "E", "F"])
def test_huebler_identity_exact(letter: str) -> None:
    result = map_difficulty(RouteType.KLETTERSTEIG, letter, "huebler")
    assert result.structured_scale == "huebler"
    assert result.structured_value == letter
    assert result.mapped_huebler == letter
    assert result.mapping_confidence is MappingConfidence.EXACT


def test_huebler_aliases_and_strip_casefold() -> None:
    for scale in ("Huebler", "Hübler"):
        result = map_difficulty(RouteType.KLETTERSTEIG, "C", scale)
        assert result.mapped_huebler == "C"
        assert result.mapping_confidence is MappingConfidence.EXACT
        assert result.original_scale == scale
    spaced = map_difficulty(RouteType.KLETTERSTEIG, " c ", "huebler")
    assert spaced.structured_value == "C"
    assert spaced.mapped_huebler == "C"
    assert spaced.original_value == "c"


@pytest.mark.parametrize(
    "token, mapped",
    [("K1", "A"), ("K2", "B"), ("K3", "C"), ("K4", "D"), ("K5", "E"), ("K6", "F")],
)
def test_k_scale_exact_table(token: str, mapped: str) -> None:
    result = map_difficulty(RouteType.KLETTERSTEIG, token, "k1_k6")
    assert result.structured_scale == "k1_k6"
    assert result.structured_value == token
    assert result.mapped_huebler == mapped
    assert result.mapping_confidence is MappingConfidence.EXACT


def test_k3_strip_and_adjacent_k_grades() -> None:
    result = map_difficulty(RouteType.KLETTERSTEIG, " k3 ", "k1_k6")
    assert result.structured_value == "K3"
    assert result.mapped_huebler == "C"
    assert map_difficulty(RouteType.KLETTERSTEIG, "K2", "k1_k6").mapped_huebler == "B"
    assert map_difficulty(RouteType.KLETTERSTEIG, "K4", "k1_k6").mapped_huebler == "D"


@pytest.mark.parametrize(
    "value, scale, mapped, structured_scale, structured_value",
    [
        ("K3+", "k1_k6", "D", "k1_k6", "K3+"),
        ("K3/K4", "k1_k6", "D", "k1_k6", "K3/K4"),
        ("K2+", "k1_k6", "C", "k1_k6", "K2+"),
        ("A+", "huebler", "B", "huebler", "A+"),
        ("A/B", "huebler", "B", "huebler", "A/B"),
        ("B-", "huebler", "B", "huebler", "B-"),
        ("C/D", "huebler", "D", "huebler", "C/D"),
        ("E/F", "huebler", "F", "huebler", "E/F"),
        ("A-", "huebler", "A", "huebler", "A-"),
    ],
)
def test_ambiguous_rounds_to_harder_huebler(
    value: str,
    scale: str,
    mapped: str,
    structured_scale: str,
    structured_value: str,
) -> None:
    result = map_difficulty(RouteType.KLETTERSTEIG, value, scale)
    assert result.mapped_huebler == mapped
    assert result.mapping_confidence is MappingConfidence.APPROXIMATE
    assert result.structured_scale == structured_scale
    assert result.structured_value == structured_value


@pytest.mark.parametrize(
    "route_type, value, scale",
    [
        (RouteType.KLETTERSTEIG, "K0", "k1_k6"),
        (RouteType.KLETTERSTEIG, "K7", "k1_k6"),
        (RouteType.KLETTERSTEIG, "K6+", "k1_k6"),
        (RouteType.KLETTERSTEIG, "G", "huebler"),
        (RouteType.KLETTERSTEIG, "F+", "huebler"),
        (RouteType.ALPINE_HIKE, "T7", "sac"),
        (RouteType.ALPINE_HIKE, "T0", "sac"),
        (RouteType.KLETTERSTEIG, "", "huebler"),
        (RouteType.KLETTERSTEIG, "C", "YDS"),
        (RouteType.KLETTERSTEIG, "Z", "Huebler"),
        (RouteType.ALPINE_HIKE, "T3+", "sac"),
        (RouteType.ALPINE_HIKE, "K3", "k1_k6"),
        (RouteType.ALPINE_HIKE, "C", "huebler"),
        (RouteType.OUTDOOR_CLIMBING, "C", "huebler"),
        (RouteType.OUTDOOR_CLIMBING, "5.14a", "YDS"),
        (RouteType.KLETTERSTEIG, "6a", "french"),
    ],
)
def test_outside_table_is_unmapped(
    route_type: RouteType, value: str, scale: str
) -> None:
    result = map_difficulty(route_type, value, scale)
    assert result.mapping_confidence is MappingConfidence.UNMAPPED
    assert result.structured_scale is None
    assert result.structured_value is None
    assert result.mapped_huebler is None
    assert result.original_value == value
    assert result.original_scale == scale


@pytest.mark.parametrize("token", ["T1", "T2", "T3", "T4", "T5", "T6"])
def test_sac_exact_no_huebler(token: str) -> None:
    result = map_difficulty(RouteType.ALPINE_HIKE, token, "sac")
    assert result.structured_scale == "sac"
    assert result.structured_value == token
    assert result.mapped_huebler is None
    assert result.mapping_confidence is MappingConfidence.EXACT


def test_sac_alias_and_adjacent_tokens() -> None:
    aliased = map_difficulty(RouteType.ALPINE_HIKE, "T3", "SAC")
    assert aliased.structured_value == "T3"
    assert aliased.mapping_confidence is MappingConfidence.EXACT
    assert map_difficulty(RouteType.ALPINE_HIKE, "T4", "sac").structured_value == "T4"


def test_outdoor_climbing_french_and_uiaa_only() -> None:
    french = map_difficulty(RouteType.OUTDOOR_CLIMBING, "6a", "french")
    assert french.structured_scale == "french"
    assert french.structured_value == "6a"
    assert french.mapped_huebler is None
    assert french.mapping_confidence is MappingConfidence.EXACT
    uiaa = map_difficulty(RouteType.OUTDOOR_CLIMBING, "V", "uiaa")
    assert uiaa.structured_scale == "uiaa"
    assert uiaa.structured_value == "V"
    assert uiaa.mapped_huebler is None
    assert uiaa.mapping_confidence is MappingConfidence.EXACT
    assert map_difficulty(RouteType.OUTDOOR_CLIMBING, "6a", "French").structured_scale == "french"
    assert map_difficulty(RouteType.OUTDOOR_CLIMBING, "V", "UIAA").structured_scale == "uiaa"


def test_no_cross_type_ranking() -> None:
    huebler_c = map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler")
    sac_t4 = map_difficulty(RouteType.ALPINE_HIKE, "T4", "sac")
    french_6a = map_difficulty(RouteType.OUTDOOR_CLIMBING, "6a", "french")
    with pytest.raises(TypeError):
        huebler_c < sac_t4  # noqa: B015
    with pytest.raises(TypeError):
        huebler_c > sac_t4  # noqa: B015
    with pytest.raises(TypeError):
        huebler_c <= sac_t4  # noqa: B015
    with pytest.raises(TypeError):
        huebler_c >= sac_t4  # noqa: B015
    with pytest.raises(TypeError):
        sorted([huebler_c, sac_t4])
    with pytest.raises(TypeError):
        huebler_c < french_6a  # noqa: B015
    with pytest.raises(TypeError):
        sac_t4 < french_6a  # noqa: B015
    with pytest.raises(TypeError):
        is_harder(huebler_c, sac_t4)
    with pytest.raises(TypeError):
        is_harder(french_6a, french_6a)
    with pytest.raises(TypeError):
        is_harder(
            map_difficulty(RouteType.KLETTERSTEIG, "K4", "k1_k6"),
            map_difficulty(RouteType.KLETTERSTEIG, "D", "huebler"),
        )
    with pytest.raises(TypeError):
        is_harder(
            map_difficulty(RouteType.KLETTERSTEIG, None, None),
            map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler"),
        )


def test_is_harder_same_scale() -> None:
    harder = map_difficulty(RouteType.KLETTERSTEIG, "D", "huebler")
    easier = map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler")
    assert is_harder(harder, easier) is True
    assert is_harder(easier, harder) is False
    assert is_harder(easier, easier) is False
    k4 = map_difficulty(RouteType.KLETTERSTEIG, "K4", "k1_k6")
    k3 = map_difficulty(RouteType.KLETTERSTEIG, "K3", "k1_k6")
    assert is_harder(k4, k3) is True
    assert is_harder(k3, k4) is False


def test_map_difficulty_does_not_mutate_route() -> None:
    from tests.test_route_model import _route

    route = _route(
        route_type=RouteType.KLETTERSTEIG,
        original_difficulty_value="K3",
        original_difficulty_scale="k1_k6",
    )
    before = route.model_dump()
    mapped = map_difficulty(route.route_type, route.original_difficulty_value, route.original_difficulty_scale)
    assert mapped.mapped_huebler == "C"
    assert route.difficulty is None
    assert route.model_dump() == before
