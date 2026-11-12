"""Property checks over many random-policy episodes, and bit-exact determinism (spec §1 as a whole; rule 7).

Invariants checked at every step of every episode:
- budgets never negative; budget conservation: initial - current == sum of paid costs;
- agents only stand on free cells; WAIT always valid; masks never offer unaffordable actions;
- RESCUE is offered only when a waiting victim is truly on the agent's cell (mask soundness w.r.t. ground truth);
- reward decomposition R = lambda_I*r_ind + lambda_T*r_team - lambda_C*cost holds exactly;
- r_team equals the number of rescue events of the step; rescued count equals rescue events;
- termination reason is valid, t <= H, and the reason matches the state.
"""

import numpy as np
import pytest

from tlr.costs import Action
from tlr.env import RescueEnv, TERMINATION_REASONS
from tlr.mapgen import compute_statics, generate_instance
from tlr.costs import CostModel
from tlr.utils import instance_seed, make_rng, sha256_bytes

from conftest import random_valid_actions


def _run(cfg, mode, inst_idx, policy_seed, b0, H=60, statics=None, inst=None):
    inst = inst or generate_instance(cfg, instance_seed("validation", inst_idx))
    env = RescueEnv(cfg, horizon=H, b_ref=40, budget_mode=mode)
    obs, masks = env.reset(inst, b0, statics=statics)
    rng = make_rng(policy_seed)
    lam = cfg["reward"]
    init = env.budget.copy()
    spent = np.zeros_like(init)
    while not env.done:
        for i in range(env.n):
            m = masks[i]
            assert m[Action.WAIT]
            spend = env.budget[i] if mode == "per_agent" else env.budget[0]
            for a in range(4):
                if m[a]:
                    assert env.st.entry_cost[env.st.move_target[env.pos[i], a]] <= spend
            if m[Action.RESCUE]:
                vid = env.cell_to_vid[env.pos[i]]
                assert vid >= 0 and not env.v_rescued[vid]
            if m[Action.ASSIST]:
                vid = env.cell_to_vid[env.pos[i]]
                assert env.inst.victim_heavy[vid] and (np.sum(env.pos == env.pos[i]) >= 2)
        acts = random_valid_actions(masks, rng)
        obs, masks, R, done, info = env.step(acts)
        spent += info["paid"].sum() if mode == "pooled" else info["paid"]
        assert (env.budget >= 0).all()
        assert np.array_equal(init - env.budget, spent)
        assert all(env.st.free[p] for p in env.pos)
        n_resc = sum(1 for e in info["events"] if e["type"] == "rescue")
        assert info["r_team"] == pytest.approx(lam["team_per_rescue"] * n_resc)
        assert np.allclose(R, lam["lambda_I"] * info["r_ind"] + lam["lambda_T"] * info["r_team"]
                           - lam["lambda_C"] * info["paid"])
        assert all(0 <= o < 3960 for o in obs)
    assert env.termination in TERMINATION_REASONS and env.t <= H
    if env.termination == "all_rescued":
        assert env.v_rescued.all()
    elif env.termination == "exhausted":
        assert env.budget.max() < 3 and not env.v_rescued.all()
    else:
        assert env.t == H
    assert env.n_rescued == sum(1 for e in env.log.events if e["type"] == "rescue")
    return env


@pytest.mark.parametrize("mode", ["per_agent", "pooled"])
@pytest.mark.parametrize("b0", [6, 15, 40, 400])
def test_invariants_random_episodes(cfg, mode, b0):
    cm = CostModel.from_config(cfg)
    reasons = set()
    for k in range(12):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        env = _run(cfg, mode, k, policy_seed=100 + k, b0=b0, statics=st, inst=inst)
        reasons.add(env.termination)
    if b0 <= 15:
        assert "exhausted" in reasons        # scarce budgets end by exhaustion
    if b0 == 400:
        assert "horizon" in reasons          # unlimited budget + random policy -> time limit


def _log_hash(env) -> str:
    log = env.log
    parts = [np.concatenate(log.actions).tobytes(), np.concatenate(log.positions).tobytes(),
             np.concatenate(log.budgets).tobytes(), np.concatenate(log.rewards).tobytes(),
             repr(log.events).encode(), str(log.termination).encode()]
    return sha256_bytes(b"".join(parts))


def test_bit_exact_determinism(cfg):
    h1 = _log_hash(_run(cfg, "per_agent", 3, policy_seed=7, b0=40))
    h2 = _log_hash(_run(cfg, "per_agent", 3, policy_seed=7, b0=40))
    h3 = _log_hash(_run(cfg, "per_agent", 3, policy_seed=8, b0=40))
    assert h1 == h2 and h1 != h3
