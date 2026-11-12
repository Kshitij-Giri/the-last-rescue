"""Phase 2 replay evidence: baseline behaviour on validation instance 0 (uncalibrated placeholder b0=40, H=200).

  results/replays/phase2_cooperative.txt  cooperative baseline: sector exploration, waiting, joint heavy rescue
  results/replays/phase2_greedy.txt       greedy baseline: identical agents in lockstep, redundant simultaneous
                                          searches, triple (duplicate) light rescues, failed solo heavy attempts
  results/replays/phase2_oracle.txt       oracle REFERENCE (full information, centralized)
Usage: python scripts/make_phase2_replays.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.baselines import make_team  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.evaluate import run_episode  # noqa: E402
from tlr.mapgen import generate_instance  # noqa: E402
from tlr.oracle import OraclePolicy  # noqa: E402
from tlr.replay import render_episode, write_replay  # noqa: E402
from tlr.utils import instance_seed, load_config  # noqa: E402

EVENTS = ["rescue", "failed_rescue", "failed_assist", "duplicate_rescue", "first_sighting", "stale_correction"]


def main() -> None:
    cfg = load_config()
    inst = generate_instance(cfg, instance_seed("validation", 0))
    for name in ("cooperative", "greedy", "oracle"):
        env = RescueEnv(cfg, horizon=200, b_ref=40)
        pol = OraclePolicy() if name == "oracle" else make_team(name)
        log = run_episode(env, inst, 40, pol, seed=0)
        label = "oracle REFERENCE (full information, centralized)" if name == "oracle" else f"{name} baseline"
        text = render_episode(inst, log, f"{label}; validation instance 0; placeholder b0=40, H=200", EVENTS)
        write_replay(ROOT / "results" / "replays" / f"phase2_{name}.txt", text)
        print(name, "-", text.strip().splitlines()[-1])


if __name__ == "__main__":
    main()
