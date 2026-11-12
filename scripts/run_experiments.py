"""Phase 5 orchestrator: resumable training and evaluation (preregistration v1.0; docs/phase0_design_spec.md §5).

Every training run writes results/runs/<block>/<level>/seed_<s>[_slot<k>]/run.json LAST, so a run with run.json is
complete and is skipped on re-invocation. Every evaluation part writes one CSV (results/eval/<kind>/<part>.csv) and is
skipped if it exists. Interrupted work is simply redone from scratch for that run/part (deterministic, so identical).

Usage:
  python scripts/run_experiments.py status
  python scripts/run_experiments.py train  --block main [--levels Abundant,Moderate] [--workers 2]
  python scripts/run_experiments.py eval   --kind learned|shifted|transfer|A1|A2|baselines [--workers 2]
Blocks: main p0 p0sec pooled alt solo eqsteps (see src/tlr/experiments.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.baselines import make_team  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.evaluate import run_episode  # noqa: E402
from tlr.experiments import (BLOCKS, LEVELS, SEEDS, PoolCache, ablated_factory, cooperative_factory,  # noqa: E402
                             evaluate_actors, load_q, mismatch_permutations, q_team_factory, run_dir, setting,
                             world_cfg)
from tlr.iql import IQLParams  # noqa: E402
from tlr.metrics import episode_record  # noqa: E402
from tlr.oracle import OraclePolicy  # noqa: E402
from tlr.train import RunSpec, train_run  # noqa: E402

EVAL = ROOT / "results" / "eval"
CACHE: PoolCache | None = None


def now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _init() -> None:
    global CACHE
    CACHE = PoolCache()


# ------------------------------------------------------------------------------------------------ training
def train_tasks(block: str, levels: list[str]) -> list[tuple]:
    b = BLOCKS[block]
    lv = [x for x in levels if not (b.eqsteps and x == "Abundant")]   # A6: Abundant is the main run itself
    tasks = []
    for level in lv:
        for s in SEEDS:
            for slot in ([0, 1, 2] if b.solo else [None]):
                if not (run_dir(block, level, s, slot) / "run.json").exists():
                    tasks.append((block, level, s, slot))
    return tasks


def _train(task: tuple) -> str:
    block, level, seed, slot = task
    b = BLOCKS[block]
    H, B_ref, b0 = setting(b, level)
    budget = None
    if b.eqsteps:
        ref = run_dir("main", "Abundant", seed) / "run.json"
        budget = int(json.loads(ref.read_text())["total_env_steps"])
    spec = RunSpec(name=f"{block}_{level}_s{seed}" + (f"_slot{slot}" if slot is not None else ""), seed=seed, b0=b0,
                   horizon=H, b_ref=B_ref, budget_mode=b.mode, params=IQLParams(),
                   n_agents=1 if b.solo else None, agent_ids=[slot] if b.solo else None, max_env_steps=budget)
    out = train_run(world_cfg(b.world), spec, CACHE.get(b.world, "train"), CACHE.get(b.world, "validation"),
                    run_dir(block, level, seed, slot))
    f = out["final"]
    return (f"{now()} {spec.name}: {out['seconds']} s, {out['total_env_steps']} steps, val RF {f['rf']:.3f}, "
            f"heavy {f['rescued_heavy_share']:.3f}, stable {out['stable']}")


# ------------------------------------------------------------------------------------------------ evaluation
def eval_parts(kind: str) -> list[tuple]:
    parts = []
    if kind == "learned":
        for block in ("main", "p0", "p0sec", "pooled", "alt", "solo", "eqsteps"):
            for level in LEVELS:
                if block == "eqsteps" and level == "Abundant":
                    continue
                parts.append((kind, block, level))
    elif kind in ("shifted", "transfer", "A1", "A2"):
        parts = [(kind, "main", level) for level in LEVELS]
    elif kind == "baselines":
        parts = [(kind, combo, level) for combo in ("main", "p0", "p0sec", "pooled", "alt", "shifted")
                 for level in LEVELS]
    return [p for p in parts if not (EVAL / p[0] / f"{p[1]}__{p[2]}.csv").exists()]


def _trained(block: str, level: str) -> bool:
    if block == "solo":
        return all((run_dir(block, level, s, k) / "run.json").exists() for s in SEEDS for k in range(3))
    return all((run_dir(block, level, s) / "run.json").exists() for s in SEEDS)


def _eval(part: tuple) -> str:
    kind, block, level = part
    t0 = time.time()
    rows: list[dict] = []
    if kind == "learned":
        b = BLOCKS[block]
        if not _trained(block, level):
            return f"{now()} SKIP {part}: training incomplete"
        H, B_ref, b0 = setting(b, level)
        cfg, pool = world_cfg(b.world), CACHE.get(b.world, "test")
        for s in SEEDS:
            for which in (("final", "bestval") if block == "main" else ("final",)):
                rows += evaluate_actors(cfg, pool, H, B_ref, b0, b.mode, q_team_factory(load_q(block, level, s, which)),
                                        {"block": block, "level": level, "seed": s, "checkpoint": which})
    elif kind == "shifted":
        if not _trained("main", level):
            return f"{now()} SKIP {part}: training incomplete"
        H, B_ref, b0 = setting(BLOCKS["main"], level)
        cfg, pool = world_cfg("main", shifted=True), CACHE.get("main", "shifted_test")
        for s in SEEDS:
            rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", q_team_factory(load_q("main", level, s)),
                                    {"block": "main", "level": level, "seed": s, "test_set": "shifted"})
    elif kind == "transfer":
        if not _trained("main", level):
            return f"{now()} SKIP {part}: training incomplete"
        cfg, pool = world_cfg("main"), CACHE.get("main", "test")
        for test_level in LEVELS:
            H, B_ref, b0 = setting(BLOCKS["main"], test_level)
            for s in SEEDS:
                rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", q_team_factory(load_q("main", level, s)),
                                        {"train_level": level, "test_level": test_level, "seed": s})
    elif kind == "A1":
        if not _trained("main", level):
            return f"{now()} SKIP {part}: training incomplete"
        H, B_ref, b0 = setting(BLOCKS["main"], level)
        cfg, pool = world_cfg("main"), CACHE.get("main", "test")
        Qs = {s: load_q("main", level, s) for s in SEEDS}
        for r, (s2, s3) in enumerate(mismatch_permutations()):
            for s in SEEDS:
                team = [Qs[s][0], Qs[s2[s]][1], Qs[s3[s]][2]]
                rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", q_team_factory(team),
                                        {"level": level, "round": r, "seed": s, "slot1_seed": s2[s],
                                         "slot2_seed": s3[s]})
    elif kind == "A2":
        if not _trained("main", level):
            return f"{now()} SKIP {part}: training incomplete"
        H, B_ref, b0 = setting(BLOCKS["main"], level)
        cfg, pool = world_cfg("main"), CACHE.get("main", "test")
        for slot in range(3):
            for kind2 in ("random", "wait"):
                for s in SEEDS:
                    f = ablated_factory(q_team_factory(load_q("main", level, s)), slot, kind2)
                    rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", f,
                                            {"level": level, "policy": "iql", "seed": s, "ablated_slot": slot,
                                             "replacement": kind2})
                f = ablated_factory(cooperative_factory(), slot, kind2)
                rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", f,
                                        {"level": level, "policy": "cooperative", "seed": -1, "ablated_slot": slot,
                                         "replacement": kind2})
        rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", cooperative_factory(),
                                {"level": level, "policy": "cooperative", "seed": -1, "ablated_slot": -1,
                                 "replacement": "none"})
    elif kind == "baselines":
        combo = block
        b = BLOCKS["main" if combo == "shifted" else combo]
        H, B_ref, b0 = setting(b, level)
        if combo == "shifted":
            cfg, pool = world_cfg("main", shifted=True), CACHE.get("main", "shifted_test")
        else:
            cfg, pool = world_cfg(b.world), CACHE.get(b.world, "test")
        env = RescueEnv(cfg, horizon=H, b_ref=B_ref, budget_mode=b.mode)
        for name in ("random", "greedy", "cooperative", "oracle"):
            for es in (range(10) if name == "random" else [0]):
                for inst, st in pool.items:
                    pol = OraclePolicy() if name == "oracle" else make_team(name)
                    log = run_episode(env, inst, b0, pol, statics=st, seed=int(inst.seed) * 31 + es)
                    rows.append(episode_record(inst, st, log, env.costs, env.r_v, combo=combo, level=level,
                                               policy=name, eval_seed=es))
    out = EVAL / kind / f"{block}__{level}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    pd.DataFrame(rows).to_csv(tmp, index=False)
    tmp.rename(out)  # atomic: a part file exists only when complete
    return f"{now()} {kind}/{block}__{level}: {len(rows)} episodes in {time.time() - t0:.0f} s"


def status() -> None:
    for name, b in BLOCKS.items():
        cells = []
        for level in LEVELS:
            if b.eqsteps and level == "Abundant":
                continue
            n = sum(1 for s in SEEDS for k in ([0, 1, 2] if b.solo else [None])
                    if (run_dir(name, level, s, k) / "run.json").exists())
            cells.append(f"{level} {n}/{30 if b.solo else 10}")
        print(f"{name:8s} " + " | ".join(cells))
    for kind in ("learned", "shifted", "transfer", "A1", "A2", "baselines"):
        d = EVAL / kind
        print(f"eval {kind:9s}: {len(list(d.glob('*.csv'))) if d.exists() else 0} parts done, "
              f"{len(eval_parts(kind))} remaining")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "train", "eval"])
    ap.add_argument("--block")
    ap.add_argument("--kind")
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    if args.cmd == "status":
        status()
        return
    if args.cmd == "train":
        tasks = train_tasks(args.block, args.levels.split(","))
        print(f"{now()} train {args.block}: {len(tasks)} runs to do", flush=True)
        work, fn = tasks, _train
    else:
        work, fn = eval_parts(args.kind), _eval
        print(f"{now()} eval {args.kind}: {len(work)} parts to do", flush=True)
    if not work:
        return
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as ex:
        for msg in ex.map(fn, work):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
