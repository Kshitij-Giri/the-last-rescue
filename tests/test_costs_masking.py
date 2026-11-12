"""Costs, masking, dormancy and invalid-action handling (spec §1.2, §1.3a item 5, §1.4)."""

import numpy as np
import pytest

from tlr.costs import Action, CostModel
from tlr.env import InvalidActionError
from tlr.utils import deep_update, initial_budget

from conftest import rc, scenario

# Every scenario map contains at least one victim: a map with no waiting victim ends at reset ("all_rescued").
OPEN5 = [".....", ".....", "..B..", ".....", "....l"]


def test_cost_model_validation(cfg):
    cm = CostModel.from_config(cfg)
    assert (cm.move, cm.move_hazard, cm.search, cm.rescue, cm.assist, cm.wait) == (1, 2, 2, 3, 2, 0)
    assert cm.c_min == 1
    with pytest.raises(ValueError):
        CostModel.from_config(deep_update(cfg, {"costs": {"wait": 1}}))
    with pytest.raises(ValueError):
        CostModel.from_config(deep_update(cfg, {"costs": {"search": 0}}))


def test_initial_budget_round_half_up():
    assert initial_budget(0.5, 5) == 3          # 2.5 -> 3 (banker's rounding would give 2)
    assert initial_budget(0.7, 40) == 28        # 28.000000000000004 -> 28
    assert initial_budget(0.35, 20) == 7        # 6.999999999999999 -> 7
    assert initial_budget(1.0, 37) == 37
    with pytest.raises(ValueError):
        initial_budget(0.0, 40)


def test_walls_and_grid_edges_are_masked(cfg):
    env = scenario(cfg, ["B#...", ".....", ".....", ".....", "....l"], starts=[(0, 0)] * 3)
    m = env.masks[0]
    assert not m[Action.UP] and not m[Action.LEFT]     # off-grid
    assert not m[Action.RIGHT]                          # wall
    assert m[Action.DOWN] and m[Action.WAIT] and m[Action.SEARCH]
    assert not m[Action.RESCUE] and not m[Action.ASSIST]


def test_hazard_move_needs_two_units(cfg):
    env = scenario(cfg, [".....", ".....", ".~B..", ".....", "....l"], starts=[(2, 2)] * 3, budgets=[1, 2, 3])
    assert not env.masks[0][Action.LEFT] and env.masks[0][Action.RIGHT]   # budget 1: hazard unaffordable
    assert not env.masks[0][Action.SEARCH]                                # SEARCH costs 2
    assert env.masks[1][Action.LEFT] and env.masks[1][Action.SEARCH]
    obs, masks, R, done, info = env.step([Action.RIGHT, Action.LEFT, Action.WAIT])
    assert list(info["paid"]) == [1, 2, 0]
    assert list(env.budget) == [0, 0, 3]


def test_dormant_agent_can_only_wait(cfg):
    env = scenario(cfg, OPEN5, budgets=[0, 5, 5])
    assert env.dormant[0]
    assert env.masks[0].tolist() == [False] * 7 + [True]
    assert not env.done            # others can still rescue


def test_rescue_and_assist_preconditions(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    # agent 0 alone on the heavy victim; agent 1 on the light victim; agent 2 at base
    env = scenario(cfg, rows, starts=[(2, 2), (4, 4), (4, 0)])
    m0, m1, m2 = env.masks
    assert m0[Action.RESCUE] and not m0[Action.ASSIST]     # no teammate on the cell -> ASSIST masked
    assert m1[Action.RESCUE] and not m1[Action.ASSIST]     # light victim -> ASSIST never valid
    assert not m2[Action.RESCUE] and not m2[Action.ASSIST]
    env2 = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)])
    assert env2.masks[0][Action.ASSIST] and env2.masks[1][Action.ASSIST]
    env3 = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)], budgets=[2, 1, 9])
    assert not env3.masks[0][Action.RESCUE] and env3.masks[0][Action.ASSIST]   # 2 units: ASSIST yes, RESCUE no
    assert not env3.masks[1][Action.ASSIST]


def test_wait_always_valid_and_masks_sound(cfg):
    env = scenario(cfg, OPEN5, budgets=[0, 0, 3])
    assert env.masks[:, Action.WAIT].all()


def test_invalid_action_raises_and_does_not_change_state(cfg):
    env = scenario(cfg, ["B#...", ".....", ".....", ".....", "....l"], starts=[(0, 0)] * 3)
    before = (env.pos.copy(), env.budget.copy(), env.t)
    with pytest.raises(InvalidActionError):
        env.step([Action.RIGHT, Action.WAIT, Action.WAIT])   # into a wall
    with pytest.raises(InvalidActionError):
        env.step([Action.RESCUE, Action.WAIT, Action.WAIT])  # no victim
    with pytest.raises(InvalidActionError):
        env.step([9, Action.WAIT, Action.WAIT])              # not an action
    assert np.array_equal(env.pos, before[0]) and np.array_equal(env.budget, before[1]) and env.t == before[2]
