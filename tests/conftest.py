"""Shared pytest fixtures and helpers for hand-written scenarios (spec §1; Phase 1 test plan)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tlr.env import RescueEnv  # noqa: E402
from tlr.mapgen import instance_from_ascii  # noqa: E402
from tlr.utils import load_config, make_rng  # noqa: E402


@pytest.fixture
def cfg() -> dict:
    return load_config()


def rc(L: int, r: int, c: int) -> int:
    """(row, col) -> flat cell index."""
    return r * L + c


def scenario(cfg: dict, rows: Sequence[str], starts: Sequence[tuple[int, int]] | None = None,
             budgets: Sequence[int] | None = None, horizon: int = 50, b_ref: int = 40, mode: str = "per_agent",
             n_agents: int = 3, b0: int = 40) -> RescueEnv:
    """Build and reset an env on an ASCII map. `starts` are (row, col) per agent (test hook)."""
    inst = instance_from_ascii(rows)
    env = RescueEnv(cfg, horizon=horizon, b_ref=b_ref, budget_mode=mode, n_agents=n_agents)
    sp = [rc(inst.L, r, c) for r, c in starts] if starts is not None else None
    env.reset(inst, b0, start_positions=sp, budgets=budgets)
    return env


def random_valid_actions(masks: np.ndarray, rng: np.random.Generator) -> list[int]:
    """Uniformly random valid action per agent (test helper; the real random baseline arrives in Phase 2)."""
    return [int(rng.choice(np.flatnonzero(m))) for m in masks]


__all__ = ["rc", "scenario", "random_valid_actions", "make_rng"]
