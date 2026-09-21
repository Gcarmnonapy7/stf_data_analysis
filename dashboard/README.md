# 📊 Dashboards — Grafana & Superset

The **STF Transparency Platform** is designed to connect seamlessly to open-source visualization platforms like **Grafana** and **Apache Superset**.

---

## 1. Connecting Grafana to the STF Lakehouse

### Option A: DuckDB Data Source Plugin
1. Install the [Grafana DuckDB Plugin](https://github.com/VolkovLabs/volkovlabs-duckdb-datasource).
2. Point the data source path to:
   ```
   /app/data/curated/stf_warehouse.duckdb
   ```
3. Direct analytical SQL queries (e.g. from `analytics/sql/kpis.sql`) can be pasted directly into Grafana panels.

### Option B: FastAPI JSON/REST Data Source
1. Install [Infinity](https://grafana.com/grafana/plugins/yesoreyeram-infinity-datasource) or the standard JSON plugin.
2. Connect to the STF API:
   - Base URL: `http://api:8000/api/v1`
   - Endpoints:
     - `/analytics/overview` (Stat cards)
     - `/analytics/yearly-trends` (Time-series charts)
     - `/analytics/decisions-by-category` (Pie/Bar charts)
     - `/analytics/by-region` (Geomap / Choropleth)
     - `/lineage/{entity_name}` (Auditability table)

---

## 2. Connecting Apache Superset
1. Add a Database connection with DuckDB SQLAlchemy URI:
   ```
   duckdb:////absolute/path/to/data/curated/stf_warehouse.duckdb
   ```
2. Explore datasets (`fact_processes`, `fact_decisions`, `dim_date`, `dim_origin`).
