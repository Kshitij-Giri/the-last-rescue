"""Independent verification of Phase 5-6 results. Exits non-zero on ANY mismatch.

Checks
  V1 seed-level values: recomputed from the raw episode CSVs (results/eval) with an independent pandas implementation and
     compared with results/stats/seed_level_learned.csv and baselines_test.csv (tolerance 1e-12).
  V2 condition means: recomputed from V1 values and compared with results/stats/condition_means.csv.
  V3 confirmatory tests: recomputed directly with scipy (not tlr.stats) plus an independent Holm implementation;
     compared with h1_h2_omnibus.csv, h1_h2_pairwise.csv, h3_vs_baselines.csv, h4_A1_mismatch.csv, h6_A4_solo.csv, and
     results.json (H0, H5).
  V4 reproducibility: scripts/run_stats.py is re-run into a scratch directory; every output file must be byte-identical.
  V5 claims ledger: every entry of docs/claims.yaml is checked against its source; docs/claims_ledger.md is written.
  V6 provenance: training-run count and the Phase 5 manifest hashes of raw evaluation files.
Usage: python scripts/verify_results.py      (log: results/logs/verify_results.txt)
"""

from __future__ import annotations

import filecmp
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as ss

ROOT = Path(__file__).resolve().parents[1]
ST = ROOT / "results" / "stats"
LEVELS = ["Abundant", "Moderate", "Scarce", "Critical"]
FAIL: list[str] = []
LOG: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    LOG.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def seed_values(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Independent re-implementation of the preregistered seed-level values."""
    g = df.groupby(keys, sort=False)
    out = pd.DataFrame({
        "rf": g.rf.mean(),
        "rescued_heavy_share": g.rescued_heavy.sum() / g.n_heavy.sum().replace(0, np.nan),
        "ear": g.ear_num.sum() / g.ear_den.sum().replace(0, np.nan),
        "rsr": (g.rsr_other_num.sum() + g.rsr_self_num.sum()) / g.rsr_den.sum().replace(0, np.nan),
        "rsr_other": g.rsr_other_num.sum() / g.rsr_den.sum().replace(0, np.nan),
        "tdi": g.tdi.mean(), "pss": g.pss_num.sum() / g.pss_den.sum().replace(0, np.nan),
        "gini_consumption": g.gini_consumption.mean(), "cr": g.cr_num.sum() / g.cr_den.sum().replace(0, np.nan),
        "steps": g.steps.mean()})
    return out.reset_index()


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    m, run = len(p), 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[j]))
        adj[j] = run
    return adj


def snap(d):
    """Independent floating-point tie handling (same principle as tlr.stats.ZERO_TOL; see deviations C6)."""
    d = np.asarray(d, float)
    return np.where(np.abs(d) < 1e-9, 0.0, d)


def close(a, b, tol=1e-12) -> bool:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a.shape == b.shape and bool(np.all((np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= tol)))


def main() -> None:
    raw = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "learned").glob("*.csv"))])
    mine = seed_values(raw, ["block", "level", "checkpoint", "seed"])
    theirs = pd.read_csv(ST / "seed_level_learned.csv")
    j = mine.merge(theirs, on=["block", "level", "checkpoint", "seed"], suffixes=("_v", "_s"))
    check("V1 seed-level rows matched", len(j) == len(theirs) == len(mine), f"{len(j)} rows")
    for c in ("rf", "rescued_heavy_share", "ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr", "steps"):
        check(f"V1 seed-level {c}", close(j[f"{c}_v"], j[f"{c}_s"]))
    braw = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "baselines").glob("*.csv"))])
    bm = seed_values(braw, ["combo", "level", "policy"]).merge(pd.read_csv(ST / "baselines_test.csv"),
                                                               on=["combo", "level", "policy"], suffixes=("_v", "_s"))
    check("V1 baseline rows", len(bm) == 96, f"{len(bm)} rows")
    for c in ("rf", "cr", "rescued_heavy_share"):
        check(f"V1 baselines {c}", close(bm[f"{c}_v"], bm[f"{c}_s"]))

    CM = pd.read_csv(ST / "condition_means.csv")
    for (block, ckpt, level), g in mine.groupby(["block", "checkpoint", "level"]):
        for m in ("rf", "cr", "ear", "tdi", "pss"):
            ref = CM[(CM.block == block) & (CM.checkpoint == ckpt) & (CM.level == level) & (CM.metric == m)]["mean"]
            check(f"V2 mean {block}/{ckpt}/{level}/{m}", close(np.nanmean(g[m]), ref.iloc[0]))

    def M(metric, block="main"):
        d = mine[(mine.block == block) & (mine.checkpoint == "final")].set_index(["seed", "level"])[metric]
        return np.array([[d[(s, l)] for l in LEVELS] for s in range(10)])

    OM = pd.read_csv(ST / "h1_h2_omnibus.csv").set_index("metric")
    h2p = []
    for m in ("rf", "ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr"):
        X = M(m)
        X = X[~np.isnan(X).any(axis=1)]
        fr = ss.friedmanchisquare(*X.T)
        check(f"V3 Friedman {m}", close(fr.statistic, OM.loc[m, "friedman_chi2"], 1e-9) and
              close(fr.pvalue, OM.loc[m, "friedman_p"], 1e-12) and int(OM.loc[m, "n_complete"]) == len(X))
        dec = ss.page_trend_test(X, predicted_ranks=[4, 3, 2, 1]).pvalue
        inc = ss.page_trend_test(X, predicted_ranks=[1, 2, 3, 4]).pvalue
        check(f"V3 Page {m}", close(min(1, 2 * min(dec, inc)), OM.loc[m, "page_p_two_sided"], 1e-12))
        if m != "rf":
            h2p.append(fr.pvalue)
    check("V3 Holm H2 Friedman", close(holm(h2p), OM.loc[["ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption",
                                                           "cr"], "friedman_p_holm"].values, 1e-12))
    PW = pd.read_csv(ST / "h1_h2_pairwise.csv")
    rf = M("rf")
    pv = []
    for a in range(4):
        for b in range(a + 1, 4):
            pv.append(ss.wilcoxon(snap(rf[:, a] - rf[:, b]), zero_method="wilcox", correction=True).pvalue)
    ref = PW[PW.metric == "rf"]
    check("V3 RF pairwise p", close(pv, ref.p.values, 1e-12) and close(holm(pv), ref.p_holm6.values, 1e-12))
    sb = pd.read_csv(ST / "baselines_test.csv").set_index(["combo", "level", "policy"])
    H3 = pd.read_csv(ST / "h3_vs_baselines.csv")
    p3 = [ss.wilcoxon(snap(rf[:, LEVELS.index(r.level)] - sb.loc[("main", r.level, r.baseline), "rf"]),
                      zero_method="wilcox", correction=True).pvalue for r in H3.itertuples()]
    check("V3 H3 p and Holm(12)", close(p3, H3.p.values, 1e-12) and close(holm(p3), H3.p_holm12.values, 1e-12))
    r = json.loads((ST / "results.json").read_text())
    h0 = ss.wilcoxon(snap(rf[:, 0] - sb.loc[("main", "Abundant", "random"), "rf"]), alternative="greater",
                     zero_method="wilcox", correction=True)
    check("V3 H0", close(h0.pvalue, r["H0"]["p"], 1e-12) and r["H0"]["passed"])
    a1 = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "A1").glob("*.csv"))])
    a1s = seed_values(a1, ["level", "round", "seed"]).groupby(["level", "seed"]).rf.mean()
    H4 = pd.read_csv(ST / "h4_A1_mismatch.csv").set_index("level")
    p4 = []
    for j_, level in enumerate(LEVELS):
        d = snap(rf[:, j_] - np.array([a1s[(level, s)] for s in range(10)]))
        p4.append(ss.wilcoxon(d, zero_method="wilcox", correction=True).pvalue)
        check(f"V3 H4 diff {level}", close(d.mean(), H4.loc[level, "mean_diff"], 1e-9))
    check("V3 H4 p and Holm(4)", close(p4, H4.loc[LEVELS, "p"].values, 1e-12) and
          close(holm(p4), H4.loc[LEVELS, "p_holm4"].values, 1e-12))
    solo = M("rf", "solo")
    H6 = pd.read_csv(ST / "h6_A4_solo.csv").set_index("level")
    p6 = [ss.wilcoxon(snap(rf[:, k] - solo[:, k]), zero_method="wilcox", correction=True).pvalue for k in range(4)]
    check("V3 H6 p and Holm(4)", close(p6, H6.loc[LEVELS, "p"].values, 1e-12) and
          close(holm(p6), H6.loc[LEVELS, "p_holm4"].values, 1e-12))
    p0 = M("rf", "p0")
    did = (rf[:, 0] - rf[:, 3]) - (p0[:, 0] - p0[:, 3])
    check("V3 H5 DiD and p", close(did, r["H5"]["did_per_seed"], 1e-12) and
          close(ss.wilcoxon(snap(did), zero_method="wilcox", correction=True).pvalue, r["H5"]["p"], 1e-12))

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run_stats.py"), "--out", tmp], check=True,
                       capture_output=True)
        names = sorted(p.name for p in ST.glob("*") if p.suffix in (".csv", ".json"))
        same = [n for n in names if filecmp.cmp(ST / n, Path(tmp) / n, shallow=False)]
        check("V4 run_stats.py reproduces every output byte-identically", len(same) == len(names),
              f"{len(same)}/{len(names)} files identical")

    claims = yaml.safe_load((ROOT / "docs" / "claims.yaml").read_text())
    rows = []
    for c in claims:
        try:
            if c["kind"] == "json":
                v = json.loads((ROOT / c["file"]).read_text())
                for k in c["path"].split("."):
                    v = v[k]
            elif c["kind"] == "yaml":
                v = yaml.safe_load((ROOT / c["file"]).read_text())
                for k in c["path"].split("."):
                    v = v[k]
            elif c["kind"] == "csv":
                d = pd.read_csv(ROOT / c["file"])
                for k, val in c["where"].items():
                    d = d[d[k].astype(str) == str(val)]
                assert len(d) == 1, f"{len(d)} rows match"
                v = d[c["column"]].iloc[0]
            elif c["kind"] == "runs":
                v = len(list((ROOT / "results" / "runs").glob("**/run.json")))
            ok = abs(float(v) - float(c["value"])) <= float(c["tol"])
        except Exception as e:  # noqa: BLE001
            v, ok = f"ERROR {e}", False
        check(f"V5 claim {c['id']}", ok, f"stated {c['value']}, source {v}")
        rows.append({"id": c["id"], "family": c["family"], "claim": c["claim"], "source": c.get("file", "results/runs"),
                     "locator": c.get("path") or c.get("where") or c.get("query"), "stated": c["value"],
                     "source_value": v, "verified": "yes" if ok else "NO"})
    L = pd.DataFrame(rows)
    (ROOT / "docs" / "claims_ledger.md").write_text(
        "# Claims ledger (generated by scripts/verify_results.py from docs/claims.yaml)\n\n"
        "Every number reported in the phase summaries maps to the file and locator below; `verified` = the stated value "
        "matches the source within the stated rounding.\n\n" + L.to_markdown(index=False) + "\n")

    # V7: the final report (Phase 7). Every number shown in report/report.docx is registered in docs/report_numbers.yaml.
    rn_path = ROOT / "docs" / "report_numbers.yaml"
    docx_path = ROOT / "report" / "report.docx"
    if rn_path.exists() and docx_path.exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        import re
        import zipfile
        from report_lib import fmt_value, plain, read_source
        entries = yaml.safe_load(rn_path.read_text())
        bad_src, bad_fmt, missing = [], [], []
        xml = zipfile.ZipFile(docx_path).read("word/document.xml").decode("utf8")
        paras = ["".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p)) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
        text = "\n".join(paras).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        for e in entries:
            try:
                v = read_source(e) * float(e.get("scale", 1.0))
            except Exception as ex:  # noqa: BLE001
                bad_src.append(f"{e['file']}: {ex}")
                continue
            if not close(v, e["value"], 1e-12):
                bad_src.append(f"{e['file']} {e.get('where') or e.get('path')}: {v} != {e['value']}")
            if fmt_value(v, e["fmt"], e["nd"]) != e["display"]:
                bad_fmt.append(e["display"])
            if plain(e["display"]) not in text:
                missing.append(e["display"])
        check("V7 report numbers: every registered value equals its source file", not bad_src,
              f"{len(entries) - len(bad_src)}/{len(entries)}" + (f"; e.g. {bad_src[:2]}" if bad_src else ""))
        check("V7 report numbers: displayed text = formatted source value", not bad_fmt, f"{len(entries) - len(bad_fmt)}/{len(entries)}")
        check("V7 report numbers: every displayed value appears in report.docx", not missing,
              f"{len(entries) - len(missing)}/{len(entries)}" + (f"; missing {missing[:3]}" if missing else ""))
        blocks = json.loads((ROOT / "report" / "content.json").read_text())["blocks"]
        figs = [b for b in blocks if b["t"] == "figure"]
        n_img = len(re.findall(r"<pic:pic\b", xml))
        check("V7 report figures: every figure file exists and is embedded", all((ROOT / b["path"]).exists() for b in figs)
              and n_img == len(figs), f"{len(figs)} figures, {n_img} embedded images")
        labels_ok = all(f"Table {b['label']}. " in text for b in blocks if b["t"] == "table") and \
            all(f"Fig. {b['label']}. " in text for b in figs)
        check("V7 report: every table and figure caption is present", labels_ok)
        pdf = ROOT / "report" / "report.pdf"
        n_pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout)
                      .group(1)) if pdf.exists() else 0
        check("V7 report length within 25-40 pages (PDF rendering)", 25 <= n_pages <= 40, f"{n_pages} pages")
    else:
        check("V7 report present (report/report.docx and docs/report_numbers.yaml)", False, "missing")

    n_runs = len(list((ROOT / "results" / "runs").glob("**/run.json")))
    check("V6 training runs", n_runs == 350, f"{n_runs}")
    man = json.loads((ROOT / "results" / "phase5" / "phase5_manifest.json").read_text())["files"]
    evals = {k: v for k, v in man.items() if k.startswith("results/eval/")}
    bad = [k for k, h in evals.items() if hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != h]
    check("V6 raw evaluation CSVs unchanged since the Phase 5 manifest", not bad, f"{len(evals) - len(bad)}/{len(evals)}")

    LOG.append(f"\n{len(LOG) - len(FAIL)} checks passed, {len(FAIL)} failed")
    text = "\n".join(LOG)
    (ROOT / "results" / "logs" / "verify_results.txt").write_text(text + "\n")
    print(text)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
