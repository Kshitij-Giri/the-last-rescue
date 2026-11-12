"""Transition rules, rewards and termination on hand-written scenarios with hand-computed answers (spec §1.3, §1.4, §1.6).

Reward arithmetic used below (config defaults): lambda_I = lambda_T = 1, lambda_C = 0.02,
light 1.0, heavy rescuer 0.5, heavy assister 0.5, discovery 0.1, team 1.0 per rescue.
"""

import pytest

from tlr.costs import Action as A

from conftest import rc, scenario

W = A.WAIT


def test_light_rescue_rewards_and_termination(cfg):
    env = scenario(cfg, [".....", ".....", "..l..", ".....", "B...."], starts=[(2, 2), (4, 0), (4, 0)])
    _, _, R, done, info = env.step([A.RESCUE, W, W])
    assert R[0] == pytest.approx(1.0 + 1.0 - 0.02 * 3)      # individual + team - cost = 1.94
    assert R[1] == pytest.approx(1.0) and R[2] == pytest.approx(1.0)   # team reward only, WAIT is free
    assert done and env.termination == "all_rescued" and env.n_rescued == 1
    assert [e["type"] for e in info["events"]] == ["rescue"]


def test_heavy_needs_simultaneous_rescue_and_assist(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)])
    _, _, R, done, info = env.step([A.RESCUE, A.ASSIST, W])
    assert env.v_rescued[0] and not done
    assert R[0] == pytest.approx(0.5 + 1.0 - 0.06)
    assert R[1] == pytest.approx(0.5 + 1.0 - 0.04)
    assert R[2] == pytest.approx(1.0)
    ev = [e for e in info["events"] if e["type"] == "rescue"][0]
    assert ev["heavy"] and ev["rescuers"] == [0] and ev["assisters"] == [1]


def test_heavy_rescue_alone_fails_and_cost_is_paid(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (4, 0), (4, 0)])
    _, _, R, _, info = env.step([A.RESCUE, W, W])
    assert not env.v_rescued[0] and env.budget[0] == 40 - 3
    assert R[0] == pytest.approx(-0.06)
    assert [e["type"] for e in info["events"]] == ["failed_rescue"]


def test_heavy_rescue_and_assist_in_different_steps_fail(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)])
    _, _, _, _, i1 = env.step([A.RESCUE, W, W])
    _, _, _, _, i2 = env.step([W, A.ASSIST, W])
    assert not env.v_rescued[0]
    assert [e["type"] for e in i1["events"]] == ["failed_rescue"]
    assert [e["type"] for e in i2["events"]] == ["failed_assist"]


def test_two_rescuers_on_heavy_without_assist_fail(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)])
    env.step([A.RESCUE, A.RESCUE, W])
    assert not env.v_rescued[0]


def test_three_agents_heavy_credit_split(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2)] * 3)
    _, _, R, _, _ = env.step([A.RESCUE, A.ASSIST, A.ASSIST])
    assert R[0] == pytest.approx(0.5 + 1 - 0.06)
    assert R[1] == pytest.approx(0.25 + 1 - 0.04) and R[2] == pytest.approx(0.25 + 1 - 0.04)


def test_duplicate_light_rescue(cfg):
    rows = [".....", ".....", "..l..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)])
    _, _, R, _, info = env.step([A.RESCUE, A.RESCUE, W])
    assert env.n_rescued == 1
    assert R[0] == pytest.approx(0.5 + 1 - 0.06) and R[1] == pytest.approx(0.5 + 1 - 0.06)
    dup = [e for e in info["events"] if e["type"] == "duplicate_rescue"]
    assert len(dup) == 1 and dup[0]["n_wasted"] == 1


def test_discovery_reward_first_sighting_split(cfg):
    rows = [".....", ".....", "..l..", ".....", "B...l"]
    # agent 0 at (2,0) and agent 1 at (4,2) each see (2,2) only after one move; agent 2 stays at the base.
    env = scenario(cfg, rows, starts=[(2, 0), (4, 2), (4, 0)])
    assert not env.team_seen[0]
    _, _, R, _, info = env.step([A.RIGHT, A.UP, W])
    assert R[0] == pytest.approx(0.05 - 0.02) and R[1] == pytest.approx(0.05 - 0.02)
    ev = [e for e in info["events"] if e["type"] == "first_sighting" and e["victim"] == 0]
    assert ev and ev[0]["agents"] == [0, 1]
    # a later sighting by agent 2 earns nothing
    env.step([W, W, A.UP])
    _, _, R, _, _ = env.step([W, W, A.RIGHT])   # agent 2 at (3,1): sees (2,2)
    assert R[2] == pytest.approx(-0.02)


def test_search_reveals_radius_two_and_costs_two(cfg):
    rows = ["l....", ".....", "..B..", ".....", "....h"]
    env = scenario(cfg, rows, starts=[(2, 2)] * 3)
    assert env.known[0] == {}
    _, _, R, _, info = env.step([A.SEARCH, W, W])
    assert env.budget[0] == 38
    assert set(env.known[0]) == {rc(5, 0, 0), rc(5, 4, 4)}
    assert env.known[1] == {}                       # memory is private: no sharing
    assert R[0] == pytest.approx(2 * 0.1 - 0.04)
    s = [e for e in info["events"] if e["type"] == "search"][0]
    assert len(s["footprint"]) == 25


def test_exhausted_termination(cfg):
    rows = [".....", ".....", "..B..", ".....", "....l"]
    env = scenario(cfg, rows, budgets=[3, 2, 0])
    assert not env.done
    _, _, _, done, info = env.step([A.UP, A.UP, W])      # agent 0 drops to 2: nobody can RESCUE any more
    assert done and info["termination"] == "exhausted"
    env2 = scenario(cfg, rows, budgets=[2, 2, 2])
    assert env2.done and env2.termination == "exhausted" and env2.t == 0


def test_horizon_termination_and_step_after_done(cfg):
    rows = [".....", ".....", "..B..", ".....", "....l"]
    env = scenario(cfg, rows, horizon=2)
    env.step([W, W, W])
    _, _, _, done, info = env.step([W, W, W])
    assert done and info["termination"] == "horizon" and env.t == 2
    with pytest.raises(RuntimeError):
        env.step([W, W, W])


def test_termination_order_all_rescued_before_exhausted(cfg):
    env = scenario(cfg, [".....", ".....", "..l..", ".....", "B...."], starts=[(2, 2), (4, 0), (4, 0)],
                   budgets=[3, 0, 0])
    _, _, _, done, info = env.step([A.RESCUE, W, W])     # budget hits 0 AND all victims rescued
    assert info["termination"] == "all_rescued"


def test_dormant_agent_occupies_cell_and_cannot_help(cfg):
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    env = scenario(cfg, rows, starts=[(2, 2), (2, 2), (4, 0)], budgets=[9, 0, 9])
    assert env.dormant[1]
    assert env.masks[0][A.ASSIST]          # agent 0 sees a teammate on the cell but cannot see its budget
    _, _, _, _, info = env.step([A.RESCUE, W, W])
    assert not env.v_rescued[0]            # the dormant teammate could not assist
