# 📊 Apache Superset Integration — STF Transparency Platform

This directory provides pre-configured assets, dataset declarations, and quickstart instructions for integrating the **STF Transparency Platform** lakehouse with **Apache Superset**.

---

## 🚀 Quickstart Connection

### 1. Database Connection String (DuckDB SQLAlchemy)

Apache Superset connects natively to the embedded DuckDB Lakehouse via the [`duckdb-engine`](https://github.com/Mause/duckdb_engine) driver:

```text
duckdb:////path/to/sft_data/data/curated/stf_warehouse.duckdb
```

For dockerized deployments mounting the volume at `/app/data`:
```text
duckdb:////app/data/curated/stf_warehouse.duckdb?read_only=true
```

---

## 📁 Pre-Packaged Assets

- **`stf_superset_dashboard.json`**: Pre-configured dashboard containing:
  - **Slices**:
    1. *Acervo em Tramitação vs. Baixados por Ano* (Bar Chart)
    2. *Distribuição de Caseload por Ministro Relator* (Stacked Bar)
    3. *Tempo Médio de Tramitação por Classe Processual* (Box Plot & Lead Time)
    4. *Proporção Monocrática vs. Colegiada* (Pie/Donut)
    5. *Execução Orçamentária Anual (Dotação vs. Liquidado)* (Dual Line/Bar)
  - **Datasets**:
    - `fact_processes`
    - `fact_decisions`
    - `fact_budget`
    - `fact_remuneration`
    - `dim_personnel`

---

## 📥 How to Import into Superset

1. Open Apache Superset (e.g. `http://localhost:8088`).
2. Navigate to **Settings** $\rightarrow$ **Database Connections** $\rightarrow$ **+ Database**.
3. Choose **Other** $\rightarrow$ enter SQLAlchemy URI:
   ```text
   duckdb:////app/data/curated/stf_warehouse.duckdb?read_only=true
   ```
4. Navigate to **Dashboards** $\rightarrow$ Click **Import Dashboards** (top right).
5. Upload **`dashboard/superset/stf_superset_dashboard.json`**.
6. The dashboard **"STF Analytics & Transparência"** will be instantly populated!

