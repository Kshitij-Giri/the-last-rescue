"""Exact instance feasibility (spec §1.4) on hand-checked corridors, and agreement with the environment."""

import numpy as np

from tlr.costs import Action as A, CostModel
from tlr.env import RescueEnv
from tlr.mapgen import compute_statics, feasible_victims, instance_from_ascii, is_feasible


def _setup(cfg, rows):
    cm = CostModel.from_config(cfg)
    inst = instance_from_ascii(rows)
    return inst, compute_statics(inst, cm, [1, 2]), cm


def test_light_victim_budget_and_time(cfg):
    inst, st, cm = _setup(cfg, ["B...l", ".....", ".....", ".....", "....."])
    # d(base, victim) = 4, steps = 4: need b0 >= 4 + 3 and H >= 5.
    assert is_feasible(inst, st, cm, 3, 50, "per_agent", 7)
    assert not is_feasible(inst, st, cm, 3, 50, "per_agent", 6)
    assert is_feasible(inst, st, cm, 3, 5, "per_agent", 7)
    assert not is_feasible(inst, st, cm, 3, 4, "per_agent", 7)
    # pooled: one agent may use the whole pool n*b0
    assert is_feasible(inst, st, cm, 3, 50, "pooled", 3)       # pool 9 >= 7
    assert not is_feasible(inst, st, cm, 3, 50, "pooled", 2)   # pool 6 < 7


def test_hazard_raises_path_cost(cfg):
    inst, st, cm = _setup(cfg, ["B...L", ".....", ".....", ".....", "....."])
    assert st.dist[inst.base, inst.victim_cells[0]] == 5
    assert not is_feasible(inst, st, cm, 3, 50, "per_agent", 7)
    assert is_feasible(inst, st, cm, 3, 50, "per_agent", 8)


def test_heavy_victim_needs_two_agents(cfg):
    inst, st, cm = _setup(cfg, ["B...h", ".....", ".....", ".....", "....."])
    assert not is_feasible(inst, st, cm, 1, 50, "per_agent", 100)
    assert is_feasible(inst, st, cm, 2, 50, "per_agent", 7)    # d + max(c_R, c_A) = 7
    assert not is_feasible(inst, st, cm, 2, 50, "per_agent", 6)
    assert not is_feasible(inst, st, cm, 3, 50, "pooled", 4)   # 2d + c_R + c_A = 13 > 12
    assert is_feasible(inst, st, cm, 3, 50, "pooled", 5)       # 15 >= 13


def test_feasibility_boundary_is_achievable_in_env(cfg):
    """At the exact feasibility boundary, a scripted plan really rescues the victim (the check is not optimistic)."""
    inst, st, cm = _setup(cfg, ["B...h", ".....", ".....", ".....", "....."])
    assert feasible_victims(inst, st, cm, 3, 50, "per_agent", 7).tolist() == [True]
    env = RescueEnv(cfg, horizon=5, b_ref=40)
    env.reset(inst, 7, statics=st)
    for _ in range(4):
        env.step([A.RIGHT, A.RIGHT, A.WAIT])
    _, _, _, done, _ = env.step([A.RESCUE, A.ASSIST, A.WAIT])
    assert env.v_rescued[0] and done and env.t == 5
    assert env.budget.tolist() == [0, 1, 7]
