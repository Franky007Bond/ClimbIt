from __future__ import annotations

import json
import uuid
import warnings
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import RefResolver, validate

from app.data.seed_routes import (
    PUBLISHED_ALPINE_HIKE_SLUG,
    QUARANTINED_KLETTERSTEIG_SLUG,
    seed_route_id,
)
from app.export_openapi import openapi_document
from app.main import app

pytest_plugins = ["tests.test_route_search"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _committed_openapi() -> dict:
    path = _repo_root() / "contracts" / "openapi.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _response_schema(spec: dict, path: str, method: str, status: str) -> dict:
    operation = spec["paths"][path][method]
    return operation["responses"][status]["content"]["application/json"]["schema"]


def _validate_json_against_openapi(
    spec: dict,
    instance: object,
    path: str,
    method: str,
    status: str = "200",
) -> None:
    schema = _response_schema(spec, path, method, status)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = RefResolver.from_schema(spec)
    validate(instance, schema, resolver=resolver)


def test_live_openapi_matches_committed_contract() -> None:
    exported = openapi_document()
    committed = _committed_openapi()
    with TestClient(app) as client:
        live = client.get("/openapi.json").json()
    for section in ("paths", "components", "info"):
        assert live[section] == committed[section] == exported[section]


def test_committed_openapi_includes_route_operations() -> None:
    spec = _committed_openapi()
    list_op = spec["paths"]["/routes"]["get"]
    assert list_op["operationId"] == "list_routes_routes_get"
    detail_op = spec["paths"]["/routes/{route_id}"]["get"]
    assert detail_op["operationId"] == "get_route_detail_routes__route_id__get"
    assert "route_id" in {param["name"] for param in detail_op["parameters"]}


def test_get_routes_response_matches_openapi_schema(seeded_client: TestClient) -> None:
    spec = _committed_openapi()
    response = seeded_client.get("/routes")
    assert response.status_code == 200
    body = response.json()
    assert body["routes"]
    _validate_json_against_openapi(spec, body, "/routes", "get")


def test_get_route_detail_response_matches_openapi_schema(
    seeded_client: TestClient,
) -> None:
    spec = _committed_openapi()
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.get(f"/routes/{route_id}")
    assert response.status_code == 200
    _validate_json_against_openapi(
        spec,
        response.json(),
        "/routes/{route_id}",
        "get",
    )


def test_quarantined_route_detail_returns_404(seeded_client: TestClient) -> None:
    route_id = seed_route_id(QUARANTINED_KLETTERSTEIG_SLUG)
    response = seeded_client.get(f"/routes/{route_id}")
    assert response.status_code == 404


def test_unknown_route_detail_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.get(f"/routes/{uuid.uuid4()}")
    assert response.status_code == 404
