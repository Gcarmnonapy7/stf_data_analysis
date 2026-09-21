.PHONY: help install ingest crawl-incremental pipeline quality export-delta export-iceberg export-all survival notebooks report api grafana test lint clean

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
PYTEST = .venv/bin/pytest
UVICORN = .venv/bin/uvicorn

help:
	@echo "STF Transparency Platform — Development Commands"
	@echo "--------------------------------------------------"
	@echo "make install           : Initialize virtualenv and install dependencies"
	@echo "make ingest            : Ingest raw datasets from STF (sample or live)"
	@echo "make crawl-incremental : Run incremental crawler with watermarks"
	@echo "make pipeline          : Run full Bronze -> Silver -> Quality -> Gold pipeline"
	@echo "make quality           : Run automated data quality assertion checks"
	@echo "make export-delta      : Export curated Gold tables to Delta Lake"
	@echo "make export-iceberg    : Export curated Gold tables to Apache Iceberg"
	@echo "make export-all        : Export curated Gold tables to both Delta and Iceberg"
	@echo "make survival          : Run Kaplan-Meier backlog survival analysis"
	@echo "make notebooks         : Launch Jupyter Lab for exploratory notebooks"
	@echo "make report            : Generate executive statistical analysis report"
	@echo "make api               : Launch FastAPI service on http://localhost:8000"
	@echo "make grafana           : Start API and Grafana via Docker Compose"
	@echo "make test              : Run test suite with pytest"
	@echo "make clean             : Remove cache and temporary test files"

install:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"
	$(PIP) freeze > requirements.txt

ingest:
	$(PYTHON) -m ingestion.download --sample --rows 1000

crawl-incremental:
	$(PYTHON) -m ingestion.crawler --dataset all --batch-size 50

pipeline:
	$(PYTHON) -m pipelines.runner --sample --rows 1000

quality:
	$(PYTHON) -m quality.runner

export-delta:
	$(PYTHON) -m pipelines.export.lake_formats --format delta

export-iceberg:
	$(PYTHON) -m pipelines.export.lake_formats --format iceberg

export-all:
	$(PYTHON) -m pipelines.export.lake_formats --format both

survival:
	$(PYTHON) -m analytics.survival

notebooks:
	$(PYTHON) -m jupyter lab analytics/notebooks/

report:
	$(PYTHON) analytics/run_analysis.py

api:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

grafana:
	docker compose up -d

test:
	$(PYTEST) tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +


