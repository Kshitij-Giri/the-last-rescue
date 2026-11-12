"""Measure environment speed (replaces the Phase 0 assumed cost in the compute estimate; spec §7).

Times only env.step() (payment, moves, resolution, observation update, features and masks for all agents);
the random policy's own time is excluded. Budgets/horizon here are placeholders (calibration is Phase 3).
Usage: python scripts/bench_env.py [--instances 20] [--episodes-per-instance 5]
"""

from __future__ import annotations

import argparse
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tlr.costs import CostModel  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.mapgen import compute_statics, generate_instance  # noqa: E402
from tlr.utils import instance_seed, load_config, make_rng  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=20)
    ap.add_argument("--episodes-per-instance", type=int, default=5)
    args = ap.parse_args()
    cfg = load_config()
    cm = CostModel.from_config(cfg)
    lines = [f"python {platform.python_version()} on {platform.machine()} ({platform.system()})", ""]

    t0 = time.perf_counter()
    insts = [generate_instance(cfg, instance_seed("validation", k)) for k in range(args.instances)]
    t1 = time.perf_counter()
    stats = [compute_statics(i, cm, [1, 2]) for i in insts]
    t2 = time.perf_counter()
    lines.append(f"map generation: {(t1 - t0) / args.instances * 1e3:.1f} ms/map; "
                 f"path tables: {(t2 - t1) / args.instances * 1e3:.1f} ms/map")

    for b0, H in ((15, 100), (40, 100), (400, 100)):
        env = RescueEnv(cfg, horizon=H, b_ref=40)
        rng = make_rng(0)
        step_time, n_steps, n_eps = 0.0, 0, 0
        for inst, st in zip(insts, stats):
            for _ in range(args.episodes_per_instance):
                _, masks = env.reset(inst, b0, statics=st, record=False)
                while not env.done:
                    acts = [int(rng.choice(np.flatnonzero(m))) for m in masks]
                    s = time.perf_counter()
                    _, masks, _, _, _ = env.step(acts)
                    step_time += time.perf_counter() - s
                    n_steps += 1
                n_eps += 1
        lines.append(f"b0={b0:>3} H={H}: {n_eps} episodes, mean length {n_steps / n_eps:.1f} steps, "
                     f"env.step = {step_time / n_steps * 1e6:.1f} us/step (3 agents) "
                     f"= {step_time / n_steps / 3 * 1e6:.1f} us per agent-step")
    text = "\n".join(lines)
    print(text)
    out = Path(__file__).resolve().parents[1] / "results" / "logs" / "bench_env.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
