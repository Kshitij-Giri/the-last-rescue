"""Shared utilities: config loading, seeding, budget rounding, grid geometry helpers.

Implements: spec §1.1 (budget B_0 = round(rho * B_ref)), §1.8 (seed ranges), reproducibility rules.
No module-level random state exists anywhere in the package: every random draw goes through an explicit
numpy Generator created from an explicit integer seed.
"""

from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"

# Seed-range bases (spec §1.8). Disjoint ranges guarantee that calibration, training, validation and test
# instances can never coincide.
SEED_BASE = {
    "calibration": 1_000_000,
    "train": 2_000_000,
    "validation": 3_000_000,
    "test": 4_000_000,
    "shifted_test": 5_000_000,
}


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a YAML config and apply nested overrides (dicts are merged recursively, other values replaced)."""
    with open(path or DEFAULT_CONFIG, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if overrides:
        cfg = deep_update(cfg, overrides)
    return cfg


def deep_update(base: dict[str, Any], upd: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of `base` with `upd` merged into it recursively."""
    out = copy.deepcopy(base)
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def make_rng(seed: int) -> np.random.Generator:
    """Create an independent PCG64 generator from an explicit integer seed."""
    return np.random.default_rng(np.random.SeedSequence(int(seed)))


SEED_STRIDE = 100  # max regeneration attempts per instance index (spec §1.4: infeasible instances are regenerated)


def instance_seed(split: str, index: int, attempt: int = 0) -> int:
    """Seed of attempt `attempt` of the `index`-th instance of a split.

    seed = base + SEED_STRIDE*index + attempt. The stride leaves room for regenerating an infeasible instance
    ("next seed") without ever colliding with the seed of the following index. With <= 10,000 instances per
    split the ranges stay disjoint (e.g. test: 4,000,000 .. 4,999,999).
    """
    if not (0 <= attempt < SEED_STRIDE):
        raise ValueError(f"attempt must be in [0, {SEED_STRIDE}), got {attempt}")
    if not (0 <= index < 10_000):
        raise ValueError("index out of range for disjoint seed ranges")
    return SEED_BASE[split] + SEED_STRIDE * int(index) + int(attempt)


def round_half_up(x: float) -> int:
    """Round to the nearest integer, halves upward (deterministic, unlike Python's banker's rounding)."""
    return int(math.floor(x + 0.5 + 1e-9))


def initial_budget(rho: float, b_ref: int) -> int:
    """B_0 = round(rho * B_ref) with round-half-UP.

    Python's built-in round() uses banker's rounding (round(2.5) == 2), which would make the mapping depend on
    parity; we use floor(x + 0.5). The 1e-9 guards against binary floating error such as 0.7*40 = 28.000000000000004
    or 0.35*20 = 6.999999999999999.
    """
    if not (0.0 < rho):
        raise ValueError(f"rho must be > 0, got {rho}")
    return round_half_up(rho * b_ref)


def chebyshev(r1: int, c1: int, r2: int, c2: int) -> int:
    """Chebyshev (king-move) distance between two grid cells."""
    return max(abs(r1 - r2), abs(c1 - c2))


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of a byte string (used for determinism tests and the results manifest)."""
    return hashlib.sha256(data).hexdigest()
