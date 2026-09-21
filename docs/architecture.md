# 🏗️ STF Transparency Platform — Architecture

The **STF Transparency Platform** is an open-source, reproducible data engineering platform designed to collect, transform, validate, store, and expose public judicial data from the Brazilian Supreme Federal Court (*Supremo Tribunal Federal* - STF / *Corte Aberta*).

---

## 1. High-Level System Architecture

```
 STF / Corte Aberta
        │
        ▼
┌──────────────────┐
│  Data Ingestion  │  HTTP Client (SSL / Retries) & Metadata Provenance
│  CSV / XLSX / API│  SHA-256 Checksums, Timestamps, Row Counts
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Raw Layer     │  Bronze Zone: data/raw/
│  Original Files  │  Immutable CSV files with full manifest tracking
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Transformation  │  Silver Zone: data/silver/
│  Polars Pipeline │  Deduplication, Schema Enforcement, ISO Dates
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Data Quality   │  Quality Contracts: quality/runner.py
│  Integrity Gate  │  Referential checks, Uniqueness, Reasonable Dates
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Curated Layer   │  Gold Zone: data/curated/
│ Parquet + DuckDB │  Star Schema: fact_processes, fact_decisions, dims
└────────┬─────────┘
         │
    ┌────┴─────────────┐
    ▼                  ▼
┌─────────────┐  ┌──────────────┐
│  REST API   │  │  Analytics   │
│   FastAPI   │  │ SQL / Python │
└──────┬──────┘  └──────┬───────┘
       │                │
       └────────┬───────┘
                ▼
         ┌──────────────┐
         │  Dashboard   │
         │ Grafana / UI │
         └──────────────┘
```

---

## 2. Medallion Storage Architecture

### 🥉 Bronze — Raw Zone (`data/raw/`)
- **Immutability Guarantee**: Raw downloads are never modified in place.
- **Manifest Tracking**: Every file written records `download_timestamp`, `source_url`, `file_hash_sha256`, `row_count`, `file_size_bytes`, and `dataset_version` into `data/metadata/manifest.jsonl`.
- **Layout**:
  ```
  data/raw/
  ├── processos/processos_raw.csv
  ├── decisoes/decisoes_raw.csv
  ├── recursos/recursos_raw.csv
  └── repercussao_geral/repercussao_geral_raw.csv
  ```

### 🥈 Silver — Clean Zone (`data/silver/`)
- **Engine**: Powered by **Polars** for multi-threaded, low-memory vectorized transformations.
- **Operations**:
  - Column name canonicalization to `snake_case`.
  - Type casting (`pl.Int64`, `pl.Date`, `pl.Utf8`).
  - Deduplication on primary keys (`process_id`, `decision_id`, `recurso_id`).
  - Categorical standardization (macro decision categories, normalized Brazilian state codes).
  - Columnar compression with **Zstandard (zstd)** into Parquet.

### 🥇 Gold — Analytical Zone (`data/curated/`)
- **Dimensional Star Schema**:
  - **Facts**:
    - `fact_processes` (grain: 1 process)
    - `fact_decisions` (grain: 1 decision)
    - `fact_appeals` (grain: 1 appeal)
  - **Dimensions**:
    - `dim_date` (rich calendar dimension with Portuguese month/day names, quarters, day-of-week)
    - `dim_process_type` (ADI, ADC, RE, HC, ARE, etc.)
    - `dim_rapporteur` (Supreme Court Justices / Relatores)
    - `dim_origin` (UF and Macro-region: Sudeste, Sul, Nordeste, Centro-Oeste, Norte)
    - `dim_subject` (Major branch of law & sub-specialty)
- **Engine**: Embedded **DuckDB** (`stf_warehouse.duckdb`) providing serverless zero-copy analytics over local Parquet files.

---

## 3. Data Lineage & Provenance Guarantee

Every metric, dashboard panel, and analytical dataset exposes complete vertical lineage:

$$\text{Dashboard Panel} \longrightarrow \text{SQL Query} \longrightarrow \text{Gold Model} \longrightarrow \text{Silver Parquet} \longrightarrow \text{Bronze Raw CSV} \longrightarrow \text{STF Source}$$

A consumer can query `/api/v1/lineage/{entity_name}` and retrieve:
- Source Authority & Legal Basis (STF Resolução 774/2022)
- Exact download timestamp & source URL
- Cryptographic SHA-256 hash of raw input
- Transformation code version
- Data quality verification audit status (`PASS`/`FAIL`)

