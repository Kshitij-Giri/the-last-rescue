"""Record SHA-256 hashes of everything frozen at the end of Phase 3 (preregistration §11).

Output: results/calibration/freeze_manifest.json. Re-run to compare: any hash change after the freeze must correspond to
a logged post-freeze deviation in docs/deviations_log.md.
Usage: python scripts/make_freeze_manifest.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "calibration" / "freeze_manifest.json"
PATTERNS = ["docs/preregistration.md", "docs/phase0_design_spec.md", "config/*.yaml", "src/tlr/*.py",
            "scripts/*.py", "tests/*.py", "requirements.txt", "results/calibration/**/*.json",
            "results/calibration/**/*.csv", "results/calibration/**/*.md", "results/calibration/**/*.txt",
            "results/calibration/figures/*.png", "results/logs/pytest.txt"]


def collect() -> dict[str, str]:
    files: dict[str, str] = {}
    for pat in PATTERNS:
        for p in sorted(ROOT.glob(pat)):
            if p.is_file() and p != OUT:
                files[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare current files with the recorded manifest")
    args = ap.parse_args()
    files = collect()
    if args.check:
        rec = json.loads(OUT.read_text())["files"]
        changed = sorted(k for k in rec if files.get(k) != rec[k])
        added = sorted(set(files) - set(rec))
        print("changed since freeze:", changed or "none")
        print("new files since freeze:", added or "none")
        sys.exit(1 if changed else 0)
    man = {"frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "python": platform.python_version(),
           "packages": {p: metadata.version(p) for p in ("numpy", "scipy", "pandas", "matplotlib", "PyYAML", "pytest")},
           "files": files}
    OUT.write_text(json.dumps(man, indent=1))
    print(f"{len(files)} files hashed -> {OUT.relative_to(ROOT)}")
    for k in ("docs/preregistration.md", "docs/phase0_design_spec.md", "config/calibrated.yaml",
              "results/calibration/instance_sets.json"):
        print(f"  {k}: {files[k]}")


if __name__ == "__main__":
    main()
