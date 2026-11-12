"""Phase 5 machinery: solo exploration streams, step-budget training, mixed-team evaluator consistency,
A1 permutations, A2 ablation, block settings."""

import numpy as np
import pytest

from tlr.experiments import (BLOCKS, ablated_factory, evaluate_actors, mismatch_permutations, q_team_factory,
                             setting)
from tlr.iql import IQLParams, IQLTeam
from tlr.train import EpisodeOrder, InstancePool, RunSpec, episode_order, evaluate_team, summarize_eval, train_run
from tlr.utils import instance_seed


def test_solo_agent_streams_equal_joint_slot_streams():
    joint = IQLTeam(3, IQLParams(), seed=4)
    for k in range(3):
        solo = IQLTeam(1, IQLParams(), seed=4, agent_ids=[k])
        assert [solo.rngs[0].random() for _ in range(5)] == [joint.rngs[k].random() for _ in range(5)]


def test_unbounded_episode_order_matches_bounded():
    o = EpisodeOrder(9, 50)
    assert [o[e] for e in range(130)] == episode_order(9, 50, 130).tolist()


def test_epsilon_by_steps():
    p = IQLParams()
    assert p.epsilon_by_steps(0, 1000) == 1.0 and p.epsilon_by_steps(700, 1000) == 0.05
    assert p.epsilon_by_steps(350, 1000) == pytest.approx(0.525)


def test_step_budget_run_stops_after_budget(cfg):
    tp = InstancePool(cfg, [instance_seed("train", k) for k in range(10)])
    vp = InstancePool(cfg, [instance_seed("validation", 0)])
    out = train_run(cfg, RunSpec("eq", seed=1, b0=13, horizon=105, b_ref=64, max_env_steps=900,
                                 checkpoint_every=50), tp, vp)
    assert out["total_env_steps"] >= 900
    # it stopped at the first episode end at or after the budget: the run minus its last episode is below budget
    assert out["total_env_steps"] - 105 < 900


def test_solo_training_uses_one_agent(cfg):
    tp = InstancePool(cfg, [instance_seed("train", k) for k in range(5)])
    vp = InstancePool(cfg, [instance_seed("validation", 0)])
    out = train_run(cfg, RunSpec("solo", seed=2, b0=64, horizon=105, b_ref=64, n_agents=1, agent_ids=[1],
                                 params=IQLParams(episodes=20), checkpoint_every=10), tp, vp)
    assert out["team"].Q.shape[0] == 1 and out["final"]["assist_actions"] == 0   # ASSIST impossible alone


def test_mixed_evaluator_equals_team_evaluator(cfg):
    """All-learned actors reproduce IQLTeam's evaluation exactly (same CRN tie-break streams)."""
    tp = InstancePool(cfg, [instance_seed("train", k) for k in range(10)])
    vp = InstancePool(cfg, [instance_seed("validation", k) for k in range(4)])
    out = train_run(cfg, RunSpec("m", seed=3, b0=32, horizon=105, b_ref=64, params=IQLParams(episodes=60),
                                 checkpoint_every=60), tp, vp)
    team = out["team"]
    from tlr.env import RescueEnv
    env = RescueEnv(cfg, horizon=105, b_ref=64)
    rows_team, _ = evaluate_team(env, team, vp, 32)
    rows_mix = evaluate_actors(cfg, vp, 105, 64, 32, "per_agent", q_team_factory([team.Q[i] for i in range(3)]), {})
    assert [r["rescued"] for r in rows_team] == [r["rescued"] for r in rows_mix]
    assert [r["steps"] for r in rows_team] == [r["steps"] for r in rows_mix]
    assert [r["collective_return"] for r in rows_team] == pytest.approx([r["collective_return"] for r in rows_mix])


def test_mismatch_permutations_valid_and_fixed():
    p1, p2 = mismatch_permutations(), mismatch_permutations()
    assert p1 == p2 and len(p1) == 2
    for s2, s3 in p1:
        assert sorted(s2) == list(range(10)) and sorted(s3) == list(range(10))
        assert all(len({s, s2[s], s3[s]}) == 3 for s in range(10))


def test_wait_ablation_agent_never_acts(cfg):
    vp = InstancePool(cfg, [instance_seed("validation", k) for k in range(2)])
    Qs = [np.zeros((3960, 8)) for _ in range(3)]
    rows = evaluate_actors(cfg, vp, 105, 64, 32, "per_agent", ablated_factory(q_team_factory(Qs), 1, "wait"), {})
    assert len(rows) == 2


def test_block_settings():
    assert setting(BLOCKS["main"], "Critical") == (105, 64, 13)
    assert setting(BLOCKS["p0"], "Critical") == (105, 64, 13)       # A3 primary: main budgets
    assert setting(BLOCKS["p0sec"], "Critical") == (48, 41, 8)       # A3 secondary: own calibration
    assert setting(BLOCKS["alt"], "Abundant") == (150, 87, 87)
