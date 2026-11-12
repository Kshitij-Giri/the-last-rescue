"""Oracle reference (spec §1.4, §2.2): plans execute exactly, agree with exact feasibility, are bracketed by UB and
by the exhaustive macro-plan optimum on tiny instances."""

import numpy as np
import pytest

from tlr.costs import CostModel
from tlr.env import RescueEnv
from tlr.evaluate import run_episode
from tlr.mapgen import compute_statics, generate_instance, is_feasible
from tlr.oracle import OraclePolicy, exhaustive_plan_count, greedy_insertion_plan, upper_bound
from tlr.utils import deep_update, instance_seed


@pytest.mark.parametrize("mode", ["per_agent", "pooled"])
def test_oracle_plan_executes_exactly_and_matches_feasibility(cfg, mode):
    cm = CostModel.from_config(cfg)
    for k in range(25):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        for b0, H in ((4, 80), (6, 80), (10, 80), (20, 80), (40, 80), (10_000, 80),
                      (10_000, 3), (10_000, 5), (10_000, 8), (40, 6)):   # small H: the time limit binds
            env = RescueEnv(cfg, horizon=H, b_ref=40, budget_mode=mode)
            pol = OraclePolicy()
            run_episode(env, inst, b0, pol, statics=st)
            assert env.n_rescued == pol.planned_rescues                 # executed exactly as planned
            assert (env.n_rescued > 0) == is_feasible(inst, st, cm, 3, H, mode, b0)
            total = 3 * b0
            assert env.n_rescued <= upper_bound(inst, cm, total)


def test_oracle_rescues_everything_with_unlimited_resources(cfg):
    cm = CostModel.from_config(cfg)
    for k in range(10):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        plan = greedy_insertion_plan(inst, st, cm, 3, 10_000, [10**6] * 3, pooled=False)
        assert len(plan) == inst.n_victims


def test_oracle_is_bracketed_by_exhaustive_optimum_and_upper_bound(cfg):
    """On tiny instances: oracle <= exhaustive optimum (same macro-plan space) <= UB. Records the gap."""
    small = deep_update(cfg, {"env": {"grid_size": 6, "victim_density": 0.09}})   # V = 3
    cm = CostModel.from_config(small)
    gaps = []
    for k in range(40):
        inst = generate_instance(small, instance_seed("calibration", k))
        st = compute_statics(inst, cm, [1, 2])
        for b0 in (5, 8, 12):
            g = len(greedy_insertion_plan(inst, st, cm, 3, 40, [b0] * 3, pooled=False))
            opt = exhaustive_plan_count(inst, st, cm, 3, 40, [b0] * 3, pooled=False)
            ub = upper_bound(inst, cm, 3 * b0)
            assert g <= opt <= ub
            gaps.append(opt - g)
    assert np.mean(gaps) <= 0.5      # sanity: the heuristic is not far from the macro-plan optimum on tiny cases


def test_oracle_respects_horizon_exactly(cfg):
    """Corridor: victim 4 steps from the base. Rescue happens at step index 4, so it needs H >= 5 (spec §1.4)."""
    from tlr.mapgen import instance_from_ascii
    inst = instance_from_ascii(["B...l", ".....", ".....", ".....", "....."])
    for H, expected in ((4, 0), (5, 1)):
        env = RescueEnv(cfg, horizon=H, b_ref=40)
        pol = OraclePolicy()
        run_episode(env, inst, 100, pol)
        assert pol.planned_rescues == expected and env.n_rescued == expected
