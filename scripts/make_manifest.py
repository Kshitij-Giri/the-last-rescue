"""results/manifest.json: SHA-256 of every code, config, doc and result file (preregistration deliverable), with
software versions and seeds. Combines the Phase 3 freeze manifest, Phase 5 manifest and current files.
Usage: python scripts/make_manifest.py
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
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and "__pycache__" not in rel.parts and rel.parts[0] != ".pytest_cache" \
                and str(rel) not in ("results/manifest.json", "docs/zip_integrity.txt"):
            files[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
    man = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "python": platform.python_version(),
           "packages": {p: metadata.version(p) for p in ("numpy", "scipy", "pandas", "matplotlib", "PyYAML", "pytest",
                                                         "python-docx")},
           "preregistration": {"file": "docs/preregistration.md", "frozen": "2026-11-12",
                               "sha256": files.get("docs/preregistration.md")},
           "confirmatory_training_seeds": list(range(10)), "pilot_seeds": [1000, 1001, 1002, 1003, 1004],
           "linked_manifests": ["results/calibration/freeze_manifest.json", "results/phase5/phase5_manifest.json"],
           "n_files": len(files), "files": files}
    (ROOT / "results" / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"{len(files)} files hashed -> results/manifest.json")


if __name__ == "__main__":
    main()
