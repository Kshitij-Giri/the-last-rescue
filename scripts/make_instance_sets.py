"""Generate and freeze the instance seed lists (spec §1.4, §1.8; calibration.yaml `instance_sets`).

Run AFTER calibration. For every split and index k, attempts 0, 1, ... are tried until the instance is feasible at the
Critical level (exact check, per-agent budgets, the configuration's own H and B_ref); the rejection rate is reported.
No policy is evaluated on these instances here - this only fixes WHICH instances later phases use.

Outputs: results/calibration/instance_sets.json (seed lists, attempts, rejection rates, SHA-256 of each list's instances)
Usage: python scripts/make_instance_sets.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.calibration import config_variant  # noqa: E402
from tlr.costs import CostModel  # noqa: E402
from tlr.mapgen import compute_statics, feasible_victims, generate_instance  # noqa: E402
from tlr.utils import SEED_STRIDE, deep_update, initial_budget, instance_seed, load_config  # noqa: E402


def build(cfg: dict, split: str, count: int, H: int, b0: int, n: int) -> dict:
    """Seed list of `count` instances of `split`, each feasible at budget b0 (attempts recorded)."""
    cm = CostModel.from_config(cfg)
    seeds, attempts, h = [], [], hashlib.sha256()
    for k in range(count):
        for a in range(SEED_STRIDE):
            s = instance_seed(split, k, a)
            inst = generate_instance(cfg, s)
            st = compute_statics(inst, cm, [1, 2])
            if feasible_victims(inst, st, cm, n, H, "per_agent", b0).any():
                seeds.append(s)
                attempts.append(a)
                h.update(inst.to_bytes())
                break
        else:
            raise RuntimeError(f"{split} index {k}: no feasible instance in {SEED_STRIDE} attempts")
    rejected = sum(attempts)
    return {"count": count, "seeds": seeds, "attempts": attempts, "rejected": rejected,
            "rejection_rate": rejected / (rejected + count), "sha256": h.hexdigest(), "H": H, "b0_critical": b0}


def feasibility_of(cfg: dict, seeds: list[int], H: int, b0: int, n: int, mode: str) -> float:
    cm = CostModel.from_config(cfg)
    ok = 0
    for s in seeds:
        inst = generate_instance(cfg, s)
        st = compute_statics(inst, cm, [1, 2])
        ok += bool(feasible_victims(inst, st, cm, n, H, mode, b0).any())
    return ok / len(seeds)


def main() -> None:
    cal = yaml.safe_load((ROOT / "config" / "calibration.yaml").read_text())
    summ = json.loads((ROOT / "results" / "calibration" / "calibration_summary.json").read_text())
    crit = summ["levels"]["critical"]
    confs = summ["configurations"]
    base = load_config()
    n = int(base["env"]["n_agents"])
    sets = cal["instance_sets"]
    out: dict = {"critical_rho": crit, "rule": "regenerate (attempt+1) until feasible at Critical, per-agent budgets"}

    m = confs["main"]
    cfg_main = config_variant(base, **m["spec"])
    b0c = initial_budget(crit, m["B_ref"])
    out["main"] = {sp: build(cfg_main, sp, int(sets[sp]), m["H"], b0c, n)
                   for sp in ("train", "validation", "test")}
    cfg_shift = deep_update(cfg_main, {"env": {"wall_fraction": 0.25, "victim_density": 0.09}})
    out["main"]["shifted_test"] = build(cfg_shift, "shifted_test", int(sets["shifted_test"]), m["H"], b0c, n)
    out["main"]["shifted_test"]["config"] = {"wall_fraction": 0.25, "victim_density": 0.09}

    alt = summ["alternate_configuration"]
    a = confs[alt]
    cfg_alt = config_variant(base, **a["spec"])
    b0a = initial_budget(crit, a["B_ref"])
    out["alternate"] = {"name": alt, **{sp: build(cfg_alt, sp, int(sets[sp]), a["H"], b0a, n)
                                         for sp in ("train", "validation", "test")}}

    # A3: p_heavy = 0 reuses the main seed lists (pairing). Report, do not filter.
    p0 = confs["main_p0"]
    cfg_p0 = config_variant(base, **p0["spec"])
    b0p = initial_budget(crit, p0["B_ref"])
    out["main_p0_feasibility_on_main_seeds"] = {
        sp: feasibility_of(cfg_p0, out["main"][sp]["seeds"], p0["H"], b0p, n, "per_agent")
        for sp in ("validation", "test")}
    out["pooled_feasibility_on_main_seeds"] = {
        sp: feasibility_of(cfg_main, out["main"][sp]["seeds"], m["H"], b0c, n, "pooled")
        for sp in ("validation", "test")}
    p = ROOT / "results" / "calibration" / "instance_sets.json"
    p.write_text(json.dumps(out, indent=1))
    for grp in ("main", "alternate"):
        for sp, v in out[grp].items():
            if isinstance(v, dict) and "seeds" in v:
                print(f"{grp:9s} {sp:12s} n={v['count']:4d} rejected={v['rejected']:3d} "
                      f"({100 * v['rejection_rate']:.1f}%) sha256={v['sha256'][:16]}")
    print("A3 p_heavy=0 feasibility on main seeds:", out["main_p0_feasibility_on_main_seeds"])
    print("pooled feasibility on main seeds:", out["pooled_feasibility_on_main_seeds"])


if __name__ == "__main__":
    main()
