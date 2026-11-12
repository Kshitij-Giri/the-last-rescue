"""Phase 5 summary: seed-level values, condition means, the preregistered H0-gate, and A1-A8 completion status.

Descriptive only, apart from the H0-gate (preregistration §5.2), which Phase 5 is required to run. All confirmatory and
secondary tests (Friedman, Page's L, Wilcoxon families with Holm, bootstrap CIs, A8 mediation) are Phase 6.
Seed-level values follow preregistration §3: per seed, mean over the 100 test episodes; ratio metrics pooled.

Usage: python scripts/phase5_summary.py
Outputs: results/phase5/seed_level_<table>.csv, results/phase5/phase5_summary.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.experiments import BLOCKS, LEVELS, SEEDS, run_dir  # noqa: E402
from tlr.train import summarize_eval  # noqa: E402

EVAL = ROOT / "results" / "eval"
OUT = ROOT / "results" / "phase5"
COLS = ["rf", "ms", "rescued_heavy_share", "rescued_light_share", "ear", "rsr_other", "tdi", "pss", "cr",
        "e1_abandonment", "e2_duplicate", "collective_return", "steps", "exhausted", "horizon", "coverage"]


def load(kind: str) -> pd.DataFrame:
    files = sorted((EVAL / kind).glob("*.csv"))
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def seed_level(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for k, g in df.groupby(keys, sort=False):
        k = k if isinstance(k, tuple) else (k,)
        rows.append({**dict(zip(keys, k)), "episodes": len(g), **summarize_eval(g.to_dict("records"))})
    return pd.DataFrame(rows)


def fmt(df: pd.DataFrame, cols: list[str]) -> str:
    d = df[cols].copy()
    for c in ("seed", "round"):
        if c in d:
            d[c] = d[c].astype(int).astype(str)   # identifiers, not numbers
    return d.to_markdown(index=False, floatfmt=".3f")


def lvl_order(df: pd.DataFrame, col: str = "level") -> pd.DataFrame:
    return df.assign(_o=df[col].map({l: i for i, l in enumerate(LEVELS)})).sort_values("_o").drop(columns="_o")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    md = ["# Phase 5 results summary (descriptive; formal analysis is Phase 6)", "",
          "All values are on the frozen **test** instances (100 per condition; shifted test where stated), after "
          "**8,000 training episodes** (not converged; Phase 4). Unit = training seed (0-9): per seed, mean over test "
          "episodes, ratio metrics pooled. All runs are included, stable or not. The oracle is a full-information "
          "centralized reference, never a learner.", ""]

    # ---------------- training status and stability (A5)
    st_rows = []
    for name, b in BLOCKS.items():
        for level in LEVELS:
            if b.eqsteps and level == "Abundant":
                continue
            for s in SEEDS:
                for slot in ([0, 1, 2] if b.solo else [None]):
                    p = run_dir(name, level, s, slot) / "run.json"
                    if p.exists():
                        r = json.loads(p.read_text())
                        st_rows.append({"block": name, "level": level, "seed": s, "slot": slot,
                                        "seconds": r["seconds"], "env_steps": r["total_env_steps"],
                                        "episodes": int(r["final"]["episode"]), "stable": r["stable"],
                                        "last_churn": r["last_churn"], "last3_rf_range": r["last3_rf_range"],
                                        "val_rf_final": r["final"]["rf"], "best_val_rf": r["best_val_rf"]})
    ST = pd.DataFrame(st_rows)
    ST.to_csv(OUT / "training_runs.csv", index=False)
    g = ST.groupby(["block", "level"], sort=False).agg(runs=("seed", "size"), stable=("stable", "sum"),
                                                       churn_mean=("last_churn", "mean"),
                                                       rf_range_mean=("last3_rf_range", "mean"),
                                                       episodes_mean=("episodes", "mean"),
                                                       env_steps_mean=("env_steps", "mean"),
                                                       cpu_seconds=("seconds", "sum")).reset_index()
    md += ["## Training runs and stability (A5)", "",
           f"{len(ST)} training runs completed, {ST.seconds.sum() / 3600:.2f} CPU-hours of training. "
           "Stable = preregistered criterion (churn < 5% between the last two checkpoints and validation RF range < 0.02 "
           "over the last three).", "", g.to_markdown(index=False, floatfmt=".3f"), ""]

    # ---------------- learned policies on test
    L = load("learned")
    SL = seed_level(L, ["block", "level", "checkpoint", "seed"]) if len(L) else pd.DataFrame()
    SL.to_csv(OUT / "seed_level_learned.csv", index=False)
    B = load("baselines")
    SB = seed_level(B, ["combo", "level", "policy"]) if len(B) else pd.DataFrame()
    SB.to_csv(OUT / "baselines_test.csv", index=False)

    if len(SL):
        main_f = SL[(SL.block == "main") & (SL.checkpoint == "final")]
        md += ["## Exp1 / Exp2 — main sweep, seed level (final checkpoint, test)", ""]
        for level in LEVELS:
            d = main_f[main_f.level == level].sort_values("seed")
            if len(d):
                md += [f"**{level}**", "", fmt(d, ["seed", "rf", "rescued_heavy_share", "rescued_light_share", "ear",
                                                   "rsr_other", "tdi", "pss", "cr", "e1_abandonment", "steps",
                                                   "exhausted", "horizon"]), ""]
        agg = lvl_order(main_f.groupby("level")[COLS].agg(["mean", "std"]).reset_index())
        agg.columns = ["_".join(c).strip("_") for c in agg.columns]
        md += ["**Condition means ± SD over 10 seeds (main, final checkpoint):**", "",
               agg[["level"] + [f"{c}_{s}" for c in ("rf", "rescued_heavy_share", "ear", "rsr_other", "tdi", "pss",
                                                       "cr", "e1_abandonment") for s in ("mean", "std")]]
               .to_markdown(index=False, floatfmt=".3f"), ""]
        bv = SL[(SL.block == "main") & (SL.checkpoint == "bestval")].groupby("level").rf.mean()
        md += ["Best-on-validation checkpoint (preregistered sensitivity), mean test RF: " +
               ", ".join(f"{l} {bv.get(l, np.nan):.3f}" for l in LEVELS), ""]

    if len(SB):
        md += ["## Baselines on the same test instances (reference)", "",
               fmt(lvl_order(SB.sort_values(["combo", "policy"])),
                   ["combo", "level", "policy", "rf", "rescued_heavy_share", "ear", "cr", "steps", "exhausted"]), ""]

    # ---------------- H0-gate (preregistration §5.2)
    if len(SL) and len(SB):
        iql = main_f[main_f.level == "Abundant"].sort_values("seed").rf.values
        rnd = float(SB[(SB.combo == "main") & (SB.level == "Abundant") & (SB.policy == "random")].rf.iloc[0])
        if len(iql) == 10:
            d = iql - rnd
            p = float(wilcoxon(d, alternative="greater").pvalue)
            delta = (int((d > 0).sum()) - int((d < 0).sum())) / len(d)
            passed = p < 0.05 and delta >= 0.33
            gate = {"iql_seed_rf": iql.tolist(), "random_rf": rnd, "wilcoxon_one_sided_p": p, "delta_1": delta,
                    "passed": bool(passed)}
            (OUT / "h0_gate.json").write_text(json.dumps(gate, indent=1))
            md += ["## H0-gate (preregistered; test set, seeds 0-9, Abundant)", "",
                   f"IQL RF per seed: {', '.join(f'{x:.3f}' for x in iql)}; random baseline RF {rnd:.3f}. "
                   f"One-sided Wilcoxon signed-rank p = {p:.4f}; δ₁ = {delta:.2f}. **Gate {'PASSED' if passed else 'FAILED'}** "
                   f"(criterion: p < 0.05 and δ₁ ≥ 0.33).", ""]

    # ---------------- A1, A2
    A1 = load("A1")
    if len(A1):
        a1 = seed_level(A1, ["level", "round", "seed"])
        a1.to_csv(OUT / "seed_level_A1.csv", index=False)
        mm = a1.groupby(["level", "seed"]).rf.mean().rename("mismatch_rf").reset_index()
        orig = main_f[["level", "seed", "rf"]].rename(columns={"rf": "original_rf"})
        j = lvl_order(orig.merge(mm, on=["level", "seed"]))
        j["difference"] = j.original_rf - j.mismatch_rf
        j.to_csv(OUT / "seed_level_A1_paired.csv", index=False)
        s = lvl_order(j.groupby("level")[["original_rf", "mismatch_rf", "difference"]].mean().reset_index())
        s["seeds_original_better"] = [int((j[j.level == l].difference > 0).sum()) for l in s.level]
        md += ["## A1 — teammate mismatch (test; mismatch score = mean of the seed's 2 mismatched teams)", "",
               s.to_markdown(index=False, floatfmt=".3f"), ""]
    A2 = load("A2")
    if len(A2):
        a2 = seed_level(A2, ["level", "policy", "seed", "ablated_slot", "replacement"])
        a2.to_csv(OUT / "seed_level_A2.csv", index=False)
        iq = a2[a2.policy == "iql"].groupby(["level", "replacement"])[["rf", "cr", "rescued_heavy_share"]].mean()
        co = a2[a2.policy == "cooperative"].groupby(["level", "replacement"])[["rf", "cr", "rescued_heavy_share"]].mean()
        intact = main_f.groupby("level")[["rf", "cr", "rescued_heavy_share"]].mean()
        rows = []
        for level in LEVELS:
            for rep in ("random", "wait"):
                if (level, rep) in iq.index:
                    rows.append({"level": level, "replacement": rep, "iql_intact_rf": intact.loc[level, "rf"],
                                 "iql_ablated_rf": iq.loc[(level, rep), "rf"],
                                 "iql_intact_cr": intact.loc[level, "cr"], "iql_ablated_cr": iq.loc[(level, rep), "cr"],
                                 "coop_intact_rf": co.loc[(level, "none"), "rf"] if (level, "none") in co.index else np.nan,
                                 "coop_ablated_rf": co.loc[(level, rep), "rf"],
                                 "coop_intact_cr": co.loc[(level, "none"), "cr"] if (level, "none") in co.index else np.nan,
                                 "coop_ablated_cr": co.loc[(level, rep), "cr"]})
        md += ["## A2 — one agent replaced at test time (mean over seeds and the 3 slots)", "",
               pd.DataFrame(rows).to_markdown(index=False, floatfmt=".3f"), ""]

    # ---------------- A3, A4, A6, ablation, alternate config
    def block_means(block: str) -> pd.DataFrame:
        d = SL[(SL.block == block) & (SL.checkpoint == "final")]
        return lvl_order(d.groupby("level")[["rf", "rescued_heavy_share", "cr", "tdi", "rsr_other", "steps",
                                             "exhausted", "horizon"]].mean().reset_index())

    if len(SL):
        for block, title in (("p0", "A3 primary — p_heavy = 0 world, main budgets"),
                             ("p0sec", "A3 secondary — p_heavy = 0 world, its own calibration"),
                             ("solo", "A4 — solo-trained agents deployed together"),
                             ("eqsteps", "A6 — equal environment steps (vs main, equal episodes)"),
                             ("pooled", "Ablation — pooled team budget"),
                             ("alt", "Alternate configuration L12_d04")):
            d = SL[(SL.block == block) & (SL.checkpoint == "final")]
            if len(d):
                md += [f"## {title} (test, mean over seeds; seed-level rows in seed_level_learned.csv)", "",
                       block_means(block).to_markdown(index=False, floatfmt=".3f"), ""]
        # paired, seed-level contrasts (descriptive)
        mf = SL[(SL.block == "main") & (SL.checkpoint == "final")].set_index(["level", "seed"]).rf
        def paired(block: str) -> pd.DataFrame:
            o = SL[(SL.block == block) & (SL.checkpoint == "final")].set_index(["level", "seed"]).rf
            j = pd.concat([mf.rename("main"), o.rename(block)], axis=1).dropna().reset_index()
            j["diff_main_minus"] = j["main"] - j[block]
            return j
        for block in ("solo", "eqsteps", "pooled"):
            if len(SL[SL.block == block]):
                pj = paired(block)
                pj.to_csv(OUT / f"seed_level_paired_main_vs_{block}.csv", index=False)
        if len(SL[SL.block == "p0"]):
            p0 = SL[(SL.block == "p0") & (SL.checkpoint == "final")].set_index(["level", "seed"]).rf
            dd = []
            for s in SEEDS:
                try:
                    dd.append({"seed": s, "drop_p05": mf[("Abundant", s)] - mf[("Critical", s)],
                               "drop_p0": p0[("Abundant", s)] - p0[("Critical", s)]})
                except KeyError:
                    pass
            if dd:
                D = pd.DataFrame(dd)
                D["DiD"] = D.drop_p05 - D.drop_p0
                D.to_csv(OUT / "seed_level_A3_DiD.csv", index=False)
                md += ["## A3 — difference-in-differences per seed (RF, Abundant minus Critical; primary)", "",
                       fmt(D, ["seed", "drop_p05", "drop_p0", "DiD"]), "",
                       f"Mean DiD = {D.DiD.mean():.3f} (seeds with DiD > 0: {int((D.DiD > 0).sum())}/10). "
                       "Test and CI: Phase 6.", ""]

    # ---------------- Exp5
    SH = load("shifted")
    if len(SH):
        sh = seed_level(SH, ["level", "seed"])
        sh.to_csv(OUT / "seed_level_shifted.csv", index=False)
        comp = lvl_order(sh.groupby("level").rf.mean().rename("shifted_rf").reset_index().merge(
            main_f.groupby("level").rf.mean().rename("test_rf").reset_index(), on="level"))
        md += ["## Exp5 — generalization: same-distribution test vs shifted test (wall 0.25, density 0.09)", "",
               comp.to_markdown(index=False, floatfmt=".3f"), ""]
    TR = load("transfer")
    if len(TR):
        tr = seed_level(TR, ["train_level", "test_level", "seed"])
        tr.to_csv(OUT / "seed_level_transfer.csv", index=False)
        M = tr.groupby(["train_level", "test_level"]).rf.mean().unstack()[LEVELS].reindex(LEVELS)
        md += ["## Exp5 — cross-ρ transfer matrix (rows: trained at; columns: tested at; mean RF over seeds)", "",
               M.to_markdown(floatfmt=".3f"), ""]

    (OUT / "phase5_summary.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
