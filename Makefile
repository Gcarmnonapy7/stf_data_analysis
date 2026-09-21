.PHONY: help install ingest pipeline quality api test lint clean

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
PYTEST = .venv/bin/pytest
UVICORN = .venv/bin/uvicorn

help:
	@echo "STF Transparency Platform — Development Commands"
	@echo "--------------------------------------------------"
	@echo "make install    : Initialize virtualenv and install dependencies"
	@echo "make ingest     : Ingest raw datasets from STF (sample or live)"
	@echo "make pipeline   : Run full Bronze -> Silver -> Quality -> Gold pipeline"
	@echo "make quality    : Run automated data quality assertion checks"
	@echo "make api        : Launch FastAPI service on http://localhost:8000"
	@echo "make test       : Run test suite with pytest"
	@echo "make clean      : Remove cache and temporary test files"

install:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"
	$(PIP) freeze > requirements.txt

ingest:
	$(PYTHON) -m ingestion.download --sample --rows 1000

pipeline:
	$(PYTHON) -m pipelines.runner --sample --rows 1000

quality:
	$(PYTHON) -m quality.runner

api:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTEST) tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
