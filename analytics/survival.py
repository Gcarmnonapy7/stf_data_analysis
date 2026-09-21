"""Temporal Survival Analysis Engine for Judicial Process Backlog.

Implements the non-parametric Kaplan-Meier estimator for time-to-disposition:
    S(t) = ∏_{t_i ≤ t} (1 - d_i / n_i)

Where:
- Event (E = 1): Case disposed / resolved (BAIXADO or JULGADO).
- Censored (E = 0): Case active / pending in backlog (EM TRAMITAÇÃO).
- Duration (T): Calendar days from distribution to disposition or censoring date.

Provides:
- Overall backlog survival curve.
- Median backlog duration (backlog half-life).
- Stratification by Procedural Class (HC, RE, ARE, ADI, Rcl).
- Stratification by Reporting Justice (Ministro Relator).
- Survival rates at standard milestones (30, 90, 180, 365, 730, 1825 days).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import polars as pl


class BacklogSurvivalAnalyzer:
    """Computes Kaplan-Meier survival curves and duration statistics for court backlogs."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        project_root = Path(__file__).resolve().parent.parent
        self.db_path = (
            Path(db_path)
            if db_path
            else project_root / "data" / "curated" / "stf_warehouse.duckdb"
        )
        self.reference_date = date(2026, 12, 31)

    def _extract_dataset(self) -> pl.DataFrame:
        """Extracts processes and decision durations from DuckDB lakehouse."""
        con = duckdb.connect(str(self.db_path), read_only=True)
        query = """
            SELECT 
                p.process_id,
                p.classe_sigla,
                p.relator,
                p.situacao,
                p.data_distribuicao,
                COALESCE(
                    (SELECT MIN(d.data_decisao) FROM fact_decisions d WHERE d.process_id = p.process_id),
                    p.data_distribuicao
                ) AS data_evento
            FROM fact_processes p
            WHERE p.data_distribuicao IS NOT NULL
        """
        df = con.execute(query).pl()
        con.close()

        # Compute duration and event indicator
        durations = []
        events = []

        for row in df.iter_rows(named=True):
            dist_date = row["data_distribuicao"]
            if isinstance(dist_date, str):
                dist_date = date.fromisoformat(dist_date)

            situacao = (row["situacao"] or "").upper()
            is_event = situacao in ("BAIXADO", "JULGADO")

            if is_event:
                event_date = row["data_evento"]
                if isinstance(event_date, str):
                    event_date = date.fromisoformat(event_date)
                duration = max(1, (event_date - dist_date).days)
                event_flag = 1
            else:
                # Censored observation
                duration = max(1, (self.reference_date - dist_date).days)
                event_flag = 0

            durations.append(duration)
            events.append(event_flag)

        df = df.with_columns([
            pl.Series("duration_days", durations, dtype=pl.Int64),
            pl.Series("event", events, dtype=pl.Int32),
        ])

        return df

    @staticmethod
    def calculate_kaplan_meier(
        durations: List[int],
        events: List[int],
        max_points: int = 40,
    ) -> Dict[str, Any]:
        """Calculates step-wise Kaplan-Meier survival probabilities."""
        if not durations:
            return {"timeline": [], "survival_probability": [], "median_days": None}

        pairs = sorted(zip(durations, events), key=lambda x: x[0])
        total_subjects = len(pairs)

        unique_times = sorted(list(set(d for d, e in pairs if e == 1)))
        if not unique_times:
            # All censored
            return {
                "timeline": [0, max(durations)],
                "survival_probability": [1.0, 1.0],
                "median_days": None,
                "total_cases": total_subjects,
                "events_count": 0,
                "censored_count": total_subjects,
                "milestone_survival": {f"{m}_days": 1.0 for m in [30, 90, 180, 365, 730, 1825]},
            }

        at_risk = total_subjects
        current_survival = 1.0

        timeline = [0]
        survival_probs = [1.0]
        events_at_time = {}
        censored_at_time = {}

        for d, e in pairs:
            if e == 1:
                events_at_time[d] = events_at_time.get(d, 0) + 1
            else:
                censored_at_time[d] = censored_at_time.get(d, 0) + 1

        all_distinct_times = sorted(list(set(durations)))
        median_days = None

        for t in all_distinct_times:
            d_i = events_at_time.get(t, 0)
            c_i = censored_at_time.get(t, 0)

            if at_risk > 0 and d_i > 0:
                current_survival *= (1.0 - (d_i / at_risk))
                timeline.append(t)
                survival_probs.append(round(current_survival, 4))

                if median_days is None and current_survival <= 0.50:
                    median_days = t

            at_risk -= (d_i + c_i)

        # Milestone survival probabilities
        milestones = [30, 90, 180, 365, 730, 1825]
        milestone_probs = {}
        for m in milestones:
            # Find survival probability at milestone m
            prob = 1.0
            for t_val, s_val in zip(timeline, survival_probs):
                if t_val <= m:
                    prob = s_val
                else:
                    break
            milestone_probs[f"{m}_days"] = prob

        # Subsample timeline for frontend visualization if too many points
        if len(timeline) > max_points:
            step = len(timeline) // max_points
            sampled_timeline = timeline[::step]
            sampled_probs = survival_probs[::step]
            if timeline[-1] not in sampled_timeline:
                sampled_timeline.append(timeline[-1])
                sampled_probs.append(survival_probs[-1])
            timeline = sampled_timeline
            survival_probs = sampled_probs

        return {
            "timeline": timeline,
            "survival_probability": survival_probs,
            "median_days": median_days,
            "total_cases": total_subjects,
            "events_count": sum(events),
            "censored_count": total_subjects - sum(events),
            "milestone_survival": milestone_probs,
        }

    def compute_survival_overview(self) -> Dict[str, Any]:
        """Calculates global and stratified survival analytics."""
        df = self._extract_dataset()
        durations = df["duration_days"].to_list()
        events = df["event"].to_list()

        # 1. Global STF survival curve
        global_km = self.calculate_kaplan_meier(durations, events)

        # 2. Stratified by Legal Class (Top 5 classes)
        classes_data = {}
        top_classes = (
            df.group_by("classe_sigla")
            .len()
            .sort("len", descending=True)
            .limit(5)["classe_sigla"]
            .to_list()
        )
        for cls in top_classes:
            sub = df.filter(pl.col("classe_sigla") == cls)
            km_cls = self.calculate_kaplan_meier(
                sub["duration_days"].to_list(),
                sub["event"].to_list(),
                max_points=20,
            )
            classes_data[cls] = km_cls

        # 3. Stratified by Reporting Justice (Ministro Relator)
        judges_data = {}
        top_judges = (
            df.group_by("relator")
            .len()
            .sort("len", descending=True)
            .limit(11)["relator"]
            .to_list()
        )
        for j in top_judges:
            if not j:
                continue
            sub = df.filter(pl.col("relator") == j)
            km_j = self.calculate_kaplan_meier(
                sub["duration_days"].to_list(),
                sub["event"].to_list(),
                max_points=15,
            )
            short_name = j.replace("Min. ", "")
            judges_data[short_name] = {
                "median_days": km_j["median_days"],
                "total_cases": km_j["total_cases"],
                "one_year_retention_pct": round(km_j["milestone_survival"].get("365_days", 1.0) * 100, 1),
            }

        return {
            "global": global_km,
            "stratified_by_class": classes_data,
            "stratified_by_judge": judges_data,
        }


if __name__ == "__main__":
    analyzer = BacklogSurvivalAnalyzer()
    res = analyzer.compute_survival_overview()
    print("Kaplan-Meier Backlog Analysis:")
    print(f"- Total Cases: {res['global']['total_cases']}")
    print(f"- Disposed Events: {res['global']['events_count']}")
    print(f"- Active (Censored): {res['global']['censored_count']}")
    print(f"- Median Survival (Backlog Half-Life): {res['global']['median_days']} days")
    print(f"- 1-Year Survival Probability: {res['global']['milestone_survival']['365_days']:.2%}")
