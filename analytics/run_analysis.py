"""Automated Statistical Analysis and Executive Report Generator for STF Lakehouse.

Queries the DuckDB Lakehouse and produces a documented statistical report
answering the core research questions:
- Annual case inflow & backlog accumulation
- Monocracy ratio (Monocratic vs. Collegiate decisions)
- Case duration and judicial lead time
- Geographic concentration across Brazilian states and regions
- Substantive outcome distribution
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from analytics.duckdb_client import STFLakehouseClient


def generate_executive_report(output_path: Path | str | None = None) -> str:
    """Executes analytical queries and compiles an executive markdown report."""
    client = STFLakehouseClient()
    report_lines: List[str] = []

    report_lines.append("# 🏛️ STF Transparency Platform — Executive Analytical Report")
    report_lines.append("> **Analytical Layer**: DuckDB Gold Star Schema (`stf_warehouse.duckdb`)")
    report_lines.append("> **Methodology**: Verbatim judicial statistics with non-partisan analytical aggregations.\n")

    # 1. Macro KPIs
    kpis = client.get_kpi_overview()
    report_lines.append("## 1. Executive Summary")
    report_lines.append(f"- **Total Ingested Processes**: `{kpis['total_processes']:,}`")
    report_lines.append(f"- **Total Judicial Decisions**: `{kpis['total_decisions']:,}`")
    report_lines.append(f"- **Active Cases in Tramitation (Acervo Ativo)**: `{kpis['active_processes']:,}` ({kpis['active_processes'] / max(1, kpis['total_processes']) * 100:.1f}%)")
    report_lines.append(f"- **Archived / Concluded Cases (Baixados)**: `{kpis['archived_processes']:,}` ({kpis['archived_processes'] / max(1, kpis['total_processes']) * 100:.1f}%)")
    report_lines.append(f"- **Total Interposed Appeals (Recursos)**: `{kpis['total_appeals']:,}`\n")

    # 2. Yearly Intake and Backlog Evolution
    yearly_sql = """
        SELECT 
            d.year AS ano,
            COUNT(*) AS total_processos,
            COUNT(CASE WHEN p.situacao = 'EM TRAMITAÇÃO' THEN 1 END) AS em_tramitacao,
            COUNT(CASE WHEN p.situacao = 'BAIXADO' THEN 1 END) AS baixados,
            COUNT(CASE WHEN p.situacao = 'JULGADO' THEN 1 END) AS julgados
        FROM fact_processes p
        JOIN dim_date d ON p.date_distribuicao_key = d.date_key
        GROUP BY d.year
        ORDER BY ano DESC
    """
    yearly_data = client.query(yearly_sql)
    report_lines.append("## 2. Annual Case Inflow & Backlog Dynamics")
    report_lines.append("| Year | Total Distributed | In Tramitation | Archived (Baixados) | Judged (Julgados) |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for r in yearly_data:
        report_lines.append(f"| **{r['ano']}** | {r['total_processos']:,} | {r['em_tramitacao']:,} | {r['baixados']:,} | {r['julgados']:,} |")
    report_lines.append("")

    # 3. Decision Category Dynamics (Monocrática vs Colegiada)
    dec_sql = """
        SELECT 
            categoria_decisao,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
        FROM fact_decisions
        GROUP BY categoria_decisao
        ORDER BY total DESC
    """
    dec_data = client.query(dec_sql)
    report_lines.append("## 3. Decision Profile: Monocratic vs. Collegiate Rulings")
    report_lines.append("| Category | Total Decisions | Share (%) |")
    report_lines.append("| :--- | :--- | :--- |")
    for r in dec_data:
        report_lines.append(f"| `{r['categoria_decisao']}` | {r['total']:,} | {r['percentual']}% |")
    report_lines.append("")

    # 4. Top Procedural Classes
    class_sql = """
        SELECT 
            classe_sigla,
            classe_descricao,
            COUNT(*) AS total_acoes,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
        FROM fact_processes
        GROUP BY classe_sigla, classe_descricao
        ORDER BY total_acoes DESC
        LIMIT 10
    """
    class_data = client.query(class_sql)
    report_lines.append("## 4. Top Procedural Classes (Classes Processuais)")
    report_lines.append("| Class Acronym | Full Description | Total Cases | Share (%) |")
    report_lines.append("| :--- | :--- | :--- | :--- |")
    for r in class_data:
        report_lines.append(f"| **{r['classe_sigla']}** | {r['classe_descricao']} | {r['total_acoes']:,} | {r['percentual']}% |")
    report_lines.append("")

    # 5. Geographic Case Origin Distribution
    geo_sql = """
        SELECT 
            o.regiao,
            COUNT(*) AS total_processos,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
        FROM fact_processes p
        JOIN dim_origin o ON p.uf_origem = o.uf_origem
        GROUP BY o.regiao
        ORDER BY total_processos DESC
    """
    geo_data = client.query(geo_sql)
    report_lines.append("## 5. Geographic Distribution by Brazilian Region")
    report_lines.append("| Macro-Region | Cases | Share (%) |")
    report_lines.append("| :--- | :--- | :--- |")
    for r in geo_data:
        report_lines.append(f"| **{r['regiao']}** | {r['total_processos']:,} | {r['percentual']}% |")
    report_lines.append("")

    # 6. Case Duration / Lead Time
    duration_sql = """
        SELECT 
            p.classe_sigla,
            ROUND(AVG(f.data_decisao - p.data_distribuicao), 1) AS media_dias,
            MEDIAN(f.data_decisao - p.data_distribuicao) AS mediana_dias,
            MIN(f.data_decisao - p.data_distribuicao) AS min_dias,
            MAX(f.data_decisao - p.data_distribuicao) AS max_dias
        FROM fact_decisions f
        JOIN fact_processes p ON f.process_id = p.process_id
        GROUP BY p.classe_sigla
        ORDER BY media_dias DESC
        LIMIT 10
    """
    duration_data = client.query(duration_sql)
    report_lines.append("## 6. Judicial Lead Time (Days to Decision by Class)")
    report_lines.append("| Class | Mean Days | Median Days | Min Days | Max Days |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for r in duration_data:
        report_lines.append(f"| **{r['classe_sigla']}** | {r['media_dias']} | {r['mediana_dias']} | {r['min_dias']} | {r['max_dias']} |")
    report_lines.append("")

    # 7. Decision Outcome Distribution
    outcome_sql = """
        SELECT 
            resultado,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
        FROM fact_decisions
        GROUP BY resultado
        ORDER BY total DESC
    """
    outcome_data = client.query(outcome_sql)
    report_lines.append("## 7. Decision Outcomes (Resultados do Julgamento)")
    report_lines.append("| Outcome | Total Decisions | Share (%) |")
    report_lines.append("| :--- | :--- | :--- |")
    for r in outcome_data:
        report_lines.append(f"| `{r['resultado']}` | {r['total']:,} | {r['percentual']}% |")
    report_lines.append("")

    content = "\n".join(report_lines)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(content, encoding="utf-8")

    return content


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    report_file = project_root / "analytics" / "reports" / "stf_executive_report.md"
    report_md = generate_executive_report(report_file)
    print(f"✓ Executive analytical report generated at: {report_file}")
