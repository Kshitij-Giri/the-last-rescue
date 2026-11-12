"""Phase 5 integrity check: every preregistered run and evaluation part exists and is well-formed.

Checks: all runs have run.json, q_final.npz, q_bestval.npz, train_log.csv, checkpoints.csv; equal-episode runs have exactly
8,000 episodes with the frozen hyperparameters; A6 runs used >= the main Abundant step count of the same seed (and stopped
within one episode of it); evaluation parts are complete with the expected episode counts. Exit code 1 on any problem.
Usage: python scripts/check_phase5_integrity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.experiments import BLOCKS, LEVELS, SEEDS, run_dir  # noqa: E402

FROZEN = {"alpha": 0.1, "gamma": 0.98, "eps_start": 1.0, "eps_end": 0.05, "eps_decay_fraction": 0.7, "episodes": 8000}


def main() -> None:
    problems, n_runs = [], 0
    for name, b in BLOCKS.items():
        for level in LEVELS:
            if b.eqsteps and level == "Abundant":
                continue
            for s in SEEDS:
                for slot in ([0, 1, 2] if b.solo else [None]):
                    d = run_dir(name, level, s, slot)
                    for f in ("run.json", "q_final.npz", "q_bestval.npz", "train_log.csv", "checkpoints.csv"):
                        if not (d / f).exists():
                            problems.append(f"missing {d.relative_to(ROOT)}/{f}")
                    if not (d / "run.json").exists():
                        continue
                    n_runs += 1
                    r = json.loads((d / "run.json").read_text())
                    p = r["spec"]["params"]
                    if any(p[k] != v for k, v in FROZEN.items()):
                        problems.append(f"{d.relative_to(ROOT)}: non-frozen hyperparameters {p}")
                    if r["spec"]["seed"] != s:
                        problems.append(f"{d.relative_to(ROOT)}: seed mismatch")
                    eps = int(r["final"]["episode"])
                    if not b.eqsteps and eps != 8000:
                        problems.append(f"{d.relative_to(ROOT)}: {eps} episodes")
                    if b.eqsteps:
                        ref = json.loads((run_dir("main", "Abundant", s) / "run.json").read_text())["total_env_steps"]
                        if not (ref <= r["total_env_steps"] < ref + r["spec"]["horizon"] + 1):
                            problems.append(f"{d.relative_to(ROOT)}: steps {r['total_env_steps']} vs budget {ref}")
    expected = {"learned": (27, None), "shifted": (4, 1000), "transfer": (4, 4000), "A1": (4, 2000), "A2": (4, 6700),
                "baselines": (24, 1300)}
    for kind, (n_parts, n_eps) in expected.items():
        files = sorted((ROOT / "results" / "eval" / kind).glob("*.csv"))
        if len(files) != n_parts:
            problems.append(f"eval {kind}: {len(files)}/{n_parts} parts")
        for f in files:
            n = len(pd.read_csv(f))
            want = n_eps if n_eps is not None else (2000 if f.name.startswith("main__") else 1000)
            if n != want:
                problems.append(f"eval {kind}/{f.name}: {n} episodes (expected {want})")
    print(f"{n_runs} training runs checked; {len(problems)} problem(s)")
    for p in problems:
        print("  PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
