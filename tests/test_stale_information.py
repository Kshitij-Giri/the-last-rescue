"""Stale victim information (spec §1.3a): an agent remembers a victim that a teammate rescued out of its view.

Map (7x7), light victim v0 at (3,3), light victim v1 at (6,0) (keeps the episode running), base (6,6).
Agent 0 starts at (3,2) and sees v0 at reset; agent 1 starts at (0,3); agent 2 waits at the base.
"""

import numpy as np

from tlr.costs import Action as A

from conftest import rc, scenario

W = A.WAIT
ROWS = [".......", ".......", ".......", ".......", ".......", ".......", "l.....B"]
ROWS[3] = "...l..."
STARTS = [(3, 2), (0, 3), (6, 6)]


def _play_until_rescue(env, rescue: bool):
    env.step([A.LEFT, A.DOWN, W])     # A0 (3,1): (3,3) leaves its view.  A1 (1,3)
    env.step([A.LEFT, A.DOWN, W])     # A0 (3,0).  A1 (2,3)
    env.step([W, A.DOWN, W])          # A1 (3,3) on the victim
    env.step([W, A.RESCUE if rescue else W, W])   # t = 3: A1 rescues v0 (or not, in the counterfactual)


def test_stale_memory_never_uses_hidden_state_and_is_corrected(cfg):
    env = scenario(cfg, ROWS, starts=STARTS)
    cf = scenario(cfg, ROWS, starts=STARTS)              # counterfactual: v0 is NOT rescued
    v0 = rc(7, 3, 3)
    assert v0 in env.known[0]
    _play_until_rescue(env, rescue=True)
    _play_until_rescue(cf, rescue=False)
    assert env.v_rescued[0] and not cf.v_rescued[0]

    # 1. Agent 0 still believes v0 is waiting, and its observation and mask are identical to the counterfactual:
    #    the rescue happened outside its view, so nothing hidden leaked into its inputs.
    assert v0 in env.known[0]
    assert env.features(0) == cf.features(0)
    assert env.features(0)[0] == 3 + 2 * 3 + 0        # f1: victim to the RIGHT, 3 steps (near)
    assert np.array_equal(env.masks[0], cf.masks[0])

    # 2. Agent 0 walks back; its moves are ordinary valid actions (stale information only wastes travel).
    _, _, _, _, info = env.step([A.RIGHT, W, W])       # A0 (3,1): (3,3) still out of view (Chebyshev 2)
    assert not [e for e in info["events"] if e["type"] == "stale_correction"]
    _, _, _, _, info = env.step([A.RIGHT, W, W])       # A0 (3,2): (3,3) enters view -> memory corrected
    sc = [e for e in info["events"] if e["type"] == "stale_correction"]
    assert len(sc) == 1 and sc[0]["agent"] == 0 and sc[0]["victim"] == 0
    assert sc[0]["t"] == 5 and sc[0]["steps_since_rescue"] == 2
    assert v0 not in env.known[0] and env.features(0)[0] == 0

    # 3. RESCUE is never offered on the already-rescued victim.
    env.step([A.RIGHT, W, W])                          # A0 on (3,3)
    assert env.pos[0] == v0 and not env.masks[0][A.RESCUE]

    # 4. The rescuer itself never logs a stale correction.
    assert not [e for e in env.log.events if e["type"] == "stale_correction" and e["agent"] == 1]
