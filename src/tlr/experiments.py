"""Phase 5 experiment definitions: training blocks, instance pools, and evaluators (preregistration v1.0 §2, §3, §5;
spec §5 A1-A6, Exp1-Exp5).

Training blocks (seeds 0-9, all four rho levels unless noted):
  main     main configuration, per-agent budgets (Exp1-Exp4; H0-gate; A1, A2, A5)
  p0       A3 primary: p_heavy = 0 world on the main seeds, main H = 105 and B_ref = 64
  p0sec    A3 secondary: p_heavy = 0 world at its own calibration (H = 48, B_ref = 41)
  pooled   pooled team budget ablation (B_team = 3 b0), main configuration
  alt      alternate configuration L12_d04 (H = 150, B_ref = 87), its own frozen instance sets
  solo     A4: each agent slot trained ALONE (n = 1 environment), deployed together at test time
  eqsteps  A6: Moderate/Scarce/Critical trained for the same number of environment steps as the main Abundant run of
           the same seed (epsilon scheduled by steps)
Evaluation never uses validation instances for anything but checkpoints; test/shifted-test only for final evaluation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml

from .baselines import CooperativeController, StaticContext
from .calibration import config_variant
from .costs import Action
from .env import RescueEnv
from .iql import eval_rngs, masked_argmax
from .metrics import episode_record
from .train import InstancePool
from .utils import deep_update, load_config

ROOT = Path(__file__).resolve().parents[2]
LEVELS = ["Abundant", "Moderate", "Scarce", "Critical"]
SEEDS = list(range(10))


def calibrated() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "config" / "calibrated.yaml").read_text())


def instance_sets() -> dict[str, Any]:
    return json.loads((ROOT / "results" / "calibration" / "instance_sets.json").read_text())


@dataclass(frozen=True)
class Block:
    name: str
    world: str          # configuration of the instances: main | main_p0 | L12_d04
    calib: str          # configuration whose H, B_ref and budgets are used
    mode: str = "per_agent"
    solo: bool = False
    eqsteps: bool = False


BLOCKS = {
    "main": Block("main", "main", "main"),
    "p0": Block("p0", "main_p0", "main"),
    "p0sec": Block("p0sec", "main_p0", "main_p0"),
    "pooled": Block("pooled", "main", "main", mode="pooled"),
    "alt": Block("alt", "L12_d04", "L12_d04"),
    "solo": Block("solo", "main", "main", solo=True),
    "eqsteps": Block("eqsteps", "main", "main", eqsteps=True),
}


def world_cfg(world: str, shifted: bool = False) -> dict[str, Any]:
    spec = calibrated()["configurations"][world]["spec"]
    cfg = config_variant(load_config(), **spec)
    if shifted:
        cfg = deep_update(cfg, {"env": {"wall_fraction": 0.25, "victim_density": 0.09}})
    return cfg


def setting(block: Block, level: str) -> tuple[int, int, int]:
    """(H, B_ref, b0) of a block at a level."""
    c = calibrated()["configurations"][block.calib]
    return int(c["H"]), int(c["B_ref"]), int(c["b0_per_level"][level])


def seeds_for(world: str, split: str) -> list[int]:
    """Frozen seed list. The p_heavy = 0 world reuses the main lists (A3 pairing); the alternate config has its own."""
    s = instance_sets()
    group = "alternate" if world == "L12_d04" else "main"
    return s[group][split]["seeds"]


class PoolCache:
    """Per-process cache of instance pools (deterministic data; avoids recomputing path tables for every run)."""

    def __init__(self, max_items: int = 4) -> None:
        self.items: dict[tuple[str, str], InstancePool] = {}
        self.max_items = max_items

    def get(self, world: str, split: str) -> InstancePool:
        key = (world, split)
        if key not in self.items:
            if len(self.items) >= self.max_items:
                self.items.pop(next(iter(self.items)))
            shifted = split == "shifted_test"
            self.items[key] = InstancePool(world_cfg(world, shifted), seeds_for(world, split))
        return self.items[key]


# ----------------------------------------------------------------------------------------------------------------
# Actors for mixed-team evaluation (A1 mismatched teams, A2 ablation, A4 solo teams, plain learned teams)
# ----------------------------------------------------------------------------------------------------------------

class QActor:
    """Greedy learned agent; tie-breaks from the CRN evaluation stream of its slot (same as IQLTeam evaluation)."""

    needs_view = False

    def __init__(self, Q: np.ndarray, rng: np.random.Generator) -> None:
        self.Q, self.rng = Q, rng

    def act(self, obs: int, mask: np.ndarray, view=None) -> int:
        return masked_argmax(self.Q[obs], mask, self.rng)


class RandomActor:
    needs_view = False

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    def act(self, obs: int, mask: np.ndarray, view=None) -> int:
        return int(self.rng.choice(np.flatnonzero(mask)))


class WaitActor:
    needs_view = False

    def act(self, obs: int, mask: np.ndarray, view=None) -> int:
        return int(Action.WAIT)


class ControllerActor:
    """Wraps a decentralized baseline controller (uses the agent's own view, never the environment)."""

    needs_view = True

    def __init__(self, ctrl) -> None:
        self.ctrl = ctrl

    def act(self, obs: int, mask: np.ndarray, view=None) -> int:
        return int(self.ctrl.act(view, mask))


ActorFactory = Callable[[Any, StaticContext, int], list]   # (instance, ctx, instance_index) -> list of n actors


def q_team_factory(Qs: list[np.ndarray]) -> ActorFactory:
    """Learned team from per-slot Q-tables (slot i uses Qs[i]); tie-breaks = eval_rngs(instance seed)."""
    def make(inst, ctx, k):
        rngs = eval_rngs(inst.seed if inst.seed is not None else k, len(Qs))
        return [QActor(Q, rngs[i]) for i, Q in enumerate(Qs)]
    return make


def ablated_factory(base: ActorFactory, slot: int, kind: str) -> ActorFactory:
    """A2: replace one slot by a random or WAIT-only agent (random stream seeded by instance seed and slot)."""
    def make(inst, ctx, k):
        actors = base(inst, ctx, k)
        if kind == "random":
            seed = inst.seed if inst.seed is not None else k
            actors[slot] = RandomActor(np.random.default_rng(np.random.SeedSequence([int(seed), slot, 0xA2])))
        elif kind == "wait":
            actors[slot] = WaitActor()
        else:
            raise ValueError(kind)
        return actors
    return make


def cooperative_factory() -> ActorFactory:
    def make(inst, ctx, k):
        return [ControllerActor(CooperativeController(i, ctx, 0)) for i in range(ctx.n)]
    return make


def evaluate_actors(cfg: dict[str, Any], pool: InstancePool, H: int, B_ref: int, b0: int, mode: str,
                    factory: ActorFactory, labels: dict[str, Any]) -> list[dict[str, Any]]:
    """Run one greedy episode per instance with the actors from `factory`; return per-episode metric rows."""
    env = RescueEnv(cfg, horizon=H, b_ref=B_ref, budget_mode=mode)
    rows = []
    for k, (inst, st) in enumerate(pool.items):
        obs, masks = env.reset(inst, b0, statics=st, record=True)
        actors = factory(inst, StaticContext.from_env(env), k)
        while not env.done:
            acts = [a.act(obs[i], masks[i], env.view(i) if a.needs_view else None) for i, a in enumerate(actors)]
            obs, masks, _, _, _ = env.step(acts)
        rows.append(episode_record(inst, st, env.log, env.costs, env.r_v, **labels))
    return rows


def mismatch_permutations(n_seeds: int = 10, rounds: int = 2) -> list[tuple[list[int], list[int]]]:
    """A1 (spec §5): per round, permutations sigma2, sigma3 of the seeds with s, sigma2(s), sigma3(s) all distinct.
    Drawn by rejection sampling from a fixed RNG (SeedSequence(0xA1)); recorded in the A1 outputs."""
    rng = np.random.default_rng(np.random.SeedSequence(0xA1))
    out = []
    while len(out) < rounds:
        s2, s3 = rng.permutation(n_seeds), rng.permutation(n_seeds)
        if all(len({s, int(s2[s]), int(s3[s])}) == 3 for s in range(n_seeds)):
            out.append((s2.tolist(), s3.tolist()))
    return out


def run_dir(block: str, level: str, seed: int, slot: int | None = None) -> Path:
    tail = f"seed_{seed}" + (f"_slot{slot}" if slot is not None else "")
    return ROOT / "results" / "runs" / block / level / tail


def load_q(block: str, level: str, seed: int, which: str = "final") -> list[np.ndarray]:
    """Per-slot Q-tables of a trained team (solo block: three single-agent runs combined)."""
    if block == "solo":
        return [np.load(run_dir(block, level, seed, k) / f"q_{which}.npz")["Q"][0] for k in range(3)]
    Q = np.load(run_dir(block, level, seed) / f"q_{which}.npz")["Q"]
    return [Q[i] for i in range(Q.shape[0])]
