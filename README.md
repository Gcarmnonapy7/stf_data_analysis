# 🇧🇷 STF Transparency Platform

> **Open-source data engineering and analytical lakehouse for Brazilian Supreme Court (*Supremo Tribunal Federal* - STF) public data.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Engine: Polars & DuckDB](https://img.shields.io/badge/Engine-Polars%20%26%20DuckDB-orange.svg)](https://duckdb.org/)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 Mission & Purpose

The **STF Transparency Platform** is a serious, open-source data engineering and analytics platform that collects, transforms, stores, and exposes public datasets from the Brazilian Supreme Federal Court (*Corte Aberta* / Resolução nº 774/2022).

The purpose of this platform is **not** to dictate opinion on judicial decisions, but to provide a reproducible, auditable analytical layer over the Court's open-data ecosystem. It transforms heterogeneous raw CSV/XLSX downloads into a documented dimensional lakehouse accessible via high-performance SQL, Parquet, and an open REST API.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph S1["1. Ingestion Layer (Bronze)"]
        CA["STF Corte Aberta (CSV / XLSX / API)"] --> Downloader["Downloader Engine (ingestion/download.py)"]
        Downloader --> Meta["Metadata Provenance Tracker (SHA-256)"]
        Downloader --> Bronze["data/raw/ (Immutable CSVs + Manifest)"]
    end

    subgraph S2["2. Transformation Layer (Silver)"]
        Bronze --> PolarsNorm["Polars Vectorized Normalization"]
        PolarsNorm --> DQ["Data Quality & Contract Gate"]
        DQ --> SilverParquet["data/silver/ (*.parquet)"]
    end

    subgraph S3["3. Dimensional Lakehouse (Gold)"]
        SilverParquet --> StarSchema["Star-Schema Dimensional Modeler"]
        StarSchema --> Facts["fact_processes / fact_decisions / fact_appeals"]
        StarSchema --> Dims["dim_date / dim_process_type / dim_origin / dim_rapporteur"]
        Facts & Dims --> DuckDB[(DuckDB Lakehouse: stf_warehouse.duckdb)]
    end

    subgraph S4["4. Serving & Auditability"]
        DuckDB --> FastAPI["FastAPI REST Service (/api/v1)"]
        DuckDB --> Lineage["Lineage Engine ('Where did this number come from?')"]
        DuckDB --> SQL["Analytical SQL Queries"]
    end
```

---

## 📦 Data Layers (Medallion Architecture)

### 🥉 1. Bronze — Raw (`data/raw/`)
Stores the original STF files exactly as downloaded. Raw data is strictly immutable.
Every ingestion logs an audit record in `data/metadata/manifest.jsonl` with:
- `source_url`
- `download_timestamp` (ISO 8601 UTC)
- `file_hash_sha256`
- `dataset_version`
- `row_count` and `file_size_bytes`

### 🥈 2. Silver — Clean & Normalized (`data/silver/`)
High-performance normalization powered by **Polars**:
- Canonical `snake_case` column naming.
- Strict type casting (`pl.Int64`, `pl.Date`, `pl.Utf8`).
- Deduplication on primary keys (`process_id`, `decision_id`).
- Standardized macro decision categories (`MONOCRATICA`, `COLEGIADA`, `PRESIDENCIA`).
- Normalized Brazilian state codes (`uf_origem`).
- Compressed, columnar storage in **Parquet (ZSTD)**.

### 🥇 3. Gold — Analytical Star Schema (`data/curated/`)
Curated dimensional models optimized for OLAP aggregations:
- **Facts**: `fact_processes`, `fact_decisions`, `fact_appeals`
- **Dimensions**: `dim_date`, `dim_process_type`, `dim_rapporteur`, `dim_origin`, `dim_subject`
- **Engine**: Embedded **DuckDB** (`stf_warehouse.duckdb`) enabling serverless, zero-copy analytics.

---

## 🔥 Data Lineage: "Where did this number come from?"

Every metric, dataset, and API response can be traced vertically to its exact raw source file and ingestion manifest.

```
Dashboard / API
      │
      ▼
SQL Analytical Query
      │
      ▼
Gold Dataset (fact_decisions)
      │
      ▼
Polars Normalization (v0.1.0-clean)
      │
      ▼
Silver Parquet (silver/decisoes.parquet)
      │
      ▼
Raw CSV (raw/decisoes/decisoes_raw.csv | SHA-256: 0304d4471a9c...)
      │
      ▼
STF Corte Aberta (Portal STF / Resolução 774/2022)
```

Example response from `/api/v1/lineage/fact_decisions`:
```json
{
  "target_entity": "fact_decisions",
  "validation_status": "PASS",
  "lineage_nodes": [
    {
      "layer": "GOLD_ANALYTICAL",
      "name": "fact_decisions",
      "version": "v0.1.0-star",
      "row_count": 1513
    },
    {
      "layer": "SILVER_CLEAN",
      "name": "silver/decisoes.parquet",
      "version": "v0.1.0-clean",
      "row_count": 1513
    },
    {
      "layer": "BRONZE_RAW",
      "name": "raw/decisoes/decisoes_raw.csv",
      "hash_or_checksum": "0304d4471a9c45420fd32d49a7dc71bb4ab6716df0c182c574b9ebf41c921cb6",
      "row_count": 1513
    },
    {
      "layer": "SOURCE",
      "name": "STF Corte Aberta",
      "version": "Official Portal"
    }
  ]
}
```

---

## 🧪 Data Quality Contracts

Automated quality gates execute as part of the pipeline run (`quality/runner.py`):
- [x] **Primary Key Uniqueness**: Zero duplicate `process_id` or `decision_id` entries.
- [x] **Not-Null Critical Fields**: Mandatory identifiers and distribution dates.
- [x] **Date Sanity**: No impossible or future dates.
- [x] **Referential Temporal Consistency**: Decision date $\ge$ Distribution date.
- [x] **Categorical Validity**: State codes strictly validated against ISO 3166-2:BR.
- [x] **Checksum Integrity**: Re-verified against ingestion manifests.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- `make` (optional) or standard virtual environment

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/gabrielcarmonapy/sft_data.git
cd sft_data

# Set up environment and install dependencies
make install
# or:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Run the Full End-to-End Pipeline
```bash
# Ingests, normalizes, validates, and builds DuckDB star-schema:
make pipeline
# or:
.venv/bin/python -m pipelines.runner --sample --rows 1000
```

### 3. Run Automated Tests
```bash
make test
# or:
.venv/bin/pytest tests/ -v
```

### 4. Launch the REST API
```bash
make api
# or:
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to interactive OpenAPI documentation at **`http://localhost:8000/docs`**.

---

## 📊 Analytical Insights (DuckDB Queries)

Core analytical queries are documented in [`analytics/sql/kpis.sql`](analytics/sql/kpis.sql):
- **Annual Case Inflow & Backlog Trends**
- **Distribution by Legal Class** (`ADI`, `RE`, `HC`, `ARE`, `ADPF`, etc.)
- **Monocratic vs. Collegiate Decision Ratios**
- **Outcome Distribution** (`Provido`, `Não Provido`, `Negado Seguimento`, etc.)
- **Decisions by Reporting Justice** (*Relator*)
- **Lead Time from Distribution to Decision**

---

## 📁 Repository Layout

```
stf-transparency-platform/
├── README.md               # Project overview and documentation
├── pyproject.toml          # Project configuration and dependencies
├── requirements.txt        # Pinned virtual environment dependencies
├── Makefile                # Automation commands
├── Dockerfile              # Container definition
├── docker-compose.yml      # Local dev and orchestration
│
├── ingestion/              # Ingestion layer (Bronze)
│   ├── download.py         # Resilient HTTP extractor
│   ├── metadata.py         # SHA-256 provenance tracker
│   └── fixtures.py         # Schema-valid synthetic sample generator
│
├── transformations/        # Vectorized Polars transformations (Silver)
│   ├── processes.py        # Case normalization and deduplication
│   ├── decisions.py        # Decision categorization
│   └── appeals.py          # Appeals & Repercussão Geral
│
├── quality/                # Data quality & governance
│   ├── runner.py           # Automated test assertions
│   └── lineage.py          # Traceability engine
│
├── pipelines/              # Master pipeline orchestration
│   ├── runner.py           # Medallion lifecycle runner
│   └── gold/builder.py     # Star-schema builder
│
├── analytics/              # Analytical lakehouse layer
│   ├── duckdb_client.py    # DuckDB client connection manager
│   └── sql/kpis.sql        # Standard analytical queries
│
├── api/                    # Serving REST API (FastAPI)
│   ├── main.py             # App entrypoint
│   ├── schemas/models.py   # Pydantic models
│   └── routes/             # Endpoints (processes, decisions, analytics, lineage)
│
├── docs/                   # Engineering documentation
│   ├── architecture.md     # Architecture documentation
│   ├── data_dictionary.md  # Detailed schema definitions
│   └── methodology.md      # Neutrality principles and metric math
│
├── data/                   # Data lakehouse directory (local storage)
│   ├── raw/                # Bronze immutable files
│   ├── silver/             # Silver clean Parquet tables
│   ├── curated/            # Gold dimensional models & DuckDB database
│   └── metadata/           # Ingestion manifests
│
└── tests/                  # Pytest test suite
    ├── test_ingestion.py
    ├── test_transformations.py
    ├── test_quality.py
    └── test_api.py
```

---

## 🗺️ Roadmap

- [x] **v0.1 — MVP Scaffolding & Core Architecture**
  - [x] Automated downloader & sample fixture generator
  - [x] SHA-256 metadata provenance tracking (`manifest.jsonl`)
  - [x] Polars Bronze $\rightarrow$ Silver transformations
  - [x] Gold dimensional star-schema (`fact_processes`, `fact_decisions`, `dims`)
  - [x] Embedded DuckDB lakehouse integration
  - [x] Data Quality assertion gate (11 automated checks)
  - [x] End-to-end data lineage engine
  - [x] FastAPI REST service with OpenAPI documentation
  - [x] Comprehensive Pytest test suite
- [ ] **v0.2 — Data Engineering Scaling**
  - [ ] Scheduled recurring incremental crawlers (`cron`)
  - [ ] DuckDB Iceberg / Delta Lake export options
  - [ ] Administrative domain data (Remuneração, Orçamento, Pessoal)
- [ ] **v0.3 — Analytics & Notebooks**
  - [ ] Reproducible Jupyter exploratory notebooks
  - [ ] Temporal survival analysis on process backlog
- [ ] **v0.4 — Advanced Serving**
  - [ ] DuckDB WebAssembly (Wasm) client-side querying
  - [ ] Export endpoints (Streaming CSV / JSON Lines / Parquet)
- [ ] **v0.5 — Dashboard**
  - [ ] Pre-configured Grafana and Superset dashboards
- [ ] **v1.0 — Public Platform Deployment**
  - [ ] Automated CI/CD GitHub Actions workflow
  - [ ] Public container registry release

---

## 📜 License

Licensed under the [Apache License, Version 2.0](LICENSE).
