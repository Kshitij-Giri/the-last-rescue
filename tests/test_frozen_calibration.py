"""Frozen Phase 3 artefacts are consistent and reproducible (preregistration §3, §8, §11).

- config/calibrated.yaml and config/default.yaml agree with results/calibration/calibration_summary.json;
- every frozen instance list regenerates byte-identically from its seeds (SHA-256 match) and is feasible at Critical;
- selecting levels again from the saved curves gives the frozen levels.
Skipped if Phase 3 outputs are absent (e.g. a fresh checkout before calibration has been run).
"""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tlr.calibration import config_variant, select_levels
from tlr.costs import CostModel
from tlr.mapgen import compute_statics, feasible_victims, generate_instance
from tlr.utils import deep_update, initial_budget, load_config

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "calibration" / "calibration_summary.json"
SETS = ROOT / "results" / "calibration" / "instance_sets.json"
pytestmark = pytest.mark.skipif(not SUMMARY.exists() or not SETS.exists(), reason="Phase 3 outputs not present")


def test_calibrated_config_matches_summary():
    S = json.loads(SUMMARY.read_text())
    cal = yaml.safe_load((ROOT / "config" / "calibrated.yaml").read_text())
    d = load_config()["calibrated"]
    m = S["configurations"]["main"]
    assert d["horizon"] == m["H"] == cal["configurations"]["main"]["H"] == 105
    assert d["b_ref"] == m["B_ref"] == cal["configurations"]["main"]["B_ref"] == 64
    lv = S["levels"]
    assert d["rho_levels"] == cal["rho_levels"] == {"Abundant": lv["abundant"], "Moderate": lv["moderate"],
                                                    "Scarce": lv["scarce"], "Critical": lv["critical"]}
    for name, r in S["configurations"].items():
        c = cal["configurations"][name]
        assert (c["H"], c["B_ref"]) == (r["H"], r["B_ref"])
        assert c["b0_per_level"] == {k: initial_budget(v, r["B_ref"]) for k, v in cal["rho_levels"].items()}


def test_levels_reselect_identically():
    S = json.loads(SUMMARY.read_text())
    sel = yaml.safe_load((ROOT / "config" / "calibration.yaml").read_text())["selection"]
    cur = S["configurations"]["main"]["curves"]
    coop = {float(k): v["rf_mean"] for k, v in cur["cooperative"].items()}
    orc = {float(k): v["rescued_ge1"] for k, v in cur["oracle"].items()}
    out = select_levels(coop, orc, sel)
    assert (out["moderate"], out["scarce"], out["critical"]) == (0.5, 0.3, 0.2)


@pytest.mark.parametrize("group,split", [("main", "validation"), ("main", "test"), ("main", "shifted_test"),
                                         ("alternate", "validation"), ("alternate", "test")])
def test_frozen_instance_lists_regenerate_identically(group, split):
    S = json.loads(SUMMARY.read_text())
    sets = json.loads(SETS.read_text())
    entry = sets[group][split]
    base = load_config()
    name = "main" if group == "main" else sets["alternate"]["name"]
    cfg = config_variant(base, **S["configurations"][name]["spec"])
    if split == "shifted_test":
        cfg = deep_update(cfg, {"env": {"wall_fraction": 0.25, "victim_density": 0.09}})
    cm = CostModel.from_config(cfg)
    h = hashlib.sha256()
    for s in entry["seeds"]:
        inst = generate_instance(cfg, s)
        st = compute_statics(inst, cm, [1, 2])
        assert feasible_victims(inst, st, cm, 3, entry["H"], "per_agent", entry["b0_critical"]).any()
        h.update(inst.to_bytes())
    assert h.hexdigest() == entry["sha256"]
