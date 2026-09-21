"""Tests for streaming export endpoints and administrative API."""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_export_csv():
    response = client.get("/api/v1/export/processes?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"stf_processes.csv\"" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert len(lines) > 1
    assert "process_id" in lines[0]


def test_export_jsonl():
    response = client.get("/api/v1/export/decisions?format=jsonl")
    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["content-type"]
    assert "attachment; filename=\"stf_decisions.jsonl\"" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert len(lines) > 0


def test_export_parquet():
    response = client.get("/api/v1/export/budget?format=parquet")
    assert response.status_code == 200
    assert "application/vnd.apache.parquet" in response.headers["content-type"]
    assert len(response.content) > 0


def test_export_invalid_dataset():
    response = client.get("/api/v1/export/nonexistent?format=csv")
    assert response.status_code == 400
    assert "Invalid dataset" in response.json()["detail"]


def test_export_invalid_format():
    response = client.get("/api/v1/export/processes?format=xml")
    assert response.status_code == 422  # validation error from regex/pattern


def test_administrative_endpoints():
    # Budget summary
    res_b = client.get("/api/v1/administrative/budget/summary")
    assert res_b.status_code == 200
    b_data = res_b.json()
    assert isinstance(b_data, list)
    assert len(b_data) > 0
    assert "ano_exercicio" in b_data[0]
    assert "dotacao_atualizada_milhoes" in b_data[0]

    # Remuneration summary
    res_r = client.get("/api/v1/administrative/remuneration/summary")
    assert res_r.status_code == 200
    r_data = res_r.json()
    assert isinstance(r_data, dict)
    assert "media_remuneracao_liquida" in r_data

    # Personnel roster
    res_p = client.get("/api/v1/administrative/personnel")
    assert res_p.status_code == 200
    p_data = res_p.json()
    assert "by_category" in p_data
    assert "top_departments" in p_data
    assert len(p_data["by_category"]) > 0


def test_survival_endpoint():
    response = client.get("/api/v1/analytics/survival")
    assert response.status_code == 200
    data = response.json()
    assert "global" in data
    assert "stratified_by_class" in data
    assert "stratified_by_judge" in data
    assert data["global"]["median_days"] is not None
