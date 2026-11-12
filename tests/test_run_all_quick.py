"""The --quick driver runs the whole reduced pipeline (tiny scale here) and never writes into results/."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_all  # noqa: E402


def test_quick_pipeline_tiny(tmp_path):
    out = tmp_path / "q"
    rc = run_all.quick(out, workers=1, skip_tests=True,
                       q=dict(seeds=[0, 1], episodes=20, n_train=4, n_val=2, n_test=3, checkpoint_every=10))
    assert rc == 0
    s = json.loads((out / "quick_summary.json").read_text())
    assert set(s["iql_rf"]) == {"Abundant", "Moderate", "Scarce", "Critical"}
    for lv, d in s["baselines_rf"].items():
        assert set(d) == {"random", "greedy", "cooperative", "oracle"}
        assert 0 <= d["oracle"] <= 1
    assert (out / "quick_rf.png").exists() and (out / "episodes.csv").exists()
    assert len(list((out / "runs").glob("*/seed_*/run.json"))) == 8


def test_quick_refuses_results_dir():
    with pytest.raises(SystemExit):
        run_all.quick(ROOT / "results", workers=1, skip_tests=True)


def test_quick_defaults_are_reduced_versions_of_the_frozen_settings():
    q = run_all.QUICK
    assert q["episodes"] < 8000 and len(q["seeds"]) < 10 and q["checkpoint_every"] == 500
