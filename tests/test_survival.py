"""Tests for Kaplan-Meier Backlog Survival Analysis."""

import pytest
from analytics.survival import BacklogSurvivalAnalyzer


def test_calculate_kaplan_meier_pure_math():
    # Simple synthetic case:
    # Day 10: Event (1 resolved)
    # Day 20: Censored
    # Day 30: Event (1 resolved)
    durations = [10, 20, 30]
    events = [1, 0, 1]

    km = BacklogSurvivalAnalyzer.calculate_kaplan_meier(durations, events)
    assert km["total_cases"] == 3
    assert km["events_count"] == 2
    assert km["censored_count"] == 1
    assert km["timeline"][0] == 0
    assert km["survival_probability"][0] == 1.0

    # At t=10: 3 at risk, 1 event -> S(10) = 1 * (1 - 1/3) = 2/3 = 0.6667
    assert km["timeline"][1] == 10
    assert abs(km["survival_probability"][1] - 0.6667) < 0.001

    # At t=20: censored, so no drop in survival probability
    # At t=30: 1 at risk, 1 event -> S(30) = 0.6667 * (1 - 1/1) = 0.0
    assert km["timeline"][-1] == 30
    assert km["survival_probability"][-1] == 0.0

    # Median duration should be 30 (when S(t) drops to <= 0.50)
    assert km["median_days"] == 30
    assert "milestone_survival" in km
    assert "30_days" in km["milestone_survival"]


def test_calculate_kaplan_meier_empty():
    km = BacklogSurvivalAnalyzer.calculate_kaplan_meier([], [])
    assert km["timeline"] == []
    assert km["survival_probability"] == []
    assert km["median_days"] is None


def test_calculate_kaplan_meier_all_censored():
    durations = [50, 100, 150]
    events = [0, 0, 0]
    km = BacklogSurvivalAnalyzer.calculate_kaplan_meier(durations, events)
    assert km["total_cases"] == 3
    assert km["events_count"] == 0
    assert km["censored_count"] == 3
    assert km["median_days"] is None
    assert all(p == 1.0 for p in km["survival_probability"])

