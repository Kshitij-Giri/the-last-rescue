"""Options used only by the robustness blocks R1-R7: defaults leave the environment unchanged; each option does what
docs/deviations_log.md (R1-R7) says."""

import numpy as np

from tlr.env import RescueEnv
from tlr.iql import IQLParams, IQLTeam
from tlr.mapgen import instance_from_ascii
from tlr.observation import N_OBS, budget_thresholds
from tlr.train import InstancePool, RunSpec, train_episode, train_run

from conftest import rc

ROWS = [".....", ".....", "..h..", ".....", "B...l"]


def _env(cfg, **opts):
    inst = instance_from_ascii(ROWS)
    env = RescueEnv(cfg, horizon=50, b_ref=40, **opts)
    starts = [rc(5, 2, 2), rc(5, 2, 2), rc(5, 4, 0)]
    obs, _ = env.reset(inst, 13, start_positions=starts)
    return env, obs


def test_defaults_unchanged(cfg):
    env, obs = _env(cfg)
    env2, obs2 = _env(cfg, bucket_ref="b_ref", role_bit=False)
    assert obs == obs2 and env.n_obs == N_OBS
    assert env.thresholds == budget_thresholds(40, 3)


def test_bucket_thresholds_from_b0(cfg):
    env, _ = _env(cfg, bucket_ref="b0")
    assert env.thresholds == budget_thresholds(13, 3) == (3, 4, 7)
    assert env.features(0)[3] == 3          # b = 13 is the top bucket of its own scale, bucket 1 on the B_ref scale


def test_role_bit_marks_lowest_id_on_shared_cell(cfg):
    _, plain = _env(cfg)
    env, obs = _env(cfg, role_bit=True)
    assert env.n_obs == 2 * N_OBS
    assert obs[0] == plain[0] + N_OBS       # agent 0 shares the heavy-victim cell with agent 1 and has the lower id
    assert obs[1] == plain[1]               # agent 1 is not the lowest id there
    assert obs[2] == plain[2]               # agent 2 is alone


def test_partner_training_learns_one_slot(cfg):
    pool = InstancePool(cfg, [3_000_000 + k for k in range(3)])
    spec = RunSpec(name="t", seed=0, b0=20, horizon=40, b_ref=40, params=IQLParams(episodes=6), checkpoint_every=3,
                   agent_ids=[1], partner="cooperative")
    out = train_run(cfg, spec, pool, pool)
    assert out["team"].Q.shape == (1, N_OBS, 8)
    assert np.abs(out["team"].Q).sum() > 0


def test_optimistic_init_and_dormant_updates(cfg):
    pool = InstancePool(cfg, [3_000_000 + k for k in range(2)])
    base = dict(name="t", seed=0, b0=4, horizon=30, b_ref=40, params=IQLParams(episodes=2), checkpoint_every=2)
    q0 = train_run(cfg, RunSpec(**base, q_init=2.0), pool, pool)["team"].Q
    assert (q0 == 2.0).mean() > 0.99        # untouched entries keep their optimistic value
    env = RescueEnv(cfg, horizon=30, b_ref=40)
    counts = []
    for flag in (False, True):
        team = IQLTeam(3, IQLParams(), seed=0)
        n = 0
        for inst, st in pool.items * 5:      # random play: some agents reach 0 while a teammate can still rescue
            n += train_episode(env, team, inst, st, 6, 1.0, update_dormant=flag)["updates"]
        counts.append(n)
    assert counts[1] > counts[0]
