"""SHA-256 manifest of every Phase 5 artefact (runs, Q-tables, logs, evaluation CSVs) plus software and seeds.

Output: results/phase5/phase5_manifest.json. Phase 6 merges this into results/manifest.json.
Usage: python scripts/make_phase5_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    files = {}
    for pat in ("results/runs/**/*", "results/eval/**/*.csv", "results/phase5/*.csv", "results/phase5/*.md",
                "results/phase5/*.json", "results/logs/phase5_*.txt"):
        for p in sorted(ROOT.glob(pat)):
            if p.is_file() and p.name != "phase5_manifest.json":
                files[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    man = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "python": platform.python_version(),
           "packages": {p: metadata.version(p) for p in ("numpy", "scipy", "pandas", "matplotlib", "PyYAML", "pytest")},
           "training_seeds": list(range(10)), "frozen_preregistration": "docs/preregistration.md (v1.0)",
           "iql": {"alpha": 0.1, "gamma": 0.98, "eps": "1.0 -> 0.05 over 70%", "episodes": 8000},
           "n_files": len(files), "files": files}
    out = ROOT / "results" / "phase5" / "phase5_manifest.json"
    out.write_text(json.dumps(man, indent=1))
    print(f"{len(files)} files hashed -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
