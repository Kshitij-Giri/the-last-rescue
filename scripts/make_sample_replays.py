"""Phase 1 replay evidence: ASCII replays of rule-relevant episodes (spec deliverable "replay evidence").

Produces in results/replays/:
  phase1_random_episode.txt          random valid actions on test instance 0 (placeholder b0=25, H=60: NOT calibrated)
  phase1_scripted_heavy_assist.txt   a failed solo RESCUE, then a successful simultaneous RESCUE + ASSIST
  phase1_scripted_stale_memory.txt   agent 1 walks toward a victim agent 2 already rescued; memory is corrected
  phase1_scripted_pooled_preempt.txt pooled budget: rotating priority preempts an action
Usage: python scripts/make_sample_replays.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.costs import Action as A  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.mapgen import generate_instance, instance_from_ascii  # noqa: E402
from tlr.replay import render_episode, write_replay  # noqa: E402
from tlr.utils import instance_seed, load_config, make_rng  # noqa: E402

W = A.WAIT
OUT = ROOT / "results" / "replays"


def scripted(cfg, rows, starts, plan, title, mode="per_agent", budgets=None, horizon=30):
    inst = instance_from_ascii(rows)
    env = RescueEnv(cfg, horizon=horizon, b_ref=40, budget_mode=mode)
    L = inst.L
    env.reset(inst, 40, start_positions=[r * L + c for r, c in starts], budgets=budgets)
    for acts in plan:
        if env.done:
            break
        env.step(acts)
    return render_episode(inst, env.log, title)


def main() -> None:
    cfg = load_config()

    # 1. Random policy on a generated instance.
    inst = generate_instance(cfg, instance_seed("test", 0))
    env = RescueEnv(cfg, horizon=60, b_ref=40)
    _, masks = env.reset(inst, 25)
    rng = make_rng(2026)
    while not env.done:
        _, masks, _, _, _ = env.step([int(rng.choice(np.flatnonzero(m))) for m in masks])
    write_replay(OUT / "phase1_random_episode.txt",
                 render_episode(inst, env.log, "Random valid actions (placeholder b0=25, H=60; not calibrated)"))

    # 2. Heavy victim: solo attempt fails, simultaneous RESCUE + ASSIST succeeds.
    rows = [".....", ".....", "..h..", ".....", "B...l"]
    plan = [[A.UP, A.RIGHT, W], [A.UP, A.RIGHT, W], [A.RIGHT, A.UP, W], [A.RIGHT, W, W],
            [A.RESCUE, A.UP, W],                     # agent 1 RESCUEs while agent 2 is still arriving: fails
            [A.RESCUE, A.ASSIST, W]]                 # both on the cell, simultaneous: success
    write_replay(OUT / "phase1_scripted_heavy_assist.txt",
                 scripted(cfg, rows, [(4, 0), (4, 0), (4, 0)], plan,
                          "Scripted: heavy victim needs simultaneous RESCUE + ASSIST"))

    # 3. Stale memory.
    rows = [".......", ".......", ".......", "...l...", ".......", ".......", "l.....B"]
    plan = [[A.LEFT, A.DOWN, W], [A.LEFT, A.DOWN, W], [W, A.DOWN, W], [W, A.RESCUE, W],
            [A.RIGHT, W, W], [A.RIGHT, W, W], [A.RIGHT, W, W]]
    write_replay(OUT / "phase1_scripted_stale_memory.txt",
                 scripted(cfg, rows, [(3, 2), (0, 3), (6, 6)], plan,
                          "Scripted: agent 1 remembers a victim agent 2 rescued out of its view (stale_correction)"))

    # 4. Pooled preemption.
    rows = [".....", ".....", "..l..", ".....", "B...l"]
    plan = [[W, W, W], [A.RESCUE, A.SEARCH, W]]
    write_replay(OUT / "phase1_scripted_pooled_preempt.txt",
                 scripted(cfg, rows, [(2, 2), (4, 0), (4, 0)], plan,
                          "Scripted: pooled pool of 4; at t=1 agent 2 pays first, agent 1's RESCUE is preempted",
                          mode="pooled", budgets=[4]))
    for p in sorted(OUT.glob("phase1_*.txt")):
        print(p.relative_to(ROOT), "-", p.read_text().splitlines()[-1])


if __name__ == "__main__":
    main()
