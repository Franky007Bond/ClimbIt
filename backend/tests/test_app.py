from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app


def test_app_is_a_fastapi_instance() -> None:
    assert isinstance(app, FastAPI)


def test_root_is_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 404


def test_openapi_lists_health_and_ready() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "ClimbIt"
    assert "/health" in body["paths"]
    assert "/ready" in body["paths"]
    assert "/routes" in body["paths"]
    assert "/routes/{route_id}" in body["paths"]
    route_detail = body["paths"]["/routes/{route_id}"]["get"]
    assert "route_id" in route_detail["parameters"][0]["name"]
    assert "200" in route_detail["responses"]
