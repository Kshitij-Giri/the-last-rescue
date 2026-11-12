"""One entry point for the whole pipeline.

  python scripts/run_all.py --quick     smoke run of the complete pipeline in < 10 minutes (2 cores)
  python scripts/run_all.py --full      the full study (about 2.5 h on 2 cores: training and evaluation 8,752 s in our run, then stats, figures, report)

--quick never touches results/ (the frozen study outputs). It writes to results_quick/ (or --out) and runs, on a
reduced scale, every stage the full study runs:
  1 the pytest suite
  2 IQL training of the main sweep: 4 scarcity levels x 3 seeds x 3,000 episodes (full: 10 seeds x 8,000),
    on the first 200 frozen training maps, checkpoints every 500 episodes on the first 20 validation maps
  3 greedy evaluation of the learned teams and of the random / greedy / cooperative baselines and the oracle reference
    on the first 30 frozen test maps
  4 the H0-gate and H1 statistics (one-sample Wilcoxon; Friedman + Kendall's W; Page's L) on the 3 seeds
  5 a figure and a summary (results_quick/quick_summary.md), and a timing log
Quick numbers are a pipeline check only: 3 seeds and 3,000 episodes have little power and are NOT results of the study.
The same frozen preregistered settings are used except episodes, seeds and instance counts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.baselines import make_team  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.evaluate import run_episode  # noqa: E402
from tlr.experiments import BLOCKS, LEVELS, evaluate_actors, q_team_factory, seeds_for, setting, world_cfg  # noqa: E402
from tlr.iql import IQLParams  # noqa: E402
from tlr.metrics import episode_record  # noqa: E402
from tlr.oracle import OraclePolicy  # noqa: E402
from tlr.stats import friedman, one_sample_vs_constant, page_two_sided  # noqa: E402
from tlr.train import InstancePool, RunSpec, train_run  # noqa: E402

QUICK = dict(seeds=[0, 1, 2], episodes=3000, n_train=200, n_val=20, n_test=30, checkpoint_every=500)
FULL_STEPS = [
    "python -m pytest -q",
    "python scripts/run_calibration.py && python scripts/plot_calibration.py",
    "python scripts/make_instance_sets.py && python scripts/make_freeze_manifest.py --check",
    "python scripts/run_pilot.py --baselines && python scripts/run_pilot.py --variant P0 && python scripts/analyze_pilot.py P0",
    *[f"python scripts/run_experiments.py train --block {b} --workers 2" for b in
      ["main", "p0", "p0sec", "pooled", "alt", "solo", "eqsteps"]],
    *[f"python scripts/run_experiments.py eval --kind {k} --workers 2" for k in
      ["learned", "shifted", "transfer", "A1", "A2", "baselines"]],
    "python scripts/check_phase5_integrity.py && python scripts/phase5_summary.py && python scripts/make_phase5_manifest.py",
    "python scripts/run_stats.py && python scripts/make_tables.py && python scripts/make_figures.py && python scripts/make_replays.py",
    "bash scripts/build_report.sh",
    "python scripts/verify_results.py && python scripts/make_manifest.py",
]

_POOLS: dict = {}


def _pools(q):
    key = (q["n_train"], q["n_val"], q["n_test"])
    if _POOLS.get("key") != key:
        cfg = world_cfg("main")
        _POOLS.update(key=key, cfg=cfg,
                      train=InstancePool(cfg, seeds_for("main", "train")[:q["n_train"]]),
                      val=InstancePool(cfg, seeds_for("main", "validation")[:q["n_val"]]),
                      test=InstancePool(cfg, seeds_for("main", "test")[:q["n_test"]]))
    return _POOLS


def _train_and_eval(task):
    level, seed, out, q = task
    P = _pools(q)
    H, B_ref, b0 = setting(BLOCKS["main"], level)
    params = replace(IQLParams(), episodes=q["episodes"])
    spec = RunSpec(name=f"quick_{level}_s{seed}", seed=seed, b0=b0, horizon=H, b_ref=B_ref, params=params,
                   checkpoint_every=q["checkpoint_every"])
    res = train_run(P["cfg"], spec, P["train"], P["val"], Path(out) / "runs" / level / f"seed_{seed}")
    Q = np.load(Path(out) / "runs" / level / f"seed_{seed}" / "q_final.npz")["Q"]
    rows = evaluate_actors(P["cfg"], P["test"], H, B_ref, b0, "per_agent", q_team_factory(list(Q)),
                           {"level": level, "policy": "iql", "seed": seed})
    return rows, {"level": level, "seed": seed, "seconds": res["seconds"], "env_steps": res["total_env_steps"]}


def _baselines(arg):
    level, q = arg
    P = _pools(q)
    H, B_ref, b0 = setting(BLOCKS["main"], level)
    env = RescueEnv(P["cfg"], horizon=H, b_ref=B_ref)
    rows = []
    for name in ("random", "greedy", "cooperative", "oracle"):
        for es in (range(3) if name == "random" else [0]):  # quick: 3 random evaluation seeds (full: 10)
            for inst, st in P["test"].items:
                pol = OraclePolicy() if name == "oracle" else make_team(name)
                log = run_episode(env, inst, b0, pol, statics=st, seed=int(inst.seed) * 31 + es)
                rows.append(episode_record(inst, st, log, env.costs, env.r_v, level=level, policy=name, eval_seed=es))
    return rows


def quick(out: Path, workers: int, skip_tests: bool, q: dict | None = None) -> int:
    q = dict(QUICK, **(q or {}))
    t0 = time.time()
    if out.resolve() == (ROOT / "results").resolve():
        raise SystemExit("--quick must not write into results/")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    log = []

    def stage(msg):
        line = f"[{time.time() - t0:6.1f} s] {msg}"
        print(line, flush=True)
        log.append(line)

    if not skip_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True)
        (out / "pytest.txt").write_text(r.stdout + r.stderr)
        stage(f"1 tests: {r.stdout.strip().splitlines()[-1]}")
        if r.returncode != 0:
            return 1
    tasks = [(lv, s, str(out), q) for lv in LEVELS for s in q["seeds"]]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(_train_and_eval, tasks))
        stage(f"2 trained and evaluated {len(tasks)} IQL runs ({q['episodes']} episodes each)")
        base = list(ex.map(_baselines, [(lv, q) for lv in LEVELS]))
        stage("3 baselines and oracle reference evaluated")
    ep = pd.DataFrame([r for rows, _ in res for r in rows] + [r for rows in base for r in rows])
    ep.to_csv(out / "episodes.csv", index=False)
    pd.DataFrame([m for _, m in res]).to_csv(out / "training_runs.csv", index=False)

    iql = ep[ep.policy == "iql"].groupby(["seed", "level"]).rf.mean().unstack()[LEVELS]
    bl = ep[ep.policy != "iql"].groupby(["level", "policy"]).rf.mean().unstack()
    M = iql.values
    fr, pg = friedman(M), page_two_sided(M)
    h0 = one_sample_vs_constant(iql["Abundant"].values, float(bl.loc["Abundant", "random"]), alternative="greater")
    summary = {"seeds": q["seeds"], "episodes": q["episodes"], "n_test": q["n_test"],
               "iql_rf": {lv: float(iql[lv].mean()) for lv in LEVELS},
               "baselines_rf": {lv: {p: float(bl.loc[lv, p]) for p in bl.columns} for lv in LEVELS},
               "H0_gate_quick": h0, "friedman_quick": fr, "page_quick": pg, "seconds_total": None}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.arange(4)
    for s in iql.index:
        ax.plot(x, iql.loc[s].values, color="#9db7d9", lw=1)
    ax.plot(x, iql.mean().values, "o-", color="#2a78d6", lw=2, label=f"IQL (mean of {len(q['seeds'])} seeds)")
    for p, c in [("cooperative", "#1baf7a"), ("greedy", "#eb6834"), ("random", "#7f7f7f"), ("oracle", "#3d3d3a")]:
        ax.plot(x, [bl.loc[lv, p] for lv in LEVELS], "--" if p == "oracle" else "-", color=c, lw=1.2,
                label="oracle reference (full information)" if p == "oracle" else p)
    ax.set_xticks(x, LEVELS)
    ax.set_ylabel(f"rescue fraction ({q['n_test']} test maps)")
    ax.set_title(f"QUICK pipeline check ({len(q['seeds'])} seeds, {q['episodes']:,} episodes): not study results",
                 fontsize=9, loc="left")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "quick_rf.png", dpi=130)
    plt.close(fig)
    stage("4 statistics and figure written")
    summary["seconds_total"] = round(time.time() - t0, 1)
    (out / "quick_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    lines = ["# Quick pipeline check (NOT study results)", "",
             f"Scale: {len(q['seeds'])} seeds x {q['episodes']} episodes per level, {q['n_train']} training maps, "
             f"{q['n_test']} test maps. Full study: 10 seeds x 8,000 episodes, 1,000 / 100 maps (results/).", "",
             "| level | IQL RF (mean) | random | greedy | cooperative | oracle reference |", "|---|---|---|---|---|---|"]
    for lv in LEVELS:
        lines.append(f"| {lv} | {iql[lv].mean():.3f} | " + " | ".join(f"{bl.loc[lv, p]:.3f}" for p in
                                                                      ["random", "greedy", "cooperative", "oracle"]) + " |")
    lines += ["", f"H0-gate (quick, one-sided, {len(q['seeds'])} seeds): p = {h0['p']:.4f} (with 3 seeds the smallest possible p is "
              "0.125, so the quick run cannot pass the preregistered gate; it only checks that the code path works).",
              f"Friedman (quick): chi2 = {fr['chi2']:.2f}, p = {fr['p']:.4f}, W = {fr['kendall_w']:.2f}; Page two-sided p = {pg['p']:.4f}.",
              "", f"Total time: {summary['seconds_total']} s", "", "## Log", ""] + log
    (out / "quick_summary.md").write_text("\n".join(lines) + "\n")
    print(f"done in {summary['seconds_total']} s -> {out}/quick_summary.md")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--quick", action="store_true")
    g.add_argument("--full", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results_quick"))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="--full: print the commands only")
    a = ap.parse_args()
    if a.quick:
        sys.exit(quick(Path(a.out), a.workers, a.skip_tests))
    for cmd in FULL_STEPS:
        print("$", cmd, flush=True)
        if not a.dry_run:
            subprocess.run(cmd, shell=True, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
