"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    assert data["docs_url"] == "/docs"
    assert "endpoints" in data


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_get_processes():
    response = client.get("/api/v1/processes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) <= 5
    if data["items"]:
        first = data["items"][0]
        assert "process_id" in first
        assert "classe_sigla" in first


def test_get_decisions():
    response = client.get("/api/v1/decisions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) <= 5


def test_get_analytics_overview():
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_processes" in data
    assert "total_decisions" in data
    assert data["total_processes"] >= 0


def test_get_lineage():
    response = client.get("/api/v1/lineage/fact_decisions")
    assert response.status_code == 200
    data = response.json()
    assert data["target_entity"] == "fact_decisions"
    assert "lineage_nodes" in data
    assert len(data["lineage_nodes"]) >= 3

