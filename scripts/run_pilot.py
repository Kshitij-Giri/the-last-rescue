"""Phase 4 learnability pilot (docs/pilot_protocol.md). Validation instances only; test sets are never loaded.

Usage:
  python scripts/run_pilot.py --baselines                       # baselines on validation at Abundant
  python scripts/run_pilot.py --variant P0 [--workers 2]        # 5 pilot seeds of a variant
Variants (protocol order): P0 defaults; P1 alpha 0.2; P2 alpha 0.05; P3 eps decay 0.9; P4 16k episodes;
  P0x2 = P0 with twice the episodes (episode-count rule).
Outputs: results/pilot/<variant>/seed_<s>/{train_log.csv, checkpoints.csv, val_final_episodes.csv, q_*.npz, run.json},
         results/pilot/<variant>/summary.json, results/pilot/baselines_validation_abundant.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.baselines import make_team  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.evaluate import run_episode  # noqa: E402
from tlr.iql import IQLParams  # noqa: E402
from tlr.metrics import episode_record  # noqa: E402
from tlr.oracle import OraclePolicy  # noqa: E402
from tlr.train import InstancePool, RunSpec, summarize_eval, train_run  # noqa: E402
from tlr.utils import load_config  # noqa: E402

OUT = ROOT / "results" / "pilot"
PILOT_SEEDS = [1000, 1001, 1002, 1003, 1004]
VARIANTS = {
    "P0": IQLParams(),
    "P1": IQLParams(alpha=0.2),
    "P2": IQLParams(alpha=0.05),
    "P3": IQLParams(eps_decay_fraction=0.9),
    "P4": IQLParams(episodes=16000),
    "P0x2": IQLParams(episodes=16000),
}
_POOLS: dict = {}


def _setting():
    cal = yaml.safe_load((ROOT / "config" / "calibrated.yaml").read_text())
    sets = json.loads((ROOT / "results" / "calibration" / "instance_sets.json").read_text())
    m = cal["configurations"]["main"]
    return m["H"], m["B_ref"], m["b0_per_level"]["Abundant"], sets["main"]["train"]["seeds"], \
        sets["main"]["validation"]["seeds"]


def _init_worker() -> None:
    """Each worker builds the frozen training and validation pools once (deterministic; no effect on results)."""
    cfg = load_config()
    H, B_ref, b0, tr, va = _setting()
    _POOLS["cfg"], _POOLS["train"], _POOLS["val"] = cfg, InstancePool(cfg, tr), InstancePool(cfg, va)


def _run(variant: str, seed: int) -> dict:
    H, B_ref, b0, _, _ = _setting()
    spec = RunSpec(name=f"{variant}_s{seed}", seed=seed, b0=b0, horizon=H, b_ref=B_ref, params=VARIANTS[variant])
    out = train_run(_POOLS["cfg"], spec, _POOLS["train"], _POOLS["val"], OUT / variant / f"seed_{seed}")
    out.pop("team")
    return out


def baselines() -> None:
    cfg = load_config()
    H, B_ref, b0, _, va = _setting()
    pool = InstancePool(cfg, va)
    env = RescueEnv(cfg, horizon=H, b_ref=B_ref)
    rows = []
    for name in ("random", "greedy", "cooperative", "oracle"):
        for es in (range(10) if name == "random" else [0]):
            for inst, st in pool.items:
                pol = OraclePolicy() if name == "oracle" else make_team(name)
                log = run_episode(env, inst, b0, pol, statics=st, seed=int(inst.seed) * 31 + es)
                rows.append(episode_record(inst, st, log, env.costs, env.r_v, policy=name, eval_seed=es))
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "baselines_validation_abundant.csv", index=False)
    summ = {name: summarize_eval(g.to_dict("records")) for name, g in df.groupby("policy", sort=False)}
    (OUT / "baselines_validation_abundant.json").write_text(json.dumps(summ, indent=1))
    for name, s in summ.items():
        print(f"{name:12s} RF {s['rf']:.3f}  heavy share {s['rescued_heavy_share']:.3f}  EAR {s['ear']:.3f}  "
              f"CR {s['cr']:.3f}  steps {s['steps']:.1f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant")
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    if args.baselines:
        baselines()
        return
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker) as ex:
        res = list(ex.map(_run, [args.variant] * len(PILOT_SEEDS), PILOT_SEEDS))
    summ = {r["spec"]["name"]: {k: r[k] for k in ("seconds", "total_env_steps", "stable", "last_churn",
                                                  "last3_rf_range", "best_val_episode", "best_val_rf")}
            | {"final": r["final"]} for r in res}
    (OUT / args.variant).mkdir(parents=True, exist_ok=True)
    (OUT / args.variant / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    for name, s in summ.items():
        f = s["final"]
        print(f"{name}: val RF {f['rf']:.3f} heavy {f['rescued_heavy_share']:.3f} EAR {f['ear']:.3f} "
              f"CR {f['cr']:.3f} steps {f['steps']:.1f} | stable {s['stable']} churn {s['last_churn']:.3f} "
              f"rf-range {s['last3_rf_range']:.3f} | {s['seconds']} s, {s['total_env_steps']} env steps")


if __name__ == "__main__":
    main()
