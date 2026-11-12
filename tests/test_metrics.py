"""Metric correctness on hand-written scripted episodes with answers computed by hand (spec §3, construct validity).

Episode S1 (5x5): heavy victim h at (2,2), light victim at (4,4), base (4,0).
  A0 starts (2,0), A1 starts (0,2), A2 starts on the base.
  t0: A0 RIGHT, A1 DOWN          t1: A0 RIGHT, A1 DOWN   (both now on (2,2))
  t2: A1 ASSIST alone (wasted; A0 co-located but WAITs -> E1 = 1)
  t3: A0 RESCUE + A1 ASSIST (heavy rescued, t* = 3); A2 RIGHT
  t4..t6: A2 RIGHT x3 to (4,4)   t7: A2 RESCUE -> all rescued, 8 steps.
Hand answers:
  costs A0 = 1+1+3 = 5, A1 = 1+1+2+2 = 6, A2 = 4+3 = 7, total 18
  C1 EAR = 1 effective / 2 ASSISTs = 0.5
  C4a PSS = (3+2) + 3 = 8 / 18
  C4b Gini(5,6,7) = sum|xi-xj| / (2 n^2 mean) = 8 / (2*9*6) = 0.074074...
  C5 CR: non-WAIT = A0 3 + A1 4 + A2 5 = 12; cooperative = A0 moves t0,t1 + A1 moves t0,t1 + RESCUE + ASSIST at t3 = 6
         -> 0.5 (the wasted ASSIST at t2 is not cooperative)
  C3: U0 = {(2,0),(2,1),(2,2)}, U1 = {(0,2),(1,2),(2,2)}, U2 = {(4,1),(4,2),(4,3),(4,4)} (base excluded)
      J01 = 1/5, J02 = J12 = 0 -> TDI = 1 - (0.2/3) = 0.93333...
  C2 undefined (no SEARCH); E1 = 1; E2 = 0.
"""

import math

import numpy as np
import pytest

from tlr.baselines import make_team
from tlr.cooperation_metrics import cooperation_metrics, gini
from tlr.costs import Action as A, CostModel
from tlr.env import RescueEnv
from tlr.evaluate import run_episode
from tlr.mapgen import compute_statics, generate_instance
from tlr.metrics import coverage_from_log, e3_conflict_flags, episode_record, performance_metrics
from tlr.utils import deep_update, instance_seed

from conftest import scenario

W = A.WAIT


def _metrics(env):
    return cooperation_metrics(env.inst, env.st, env.log, env.costs)


def test_scripted_episode_S1(cfg):
    env = scenario(cfg, [".....", ".....", "..h..", ".....", "B...l"], starts=[(2, 0), (0, 2), (4, 0)])
    plan = [[A.RIGHT, A.DOWN, W], [A.RIGHT, A.DOWN, W], [W, A.ASSIST, W], [A.RESCUE, A.ASSIST, A.RIGHT],
            [W, W, A.RIGHT], [W, W, A.RIGHT], [W, W, A.RIGHT], [W, W, A.RESCUE]]
    for p in plan:
        env.step(p)
    assert env.done and env.termination == "all_rescued" and env.t == 8
    m = _metrics(env)
    assert (m["ear_num"], m["ear_den"]) == (1, 2) and m["ear"] == 0.5
    assert m["pss"] == pytest.approx(8 / 18)
    assert m["gini_consumption"] == pytest.approx(8 / 108)
    assert (m["cr_num"], m["cr_den"]) == (6, 12) and m["cr"] == 0.5
    assert m["tdi"] == pytest.approx(1 - 0.2 / 3)
    assert m["rsr_den"] == 0 and math.isnan(m["rsr"])
    assert m["e1_abandonment"] == 1 and m["e2_duplicate"] == 0
    p = performance_metrics(env.inst, env.st, env.log, 1)
    assert p["rescued"] == 2 and p["rf"] == 1.0 and p["ms"] == 1 and p["spent"] == 18
    assert p["efficiency_per100"] == pytest.approx(200 / 18)
    assert p["rescued_heavy"] == 1 and p["rescued_light"] == 1


def test_minimal_requirement_rule_with_two_assisters(cfg):
    """Heavy rescue by RESCUE + 2 ASSISTs in one step: only ONE assist is effective (P6).
    EAR = 1/2; PSS = (3+2)/(3+2+2) = 5/7; CR: non-WAIT = 3, cooperative = canonical RESCUE (A0) + canonical ASSIST (A1)
    = 2 (A2's extra ASSIST is a redundant co-action) -> 2/3."""
    env = scenario(cfg, [".....", ".....", "..h..", ".....", "B...l"], starts=[(2, 2)] * 3)
    env.step([A.RESCUE, A.ASSIST, A.ASSIST])
    m = _metrics(env)
    assert (m["ear_num"], m["ear_den"]) == (1, 2)
    assert m["pss"] == pytest.approx(5 / 7)
    assert (m["cr_num"], m["cr_den"]) == (2, 3)


def test_scripted_redundant_search(cfg):
    """S2 (7x7). Footprints: A0 at (3,1): rows1-5 x cols0-3 = 20 cells; A1 at (3,3): rows1-5 x cols1-5 = 25;
    A2 at (0,6): rows0-2 x cols4-6 = 9.
      t0 A0 SEARCH: first search                          -> not redundant
      t1 A1 SEARCH: overlap with A0 = 15/25 = 0.60        -> redundant_other
      t2 A0 SEARCH: overlap with A1 = 15/20 = 0.75        -> redundant_other (other takes precedence over self)
      t3 A2 SEARCH: overlap with others = 4/9 = 0.44      -> not redundant
      t4 A2 SEARCH: others 4/9, self 9/9                  -> redundant_self
    RSR = 3/5, RSR_other = 2/5, RSR_self = 1/5."""
    rows = [".......", ".......", ".......", ".......", ".......", ".......", "B.....l"]
    env = scenario(cfg, rows, starts=[(3, 1), (3, 3), (0, 6)])
    for p in ([A.SEARCH, W, W], [W, A.SEARCH, W], [A.SEARCH, W, W], [W, W, A.SEARCH], [W, W, A.SEARCH]):
        env.step(p)
    m = _metrics(env)
    assert m["rsr_den"] == 5 and m["rsr_other_num"] == 2 and m["rsr_self_num"] == 1
    assert m["rsr"] == pytest.approx(0.6) and m["rsr_other"] == pytest.approx(0.4)
    assert m["ear_den"] == 0 and math.isnan(m["ear"])
    assert m["cr"] == 0.0                                  # searches are never "cooperative" under C5


def test_simultaneous_identical_searches_are_redundant(cfg):
    """P6: three agents SEARCH the same footprint in the same step -> agent 0 counts as first, agents 1 and 2 are
    redundant_other (they add no information)."""
    rows = [".......", ".......", ".......", ".......", ".......", ".......", "B.....l"]
    env = scenario(cfg, rows, starts=[(3, 3)] * 3)
    env.step([A.SEARCH, A.SEARCH, A.SEARCH])
    m = _metrics(env)
    assert m["rsr_den"] == 3 and m["rsr_other_num"] == 2 and m["rsr_self_num"] == 0


def test_duplicate_light_rescue_is_not_productive(cfg):
    env = scenario(cfg, [".....", ".....", "..l..", ".....", "B...l"], starts=[(2, 2), (2, 2), (4, 0)])
    env.step([A.RESCUE, A.RESCUE, W])
    m = _metrics(env)
    assert m["e2_duplicate"] == 1
    assert m["pss"] == pytest.approx(3 / 6)                # only one RESCUE was required


def test_gini_reference_values():
    assert gini(np.array([1, 1, 1])) == 0.0
    assert gini(np.array([0, 0, 3])) == pytest.approx(2 / 3)   # maximum for n = 3 is (n-1)/n
    assert gini(np.array([0, 0, 0])) == 0.0


def test_stale_travel_diagnostic(cfg):
    rows = [".......", ".......", ".......", "...l...", ".......", ".......", "l.....B"]
    env = scenario(cfg, rows, starts=[(3, 2), (0, 3), (6, 6)])
    for p in ([A.LEFT, A.DOWN, W], [A.LEFT, A.DOWN, W], [W, A.DOWN, W], [W, A.RESCUE, W],
              [A.RIGHT, W, W], [A.RIGHT, W, W], [A.RIGHT, W, W]):
        env.step(p)
    p = performance_metrics(env.inst, env.st, env.log, 1)
    # steps 4 and 5: A0's f1 target (v0) was rescued at step 3 -> 2 stale moves; at step 6 its memory is corrected.
    assert p["stale_corrections"] == 1 and p["stale_travel_moves"] == 2 and p["stale_travel_cost"] == 2


def test_same_step_observation_is_not_stale(cfg):
    """Agent 0 stands next to a light victim that agent 1 rescues: memory updates in the same step (steps_since = 0),
    which is logged but not counted as a stale correction."""
    env = scenario(cfg, [".....", ".....", "..l..", ".....", "B...l"], starts=[(2, 1), (2, 2), (4, 0)])
    env.step([A.WAIT, A.RESCUE, A.WAIT])
    ev = [e for e in env.log.events if e["type"] == "stale_correction"]
    assert len(ev) == 1 and ev[0]["steps_since_rescue"] == 0
    assert performance_metrics(env.inst, env.st, env.log, 1)["stale_corrections"] == 0


def test_coverage_from_log_matches_env(cfg):
    cm = CostModel.from_config(cfg)
    for name in ("random", "greedy", "cooperative"):
        for k in range(5):
            inst = generate_instance(cfg, instance_seed("validation", k))
            env = RescueEnv(cfg, horizon=80, b_ref=40)
            log = run_episode(env, inst, 30, make_team(name), seed=k)
            assert coverage_from_log(log, env.st, 1) == pytest.approx(env.coverage)


def test_cooperation_metrics_are_not_reward(cfg):
    """A team that rescues only light victims has positive return yet CR = 0 (greedy, unlimited budget);
    in a p_heavy = 0 world CR is 0 for every policy."""
    for k in range(5):
        inst = generate_instance(cfg, instance_seed("validation", k))
        env = RescueEnv(cfg, horizon=150, b_ref=40)
        log = run_episode(env, inst, 10_000, make_team("greedy"), seed=k)
        rec = episode_record(inst, env.st, log, env.costs, 1)
        assert rec["collective_return"] > 0 and rec["rescued"] > 0 and rec["cr"] == 0
    c0 = deep_update(cfg, {"env": {"p_heavy": 0.0}})
    for name in ("random", "greedy", "cooperative"):
        inst = generate_instance(c0, instance_seed("validation", 0))
        env = RescueEnv(c0, horizon=150, b_ref=40)
        log = run_episode(env, inst, 10_000, make_team(name), seed=0)
        assert episode_record(inst, env.st, log, env.costs, 1)["cr"] == 0


def test_e3_flags_need_both_conditions():
    rows = [  # (agent returns, collective)
        {"return_agent0": 5.0, "return_agent1": 0.0, "collective_return": 5.0},   # best agent high, team low -> 1
        {"return_agent0": 1.0, "return_agent1": 1.0, "collective_return": 2.0},   # team low, nobody high -> 0
        {"return_agent0": 4.0, "return_agent1": 4.0, "collective_return": 8.0},   # team high -> 0
        {"return_agent0": 3.0, "return_agent1": 4.0, "collective_return": 7.0},   # team high -> 0
    ]
    # individual median = 3.5, collective median = 6.0
    assert e3_conflict_flags(rows, 2) == [1, 0, 0, 0]
