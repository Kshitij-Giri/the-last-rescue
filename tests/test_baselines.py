"""Baseline policies (spec §2.2): decentralization, rule behaviour on scripted scenarios, determinism."""

import numpy as np
import pytest

from tlr.baselines import (CooperativeController, GreedyController, StaticContext, make_team, sector_partition)
from tlr.costs import Action as A, CostModel
from tlr.env import RescueEnv
from tlr.evaluate import run_episode
from tlr.mapgen import compute_statics, generate_instance, instance_from_ascii
from tlr.utils import instance_seed

from conftest import rc, scenario


def _ctx(env):
    return StaticContext.from_env(env)


@pytest.mark.parametrize("name", ["random", "greedy", "cooperative"])
def test_baselines_run_respect_masks_and_are_deterministic(cfg, name):
    """run_episode would raise InvalidActionError on any masked action; repeated runs must be identical."""
    for b0 in (10, 40, 10_000):
        for k in range(8):
            inst = generate_instance(cfg, instance_seed("validation", k))
            env = RescueEnv(cfg, horizon=150, b_ref=40)
            l1 = run_episode(env, inst, b0, make_team(name), seed=k)
            a1 = np.concatenate(l1.actions) if l1.actions else np.array([])
            l2 = run_episode(env, inst, b0, make_team(name), seed=k)
            a2 = np.concatenate(l2.actions) if l2.actions else np.array([])
            assert np.array_equal(a1, a2)


def test_greedy_never_assists_and_prefers_light(cfg):
    for k in range(10):
        inst = generate_instance(cfg, instance_seed("validation", k))
        env = RescueEnv(cfg, horizon=150, b_ref=40)
        log = run_episode(env, inst, 10_000, make_team("greedy"), seed=k)
        assert not any((a == A.ASSIST).any() for a in log.effective_actions)
        assert not any(e["type"] == "rescue" and e["heavy"] for e in log.events)
    # Equal cost to a light (left) and a heavy (right) victim: greedy goes LEFT.
    env = scenario(cfg, [".....", ".....", "l.B.h", ".....", "....."], starts=[(2, 2)] * 3)
    env.step([A.SEARCH, A.WAIT, A.WAIT])  # reveal both (radius 2)
    g = GreedyController(0, _ctx(env), 0)
    assert g.act(env.view(0), env.masks[0]) == A.LEFT


def test_greedy_attempts_heavy_at_most_once(cfg):
    env = scenario(cfg, [".....", ".....", "..h..", ".....", "B...."], starts=[(2, 2), (4, 0), (4, 0)])
    g = GreedyController(0, _ctx(env), 0)
    assert g.act(env.view(0), env.masks[0]) == A.RESCUE
    env.step([A.RESCUE, A.WAIT, A.WAIT])                 # fails (no assist)
    assert g.act(env.view(0), env.masks[0]) != A.RESCUE  # never retried


def test_sector_partition_is_deterministic_and_covers_free_cells(cfg):
    cm = CostModel.from_config(cfg)
    for k in range(10):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        s1, s2 = sector_partition(st, 3), sector_partition(st, 3)
        assert np.array_equal(s1, s2)
        assert set(s1[st.free].tolist()) == {0, 1, 2}         # every sector non-empty
        assert (s1[~st.free] == -1).all() and (s1[st.free] >= 0).all()


def test_cooperative_role_convention_completes_heavy_rescue(cfg):
    env = scenario(cfg, [".....", ".....", "..h..", ".....", "B...l"], starts=[(2, 2), (2, 2), (4, 0)])
    ctx = _ctx(env)
    c0, c1 = CooperativeController(0, ctx, 0), CooperativeController(1, ctx, 0)
    a0, a1 = c0.act(env.view(0), env.masks[0]), c1.act(env.view(1), env.masks[1])
    assert (a0, a1) == (A.RESCUE, A.ASSIST)                 # lower index RESCUEs
    env.step([a0, a1, A.WAIT])
    assert env.v_rescued[0]


def test_cooperative_waits_then_helper_comes(cfg):
    """Agent 0 waits on a heavy victim; agent 1 (within r_tm) sees it stationary and comes; they rescue together."""
    rows = [".......", ".......", ".......", "...h...", ".......", ".......", "B.....l"]
    env = scenario(cfg, rows, starts=[(3, 3), (3, 0), (6, 0)])
    team = make_team("cooperative")
    team.begin_episode(_ctx(env), 0)
    for _ in range(12):
        if env.v_rescued[0]:
            break
        acts = team.act([env.view(i) for i in range(3)], env.masks)
        if not env.v_rescued[0] and env.pos[0] == rc(7, 3, 3) and np.sum(env.pos == env.pos[0]) == 1:
            assert acts[0] == A.WAIT                      # waits alone on the heavy victim
        env.step(acts)
    ev = [e for e in env.log.events if e["type"] == "rescue" and e["heavy"]]
    assert ev and ev[0]["rescuers"] == [0] and ev[0]["assisters"] == [1]


def test_cooperative_wait_timeout(cfg):
    rows = [".......", ".......", ".......", "...h...", ".......", ".......", "B.....l"]
    env = scenario(cfg, rows, starts=[(3, 3), (6, 0), (6, 0)])     # nobody within r_tm of agent 0
    c0 = CooperativeController(0, _ctx(env), 0)
    acts = []
    for _ in range(2 * 7 + 2):
        a = c0.act(env.view(0), env.masks[0])
        acts.append(a)
        env.step([a, A.WAIT, A.WAIT])
    assert acts[:14] == [A.WAIT] * 14 and acts[14] != A.WAIT   # W = 2L = 14 waits, then it moves on


def test_controllers_are_decentralized(cfg):
    """Same view + mask -> same action, whatever happens outside the agent's view."""
    ra = ["B......", ".......", ".......", ".......", ".......", ".......", "l.....h"]
    rb = ["B......", ".......", ".......", ".......", ".......", ".......", "l......"]
    for name in ("greedy", "cooperative"):
        ea = scenario(cfg, ra, starts=[(0, 0), (6, 6), (6, 5)])
        eb = scenario(cfg, rb, starts=[(0, 0), (6, 6), (6, 5)])
        ta, tb = make_team(name), make_team(name)
        ta.begin_episode(_ctx(ea), 0)
        tb.begin_episode(_ctx(eb), 0)
        for _ in range(4):
            aa = ta.act([ea.view(i) for i in range(3)], ea.masks)
            ab = tb.act([eb.view(i) for i in range(3)], eb.masks)
            assert aa[0] == ab[0]
            ea.step([aa[0], A.WAIT, A.WAIT])
            eb.step([ab[0], A.WAIT, A.WAIT])


def test_views_cannot_modify_environment(cfg):
    env = scenario(cfg, [".....", ".....", "..l..", ".....", "B...."], starts=[(2, 2), (4, 0), (4, 0)])
    v = env.view(0)
    with pytest.raises(ValueError):
        v.observed[0] = True
    v.known.clear()
    assert env.known[0]                                    # env memory untouched


def test_cooperative_colocated_agents_do_not_search_together(cfg):
    """D19/P7: at t = 0 all agents share the base; only the lowest index SEARCHes."""
    env = scenario(cfg, [".......", ".......", ".......", "...B...", ".......", ".......", "......l"])
    team = make_team("cooperative")
    team.begin_episode(_ctx(env), 0)
    acts = team.act([env.view(i) for i in range(3)], env.masks)
    assert acts[0] == A.SEARCH and acts[1] != A.SEARCH and acts[2] != A.SEARCH
