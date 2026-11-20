"""Robustness blocks R1-R7 (exploratory, added after the main study; docs/deviations_log.md).

Each block changes one design choice of the main block (src/tlr/experiments.py ROBUST_BLOCKS), is trained on the same
seeds 0-9, training pool, validation list and four budget levels, and is evaluated greedily on the same 100 test
instances. The main block is re-evaluated here only to add action shares (WAIT, SEARCH, ...); its Q-tables are read,
never retrained. Resumable: finished runs (run.json) and evaluation parts (CSV) are skipped.

Usage:
  python scripts/run_robustness.py train [--blocks relbudget,role] [--workers 6]
  python scripts/run_robustness.py eval  [--workers 6]
  python scripts/run_robustness.py summary
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.experiments import (BLOCKS, LEVELS, ROBUST_BLOCKS, SEEDS, PoolCache, evaluate_actors, load_q,  # noqa: E402
                             q_team_factory, robust_cfg, robust_run_dir, setting, world_cfg)
from tlr.iql import IQLParams  # noqa: E402
from tlr.stats import bootstrap_ci, page_two_sided, paired_bootstrap_ci, wilcoxon_test  # noqa: E402
from tlr.train import RunSpec, train_run, summarize_eval  # noqa: E402

OUT = ROOT / "results" / "robustness"
CACHE: PoolCache | None = None


def _init() -> None:
    global CACHE
    CACHE = PoolCache()


def train_tasks(blocks: list[str]) -> list[tuple]:
    tasks = []
    for name in blocks:
        b = ROBUST_BLOCKS[name]
        for level in LEVELS:
            for s in SEEDS:
                for slot in ([0, 1, 2] if b.per_slot else [None]):
                    if not (robust_run_dir(name, level, s, slot) / "run.json").exists():
                        tasks.append((name, level, s, slot))
    return tasks


def _train(task: tuple) -> str:
    name, level, seed, slot = task
    b = ROBUST_BLOCKS[name]
    H, B_ref, b0 = setting(BLOCKS["main"], level)
    spec = RunSpec(name=f"{name}_{level}_s{seed}" + (f"_slot{slot}" if slot is not None else ""), seed=seed, b0=b0,
                   horizon=H, b_ref=B_ref, params=IQLParams(episodes=b.episodes),
                   agent_ids=[slot] if slot is not None else None, env_opts=dict(b.env_opts), q_init=b.q_init,
                   update_dormant=b.update_dormant, partner=b.partner)
    out = train_run(robust_cfg(b), spec, CACHE.get("main", "train"), CACHE.get("main", "validation"),
                    robust_run_dir(name, level, seed, slot))
    return f"{spec.name}: {out['seconds']} s, val RF {out['final']['rf']:.3f}, stable {out['stable']}"


def eval_parts() -> list[tuple]:
    parts = [(name, level) for name in ["main", *ROBUST_BLOCKS] for level in LEVELS]
    return [p for p in parts if not (OUT / "eval" / f"{p[0]}__{p[1]}.csv").exists()]


def _eval(part: tuple) -> str:
    name, level = part
    t0 = time.time()
    H, B_ref, b0 = setting(BLOCKS["main"], level)
    if name == "main":
        cfg, opts = world_cfg("main"), {}
    else:
        b = ROBUST_BLOCKS[name]
        cfg, opts = robust_cfg(b), dict(b.env_opts)
    pool = CACHE.get("main", "test")
    rows = []
    for s in SEEDS:
        rows += evaluate_actors(cfg, pool, H, B_ref, b0, "per_agent", q_team_factory(load_q(name, level, s)),
                                {"block": name, "level": level, "seed": s}, env_opts=opts, action_shares=True)
    out = OUT / "eval" / f"{name}__{level}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    pd.DataFrame(rows).to_csv(tmp, index=False)
    tmp.rename(out)
    return f"eval {name}/{level}: {len(rows)} episodes in {time.time() - t0:.0f} s"


METRICS = ["rf", "rescued_heavy_share", "ear", "cr", "share_wait", "share_search"]


def seed_table() -> pd.DataFrame:
    recs = []
    for f in sorted((OUT / "eval").glob("*.csv")):
        df = pd.read_csv(f)
        for (block, level, seed), g in df.groupby(["block", "level", "seed"]):
            s = summarize_eval(g.to_dict("records"))
            recs.append({"block": block, "level": level, "seed": int(seed), **{m: s[m] for m in METRICS[:4]},
                         "share_wait": float(g.share_wait.mean()), "share_search": float(g.share_search.mean())})
    return pd.DataFrame(recs)


def stable_counts() -> dict[str, int]:
    out = {}
    for name in ROBUST_BLOCKS:
        runs = list((OUT / "runs" / name).glob("*/*/run.json"))
        out[name] = sum(json.loads(r.read_text())["stable"] for r in runs)
        out[name + "_n"] = len(runs)
    return out


def summary() -> None:
    T = seed_table()
    T.to_csv(OUT / "seed_table.csv", index=False)
    res: dict = {"stable": stable_counts(), "blocks": {}}
    lines = ["# Robustness blocks R1-R7 (EXPLORATORY, added after the main study)", "",
             "Unit = training seed (n = 10 per cell). Test set = the same 100 frozen test instances as the main study. "
             "Values: mean [95% percentile bootstrap CI over seeds]. Differences vs main are paired by seed; "
             "p-values are unadjusted two-sided Wilcoxon signed-rank and are descriptive only. "
             "Trend p = two-sided Page's L across Abundant -> Critical.", ""]
    main = T[T.block == "main"].set_index(["level", "seed"])
    for name in ["main", *ROBUST_BLOCKS]:
        B = T[T.block == name]
        if B.empty:
            continue
        q = "main block (reference), re-evaluated for action shares" if name == "main" else ROBUST_BLOCKS[name].question
        M = np.array([[B[(B.level == lv) & (B.seed == s)].rf.mean() for lv in LEVELS] for s in SEEDS])
        pg = page_two_sided(M)
        blk = {"question": q, "page_p": pg["p"], "direction": pg["direction"], "levels": {}}
        lines += [f"## {name}: {q}", "",
                  f"RF trend across levels: {pg['direction']}, Page two-sided p = {pg['p']:.2e}."
                  + (f" Stable runs (preregistered criterion): {res['stable'][name]} of {res['stable'][name + '_n']}."
                     if name != "main" else ""), "",
                  "| level | " + " | ".join(METRICS) + " | RF - main RF | p vs main |",
                  "|---|" + "---|" * (len(METRICS) + 2)]
        for lv in LEVELS:
            L = B[B.level == lv].set_index("seed").sort_index()
            cells = []
            for m in METRICS:
                lo, hi = bootstrap_ci(L[m].values, f"rob|{name}|{lv}|{m}")
                cells.append(f"{np.nanmean(L[m]):.3f} [{lo:.3f}, {hi:.3f}]")
            rec = {m: float(np.nanmean(L[m])) for m in METRICS}
            if name == "main":
                diff_txt, p_txt = "", ""
            else:
                ref = main.loc[lv].sort_index().rf.values
                d = L.rf.values - ref
                lo, hi = paired_bootstrap_ci(L.rf.values, ref, f"rob|{name}|{lv}|diff")
                w = wilcoxon_test(d)
                rec.update(diff=float(d.mean()), diff_lo=lo, diff_hi=hi, p=w["p"])
                diff_txt, p_txt = f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]", f"{w['p']:.4f}"
            blk["levels"][lv] = rec
            lines.append(f"| {lv} | " + " | ".join(cells) + f" | {diff_txt} | {p_txt} |")
        lines.append("")
        res["blocks"][name] = blk
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    (OUT / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "eval", "summary"])
    ap.add_argument("--blocks", default=",".join(ROBUST_BLOCKS))
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    if args.cmd == "summary":
        summary()
        return
    work, fn = (train_tasks(args.blocks.split(",")), _train) if args.cmd == "train" else (eval_parts(), _eval)
    print(f"{args.cmd}: {len(work)} items", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as ex:
        for msg in ex.map(fn, work):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
