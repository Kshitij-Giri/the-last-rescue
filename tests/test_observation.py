"""Observation features, the f4 budget-bucket rule, encoding, and the no-hidden-information property (spec §1.7, §1.3a)."""

import itertools

import numpy as np
import pytest

from tlr.costs import Action
from tlr.observation import (N_OBS, budget_bucket, budget_thresholds, decode, encode, time_bucket)

from conftest import rc, scenario


@pytest.mark.parametrize("b_ref,expected", [(40, (3, 10, 20)), (41, (3, 11, 21)), (16, (3, 4, 8)),
                                            (12, (3, 4, 6)), (8, (3, 4, 5)), (1, (3, 4, 5)), (100, (3, 25, 50))])
def test_budget_thresholds(b_ref, expected):
    assert budget_thresholds(b_ref, 3) == expected


@pytest.mark.parametrize("b_ref", list(range(1, 130)))
def test_budget_buckets_exclusive_exhaustive_ordered(b_ref):
    th = budget_thresholds(b_ref, 3)
    assert th[0] < th[1] < th[2]                           # strictly increasing -> no empty or reversed bucket
    prev = 0
    for b in range(0, 3 * b_ref + 10):
        k = budget_bucket(b, th)
        assert k in (0, 1, 2, 3)                           # exhaustive: every integer b >= 0 gets a bucket
        assert k >= prev                                   # monotone
        prev = k
        # exclusive + half-open: membership test on each interval holds for exactly one bucket
        intervals = [(0, th[0]), (th[0], th[1]), (th[1], th[2]), (th[2], 10**9)]
        assert sum(lo <= b < hi for lo, hi in intervals) == 1 and intervals[k][0] <= b < intervals[k][1]
    for j, tau in enumerate(th):                           # boundary values belong to the UPPER bucket
        assert budget_bucket(tau - 1, th) == j and budget_bucket(tau, th) == j + 1
    if b_ref >= 16:                                        # integer thresholds equal the intended real cut points
        for b in range(0, 2 * b_ref):
            assert (b >= th[1]) == (b >= 0.25 * b_ref) and (b >= th[2]) == (b >= 0.5 * b_ref)
    with pytest.raises(ValueError):
        budget_bucket(-1, th)


def test_time_bucket_boundaries():
    assert [time_bucket(t, 100) for t in (0, 33, 34, 66, 67, 99)] == [0, 0, 1, 1, 2, 2]
    assert [time_bucket(t, 90) for t in (29, 30, 59, 60)] == [0, 1, 1, 2]


def test_encode_decode_bijection():
    seen = set()
    for f in itertools.product(range(11), range(5), range(6), range(4), range(3)):
        o = encode(f)
        assert 0 <= o < N_OBS and decode(o) == f
        seen.add(o)
    assert len(seen) == N_OBS == 3960


def test_f1_here_near_far_and_f3(cfg):
    rows = ["B......", ".......", ".......", "...h...", ".......", ".......", "......l"]
    env = scenario(cfg, rows, starts=[(3, 3), (4, 4), (0, 0)])
    f = env.features(0)
    assert f[0] == 2                               # here-HEAVY
    assert f[2] == 3                               # teammate at (+1,+1): tie -> vertical -> DOWN (2 + 1)
    g = env.features(1)
    assert g[0] == 3 + 2 * 0 + 0                   # victim one step UP, near
    assert g[2] == 2 + 0                           # nearest teammate (agent 0) is UP
    assert env.features(2)[2] == 3                 # agent 0 at Chebyshev distance exactly 3 = r_tm: in range (inclusive)
    # A remembered victim 4 steps away is "far": agent 1 walks away 3 steps DOWN... use agent 0 instead.
    env.step([Action.UP, Action.WAIT, Action.WAIT])        # (2,3): victim 1 step DOWN
    env.step([Action.UP, Action.WAIT, Action.WAIT])        # (1,3)
    env.step([Action.UP, Action.WAIT, Action.WAIT])        # (0,3): 3 steps -> near
    assert env.features(0)[0] == 3 + 2 * 1 + 0
    env.step([Action.LEFT, Action.WAIT, Action.WAIT])      # (0,2): 4 steps -> far; first step DOWN (UP impossible)
    assert env.features(0)[0] == 3 + 2 * 1 + 1


def test_f2_none_when_everything_observed(cfg):
    env = scenario(cfg, ["...", ".B.", "..."], starts=[(1, 1)] * 3)
    assert env.features(0)[1] == 0                 # whole 3x3 map in view at reset


def test_observation_and_mask_ignore_hidden_state(cfg):
    """Two worlds that differ only outside agent 0's view give agent 0 identical observations and masks."""
    # Both worlds share a light victim at (6,0) (keeps the episode running); world A also has a heavy victim at (6,6).
    rows_a = ["B......", ".......", ".......", ".......", ".......", ".......", "l.....h"]
    rows_b = ["B......", ".......", ".......", ".......", ".......", ".......", "l......"]
    ea = scenario(cfg, rows_a, starts=[(0, 0), (6, 6), (6, 5)])
    eb = scenario(cfg, rows_b, starts=[(0, 0), (6, 6), (6, 5)])
    assert ea.features(0)[2] == 0                  # teammates at Chebyshev distance 6: out of range
    for _ in range(3):
        assert ea.features(0) == eb.features(0)
        assert np.array_equal(ea.masks[0], eb.masks[0])
        ea.step([Action.RIGHT, Action.WAIT, Action.WAIT])
        eb.step([Action.RIGHT, Action.WAIT, Action.WAIT])
    # but agents 1 and 2 (who do see the victim) differ
    assert ea.features(1) != eb.features(1)
