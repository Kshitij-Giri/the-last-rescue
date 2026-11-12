"""Calibration logic (spec §4): selection rules, time-to-90%, analytic formula, and a small end-to-end smoke run."""

import math

import numpy as np
import pytest

from tlr.calibration import (_time_to_fraction, analytic_bref, calibration_instances, config_variant, select_levels,
                             step1_horizon, step2_bref)
from tlr.env import EpisodeLog

SEL = {"abundant": 1.0, "moderate_target": 0.70, "scarce_target": 0.40, "critical_band": [0.10, 0.15],
       "critical_min_oracle_feasible": 0.95}
GRID = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


def test_select_levels_basic_and_tie_break():
    rf = dict(zip(GRID, [0.98, 0.90, 0.80, 0.72, 0.68, 0.50, 0.40, 0.25, 0.12, 0.05]))
    feas = {r: 1.0 for r in GRID}
    out = select_levels(rf, feas, SEL)
    assert (out["moderate"], out["scarce"], out["critical"]) == (0.7, 0.4, 0.2)
    # tie: 0.72 and 0.68 are both 0.02 from 0.70 -> larger rho (0.7) wins
    assert not out["critical_constraint_violated"]


def test_select_levels_critical_moves_up_and_reports_violation():
    rf = dict(zip(GRID, [0.98, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.25, 0.12, 0.05]))
    feas = {r: 1.0 for r in GRID}
    feas[0.2] = 0.90                                   # Critical candidate fails the 95% constraint
    out = select_levels(rf, feas, SEL)
    assert out["critical"] == 0.3 and not out["critical_constraint_violated"]
    feas[0.3] = 0.90
    out = select_levels(rf, feas, SEL)
    assert out["critical_constraint_violated"]          # nothing left below Scarce: reported, not hidden


def test_levels_strictly_decreasing():
    rf = {r: 1.0 for r in GRID}                         # degenerate flat curve
    out = select_levels(rf, {r: 1.0 for r in GRID}, SEL)
    assert out["abundant"] > out["moderate"] > out["scarce"] > out["critical"]


def test_time_to_fraction():
    log = EpisodeLog(3, "per_agent", 50, 10, None)
    log.events = [{"type": "rescue", "t": t} for t in (4, 9, 2, 7, 11, 20)]
    assert _time_to_fraction(log, 6, 0.9) == 21        # needs all 6; last rescue in step 20 -> 21 steps
    assert _time_to_fraction(log, 6, 0.5) == 8         # needs 3: steps 2, 4, 7 -> 8 steps
    log.events = log.events[:5]
    assert math.isinf(_time_to_fraction(log, 6, 0.9))


def test_analytic_formula_by_hand(cfg):
    insts = calibration_instances(cfg, 3)
    a = analytic_bref(cfg, insts)
    A, h, V = a["A_free"], a["hazard_share"], a["V"]
    expected = (2 * A / 25 + (1 + h) * (A / 5 + 0.5 * V * 5)) / 3 + V * (0.5 * 3 + 0.5 * 5) / 3
    assert a["B_ref_analytic"] == pytest.approx(expected)


def test_small_end_to_end_smoke(cfg):
    cal = {"h_max_factor": 40, "unlimited_budget": 10**6, "rescue_fraction_target": 0.9, "time_slack": 0.7,
           "quantile": 0.9, "quantile_method": "higher"}
    insts = calibration_instances(cfg, 6)
    s1 = step1_horizon(cfg, insts, cal)
    assert s1["H"] == math.ceil(s1["T90"] / 0.7) and s1["T90"] in s1["T"]   # "higher" returns an observed value
    s2 = step2_bref(cfg, insts, cal, s1["H"])
    assert s2["B_ref"] in s2["consumption"]
    assert s2["share_reaching_90pct_within_H"] >= 0.8   # at least 5 of 6 by construction of the 90th percentile


def test_config_variant(cfg):
    c = config_variant(cfg, 12, 0.04, 0.0)
    assert c["env"]["grid_size"] == 12 and c["env"]["p_heavy"] == 0.0 and cfg["env"]["grid_size"] == 10
