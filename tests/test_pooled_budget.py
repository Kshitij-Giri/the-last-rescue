"""Pooled-budget ablation (spec §1.5, clarification P4): spendable pool vs per-capita feature, preemption, exhaustion."""

import pytest

from tlr.costs import Action as A
from tlr.env import RescueEnv
from tlr.mapgen import instance_from_ascii

from conftest import scenario

W = A.WAIT
ROWS = [".....", ".....", "..l..", ".....", "B...l"]


def test_per_capita_bucket_zero_does_not_block_rescue(cfg):
    # n = 3, pool = 8: per-capita share floor(8/3) = 2 < c_R -> f4 = 0, yet RESCUE must be valid (3 <= 8).
    env = scenario(cfg, ROWS, starts=[(2, 2), (4, 0), (4, 0)], mode="pooled", budgets=[8])
    v = env.view(0)
    assert v.spendable == 8 and v.budget_feature_value == 2
    assert env.features(0)[3] == 0
    assert env.masks[0][A.RESCUE]
    _, _, _, _, info = env.step([A.RESCUE, W, W])
    assert env.v_rescued[0] and env.budget[0] == 5


def test_default_pool_is_n_times_b0(cfg):
    inst = instance_from_ascii(ROWS)
    env = RescueEnv(cfg, horizon=50, b_ref=40, budget_mode="pooled")
    env.reset(inst, 7)
    assert env.budget.tolist() == [21]
    assert env.view(1).budget_feature_value == 7


def test_preemption_with_rotating_priority(cfg):
    env = scenario(cfg, ROWS, starts=[(2, 2), (4, 0), (4, 0)], mode="pooled", budgets=[4])
    # t = 0: priority 0,1,2 -> agent 0 RESCUE (3) is paid, agent 1 SEARCH (2) is preempted (1 left).
    _, _, _, done, info = env.step([A.RESCUE, A.SEARCH, W])
    assert env.v_rescued[0] and info["effective_actions"].tolist() == [A.RESCUE, W, W]
    pre = [e for e in info["events"] if e["type"] == "preempted"]
    assert len(pre) == 1 and pre[0]["agent"] == 1
    assert done and info["termination"] == "exhausted"   # pool 1 < c_R, victim (4,4) remains


def test_rotation_changes_who_pays_first(cfg):
    env = scenario(cfg, ROWS, starts=[(2, 2), (4, 0), (4, 0)], mode="pooled", budgets=[4])
    env.step([W, W, W])                                      # t = 0 -> 1
    # t = 1: priority 1,2,0 -> agent 1 SEARCH (2) is paid first, agent 0 RESCUE (3) no longer fits (2 left).
    _, _, _, _, info = env.step([A.RESCUE, A.SEARCH, W])
    assert info["effective_actions"].tolist() == [W, A.SEARCH, W]
    assert not env.v_rescued[0]
    assert [e["agent"] for e in info["events"] if e["type"] == "preempted"] == [0]


def test_pooled_exhaustion_and_dormancy(cfg):
    env = scenario(cfg, ROWS, mode="pooled", budgets=[2])
    assert env.done and env.termination == "exhausted"
    env = scenario(cfg, ROWS, mode="pooled", budgets=[0])
    assert env.dormant.all()
