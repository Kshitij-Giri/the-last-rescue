"""Reward model: R_i = lambda_I * r_ind_i + lambda_T * r_team - lambda_C * cost_i.

Implements: spec §1.6. The environment accumulates the raw components per agent and per step; this module turns them
into scalar rewards with coefficients from the config, so the coefficients exist in exactly one place.
The λ's are fixed across every ρ and condition (spec §1.6, preregistration §2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RewardModel:
    """Coefficients of every reward component (spec §1.6)."""

    discovery: float
    light_rescue: float
    heavy_rescuer: float
    heavy_assister: float
    team_per_rescue: float
    lambda_I: float
    lambda_T: float
    lambda_C: float

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "RewardModel":
        r = cfg["reward"]
        return cls(**{k: float(r[k]) for k in cls.__dataclass_fields__})


@dataclass
class RewardComponents:
    """Raw per-agent components of one step, before λ-weighting. Shares are already split among co-actors."""

    discovery_share: np.ndarray      # (n,) victims first seen by the team this step, split among simultaneous observers
    light_share: np.ndarray          # (n,) light rescues credited (1/k for k simultaneous RESCUErs)
    heavy_rescuer_share: np.ndarray  # (n,)
    heavy_assister_share: np.ndarray # (n,)
    n_rescued: int                   # victims rescued by anyone this step (drives r_team)
    cost: np.ndarray                 # (n,) integer cost actually paid


def combine(rm: RewardModel, comp: RewardComponents) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (R, r_ind, r_team) for one step. R has shape (n,)."""
    r_ind = (rm.discovery * comp.discovery_share + rm.light_rescue * comp.light_share
             + rm.heavy_rescuer * comp.heavy_rescuer_share + rm.heavy_assister * comp.heavy_assister_share)
    r_team = rm.team_per_rescue * comp.n_rescued
    R = rm.lambda_I * r_ind + rm.lambda_T * r_team - rm.lambda_C * comp.cost.astype(float)
    return R, r_ind, float(r_team)
