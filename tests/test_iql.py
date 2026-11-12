"""IQL correctness (spec §2.1): TD update by hand, terminal handling, masking, tie-breaking, epsilon schedule, dormant
skip, determinism, common-random-number map order, and learning on a trivial task."""

import numpy as np
import pytest

from tlr.costs import Action as A
from tlr.env import RescueEnv
from tlr.iql import IQLParams, IQLTeam, eval_rngs, masked_argmax, masked_max
from tlr.mapgen import compute_statics, instance_from_ascii
from tlr.costs import CostModel
from tlr.train import InstancePool, RunSpec, episode_order, train_episode, train_run

from conftest import scenario


def test_td_update_by_hand():
    team = IQLTeam(1, IQLParams(alpha=0.1, gamma=0.98), seed=0)
    team.Q[0, 7, :] = [5, 1, 1, 1, 1, 1, 9, 2]        # next observation; action 6 (9.0) is masked out below
    mask2 = np.array([1, 1, 1, 1, 1, 0, 0, 1], dtype=bool)
    td = team.update(0, 3, 2, r=1.5, o2=7, mask2=mask2, done=False)
    # target = 1.5 + 0.98 * max over VALID = 1.5 + 0.98 * 5 = 6.4; Q(3,2) was 0 -> td = 6.4, new Q = 0.64
    assert td == pytest.approx(6.4) and team.Q[0, 3, 2] == pytest.approx(0.64)
    td = team.update(0, 3, 2, r=1.5, o2=7, mask2=mask2, done=True)   # terminal: no bootstrap
    assert td == pytest.approx(1.5 - 0.64) and team.Q[0, 3, 2] == pytest.approx(0.64 + 0.1 * 0.86)


def test_masked_argmax_and_ties():
    q = np.array([3.0, 7.0, 7.0, 1.0, 9.0, 0, 0, 7.0])
    mask = np.array([1, 1, 1, 1, 0, 0, 0, 1], dtype=bool)      # the 9.0 is invalid
    picks = {masked_argmax(q, mask, np.random.default_rng(k)) for k in range(200)}
    assert picks == {1, 2, 7}                                    # uniform among valid maxima only
    assert masked_max(q, mask) == 7.0


def test_epsilon_schedule():
    p = IQLParams(episodes=1000, eps_decay_fraction=0.7)
    assert p.epsilon(0) == 1.0 and p.epsilon(700) == 0.05 and p.epsilon(999) == 0.05
    assert p.epsilon(350) == pytest.approx(0.525)


def test_epsilon_one_is_uniform_over_valid_and_zero_is_greedy():
    team = IQLTeam(1, IQLParams(), seed=3)
    mask = np.array([[1, 0, 1, 0, 1, 0, 0, 1]], dtype=bool)
    team.Q[0, 5] = [0, 0, 0, 0, 2.0, 0, 0, 0]
    counts = np.bincount([team.act([5], mask, 1.0)[0] for _ in range(4000)], minlength=8)
    assert counts[[1, 3, 5, 6]].sum() == 0 and all(abs(counts[k] / 4000 - 0.25) < 0.03 for k in (0, 2, 4, 7))
    assert all(team.act([5], mask, 0.0)[0] == 4 for _ in range(50))


def test_eval_rngs_are_common_random_numbers():
    a = [r.random() for r in eval_rngs(4000017, 3)]
    b = [r.random() for r in eval_rngs(4000017, 3)]
    c = [r.random() for r in eval_rngs(4000018, 3)]
    assert a == b and a != c


def test_episode_order_is_condition_independent():
    o1, o2 = episode_order(5, 1000, 2500), episode_order(5, 1000, 2500)
    assert np.array_equal(o1, o2) and len(o1) == 2500
    assert sorted(o1[:1000].tolist()) == list(range(1000))      # each epoch is a permutation of the pool
    assert not np.array_equal(o1, episode_order(6, 1000, 2500))


def test_dormant_agent_transitions_are_not_learned(cfg):
    inst = instance_from_ascii([".....", ".....", "..B..", ".....", "....l"])
    st = compute_statics(inst, CostModel.from_config(cfg), [1, 2])
    env = RescueEnv(cfg, horizon=5, b_ref=40)
    team = IQLTeam(3, IQLParams(), seed=0)
    # Agents 1 and 2 start with budget 0 (dormant) via the test hook; only agent 0 may update.
    obs, masks = env.reset(inst, 40, statics=st, budgets=[40, 0, 0], record=False)
    assert env.dormant.tolist() == [False, True, True]
    before = team.Q.copy()
    env_obs = obs
    while not env.done:
        dorm = env.dormant.copy()
        acts = team.act(env_obs, masks, 1.0)
        o2, m2, R, done, _ = env.step(acts)
        for i in range(3):
            if not dorm[i]:
                team.update(i, env_obs[i], acts[i], float(R[i]), o2[i], m2[i], done)
        env_obs, masks = o2, m2
    assert np.array_equal(team.Q[1], before[1]) and np.array_equal(team.Q[2], before[2])
    assert not np.array_equal(team.Q[0], before[0])


def test_training_is_deterministic(cfg):
    from tlr.mapgen import generate_instance
    from tlr.utils import instance_seed
    seeds = [instance_seed("train", k) for k in range(20)]
    tp, vp = InstancePool(cfg, seeds), InstancePool(cfg, [instance_seed("validation", k) for k in range(3)])
    spec = RunSpec("t", seed=11, b0=20, horizon=40, b_ref=64, params=IQLParams(episodes=60), checkpoint_every=30)
    q1 = train_run(cfg, spec, tp, vp)["team"].Q
    q2 = train_run(cfg, spec, tp, vp)["team"].Q
    spec3 = RunSpec("t", seed=12, b0=20, horizon=40, b_ref=64, params=IQLParams(episodes=60), checkpoint_every=30)
    q3 = train_run(cfg, spec3, tp, vp)["team"].Q
    assert np.array_equal(q1, q2) and not np.array_equal(q1, q3)


def test_iql_learns_a_trivial_rescue(cfg):
    """One light victim two steps from the base: after training, the greedy team rescues it every time."""
    inst = instance_from_ascii([".....", ".....", "B.l..", ".....", "....."])
    st = compute_statics(inst, CostModel.from_config(cfg), [1, 2])

    class Pool:
        items = [(inst, st)]

        def __len__(self):
            return 1

        def __getitem__(self, k):
            return self.items[0]

    spec = RunSpec("trivial", seed=0, b0=20, horizon=20, b_ref=64,
                   params=IQLParams(episodes=400, alpha=0.2), checkpoint_every=100)
    out = train_run(cfg, spec, Pool(), Pool())
    assert out["final"]["rf"] == 1.0
