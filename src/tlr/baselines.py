"""Decentralized baseline policies: random, greedy (individually myopic), hand-designed cooperative.

Implements: spec §2.2 (baselines). All three are DECENTRALIZED and use exactly the information learners have
(spec §1.3a): each agent's controller sees only its own `AgentView` and its own mask at each step, plus static knowledge
(map tables, costs, n, H, its own index) via `StaticContext`. Controllers may remember their own past views (that is
the agent's own observation history) but never receive the environment object. Masking applies identically to all.

Design choices that the spec left open are documented in docs/design_decisions.md (D19).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from .costs import Action, CostModel
from .mapgen import MapStatics
from .observation import AgentView

A = Action


@dataclass(frozen=True)
class StaticContext:
    """Static, a-priori knowledge every agent has (spec §1.3a): map tables, costs, team size, horizon, radii."""

    n: int
    H: int
    L: int
    base: int
    st: MapStatics
    costs: CostModel
    r_s: int
    r_tm: int

    @classmethod
    def from_env(cls, env) -> "StaticContext":
        return cls(n=env.n, H=env.H, L=env.inst.L, base=env.inst.base, st=env.st, costs=env.costs,
                   r_s=env.r_s, r_tm=env.r_tm)


class TeamPolicy(Protocol):
    """A team policy maps the n agents' views and masks to n actions."""

    name: str
    full_information: bool

    def begin_episode(self, ctx: StaticContext, seed: int) -> None: ...

    def act(self, views: list[AgentView], masks: np.ndarray) -> list[int]: ...


class AgentController(Protocol):
    def act(self, view: AgentView, mask: np.ndarray) -> int: ...


class DecentralizedTeam:
    """n independent controllers; controller i only ever sees views[i] and masks[i]."""

    full_information = False

    def __init__(self, name: str, factory: Callable[[int, StaticContext, int], AgentController]) -> None:
        self.name = name
        self.factory = factory
        self.ctrls: list[AgentController] = []

    def begin_episode(self, ctx: StaticContext, seed: int) -> None:
        self.ctrls = [self.factory(i, ctx, seed) for i in range(ctx.n)]

    def act(self, views: list[AgentView], masks: np.ndarray) -> list[int]:
        return [int(c.act(v, m)) for c, v, m in zip(self.ctrls, views, masks)]


# ----------------------------------------------------------------------------------------------------------------
# Shared helpers (used identically by greedy and cooperative so their only difference is the cooperation rules)
# ----------------------------------------------------------------------------------------------------------------

SEARCH_UNOBSERVED_FRACTION = 0.5  # SEARCH when >= 50% of the footprint is unobserved by this agent (spec §2.2)


def move_towards(ctx: StaticContext, pos: int, target: int, mask: np.ndarray) -> int | None:
    """First action on the cheapest path to `target`, if it is valid; None otherwise."""
    if target == pos:
        return None
    a = int(ctx.st.first_move[pos, target])
    return a if a >= 0 and mask[a] else None


def explore(ctx: StaticContext, view: AgentView, mask: np.ndarray, region: np.ndarray | None = None,
            allow_search: bool = True) -> int:
    """SEARCH if the footprint is mostly unobserved (and `allow_search`), else walk to the nearest unobserved cell
    (preferring `region`)."""
    st, pos = ctx.st, view.pos
    fp = st.views[ctx.r_s][pos]
    if allow_search and mask[A.SEARCH] and np.mean(~view.observed[fp]) >= SEARCH_UNOBSERVED_FRACTION:
        return int(A.SEARCH)
    unobs = st.free & ~view.observed
    cand = np.flatnonzero(unobs & region) if region is not None else np.array([], dtype=np.int64)
    if cand.size == 0:
        cand = np.flatnonzero(unobs)
    if cand.size:
        target = int(cand[int(np.argmin(st.dist[pos, cand]))])  # ties -> lowest cell index
        a = move_towards(ctx, pos, target, mask)
        if a is not None:
            return a
    return int(A.WAIT)


# ----------------------------------------------------------------------------------------------------------------
# Random
# ----------------------------------------------------------------------------------------------------------------

class RandomController:
    """Uniformly random valid action. Seeded per (episode seed, agent index) for reproducibility."""

    def __init__(self, i: int, ctx: StaticContext, seed: int) -> None:
        self.rng = np.random.default_rng(np.random.SeedSequence([int(seed), int(i), 0xA11]))

    def act(self, view: AgentView, mask: np.ndarray) -> int:
        return int(self.rng.choice(np.flatnonzero(mask)))


# ----------------------------------------------------------------------------------------------------------------
# Greedy (individually myopic)
# ----------------------------------------------------------------------------------------------------------------

class GreedyController:
    """Individually greedy: chase the nearest affordable known victim (LIGHT first at equal cost), RESCUE it, never ASSIST.

    A heavy victim is attempted at most once: after a failed solo RESCUE the agent (which can see the victim is still
    there) never targets it again. Without this rule greedy would burn its whole budget retrying, which is a degenerate
    strawman rather than a myopic-but-sensible policy.
    """

    def __init__(self, i: int, ctx: StaticContext, seed: int) -> None:
        self.i, self.ctx = i, ctx
        self.failed_heavy: set[int] = set()

    def act(self, view: AgentView, mask: np.ndarray) -> int:
        ctx, st, pos = self.ctx, self.ctx.st, view.pos
        here = view.known.get(pos)
        if here is not None and mask[A.RESCUE]:
            vid, heavy = here
            if not heavy:
                return int(A.RESCUE)
            if vid not in self.failed_heavy:
                self.failed_heavy.add(vid)
                return int(A.RESCUE)
        best = None
        for cell, (vid, heavy) in view.known.items():
            if cell == pos or (heavy and vid in self.failed_heavy):
                continue
            d = int(st.dist[pos, cell])
            if d + ctx.costs.rescue > view.spendable:
                continue  # cannot afford to get there and rescue
            key = (d, heavy, cell)  # LIGHT (False) sorts before HEAVY at equal cost
            if best is None or key < best:
                best = key
        if best is not None:
            a = move_towards(ctx, pos, best[2], mask)
            if a is not None:
                return a
        return explore(ctx, view, mask)


# ----------------------------------------------------------------------------------------------------------------
# Hand-designed cooperative
# ----------------------------------------------------------------------------------------------------------------

def sector_partition(st: MapStatics, n: int, iters: int = 25) -> np.ndarray:
    """Split free cells into n sectors with a deterministic k-means (spec §2.2(a)); returns sector id per cell (-1 walls).

    Initialisation: farthest-point seeding starting from the free cell with the lowest index; Euclidean distance on
    (row, col); ties broken by lowest index. Sectors are numbered by centroid (row, col) order, and agent i explores
    sector i. Every agent computes this from the known map, so all agents agree without communication.
    """
    L = st.L
    free = np.flatnonzero(st.free)
    xy = np.stack([free // L, free % L], axis=1).astype(float)
    centers = [xy[0]]
    for _ in range(1, n):
        d = np.min([np.sum((xy - c) ** 2, axis=1) for c in centers], axis=0)
        centers.append(xy[int(np.argmax(d))])
    C = np.array(centers)
    for _ in range(iters):
        d = np.stack([np.sum((xy - c) ** 2, axis=1) for c in C], axis=1)
        lab = np.argmin(d, axis=1)
        newC = np.array([xy[lab == k].mean(axis=0) if np.any(lab == k) else C[k] for k in range(n)])
        if np.allclose(newC, C):
            break
        C = newC
    d = np.stack([np.sum((xy - c) ** 2, axis=1) for c in C], axis=1)
    lab = np.argmin(d, axis=1)
    order = sorted(range(n), key=lambda k: (C[k][0], C[k][1], k))
    rank = {k: r for r, k in enumerate(order)}
    out = np.full(L * L, -1, dtype=np.int64)
    out[free] = [rank[int(k)] for k in lab]
    return out


class CooperativeController:
    """Hand-designed cooperative policy (spec §2.2): sectors, light rescues, wait at heavy victims, help waiting
    teammates, and a role convention for joint rescues. Priority order each step:

    1. On a waiting HEAVY victim with >= 1 teammate on the cell: lowest index present RESCUEs, others ASSIST.
    2. On a LIGHT victim: RESCUE.
    3. On a HEAVY victim alone: WAIT for a helper, up to W = 2L steps (only if it can afford either role, >= c_R);
       after the timeout it stops waiting at that victim (it can still be helped if someone else waits there).
    4. Help signal: a teammate seen on the same cell in 3 consecutive own views (stationary for 2 steps) within r_tm
       -> walk to it. Arriving at a cell without a heavy victim marks it a false alarm (never chased again).
    5. Walk to the nearest affordable known LIGHT victim not already occupied by a visible teammate.
    6. Walk to the nearest affordable known HEAVY victim not timed out (then 3. applies).
    7. Explore: own sector first (same SEARCH rule as greedy), then anywhere. Search convention (D19/P7): an agent
       does not SEARCH while a lower-index teammate stands on the same cell (that teammate searches; the others move
       on), so co-located agents never search the same footprint simultaneously (e.g. all three at the base at t = 0).
    """

    def __init__(self, i: int, ctx: StaticContext, seed: int, sectors: np.ndarray | None = None) -> None:
        self.i, self.ctx = i, ctx
        self.W = 2 * ctx.L
        sectors = sectors if sectors is not None else sector_partition(ctx.st, ctx.n)
        self.region = sectors == i
        self.hist: deque[dict[int, int]] = deque(maxlen=3)
        self.wait_count: dict[int, int] = {}
        self.timed_out: set[int] = set()
        self.help_target: int | None = None
        self.false_alarm: set[int] = set()

    def act(self, view: AgentView, mask: np.ndarray) -> int:
        ctx, st, pos, c = self.ctx, self.ctx.st, view.pos, self.ctx.costs
        self.hist.append({j: cell for j, cell in view.teammates})
        here = view.known.get(pos)
        mates_here = [j for j, cell in view.teammates if cell == pos]

        if here is not None:
            vid, heavy = here
            if heavy:
                if mates_here:                                                     # rule 1
                    role = A.RESCUE if self.i < min(mates_here) else A.ASSIST
                    self.help_target = None
                    return int(role) if mask[role] else int(A.WAIT)
                if vid not in self.timed_out and view.spendable >= c.rescue:        # rule 3
                    self.wait_count[vid] = self.wait_count.get(vid, 0) + 1
                    if self.wait_count[vid] <= self.W:
                        return int(A.WAIT)
                    self.timed_out.add(vid)
            elif mask[A.RESCUE]:                                                   # rule 2
                return int(A.RESCUE)

        if self.help_target is not None and self.help_target == pos:
            self.false_alarm.add(pos)        # arrived, no heavy victim to help with here (rule 1 would have fired)
            self.help_target = None
        if self.help_target is None and len(self.hist) == 3:                        # rule 4
            cands = []
            for j, cell in view.teammates:
                if cell != pos and cell not in self.false_alarm and all(h.get(j) == cell for h in self.hist):
                    d = int(st.dist[pos, cell])
                    if d + c.assist <= view.spendable:
                        cands.append((d, cell))
            if cands:
                self.help_target = min(cands)[1]
        if self.help_target is not None:
            a = move_towards(ctx, pos, self.help_target, mask)
            if a is not None:
                return a
            self.help_target = None

        occupied = {cell for _, cell in view.teammates}
        lights, heavies = [], []
        for cell, (vid, heavy) in view.known.items():
            if cell == pos:
                continue
            d = int(st.dist[pos, cell])
            if d + c.rescue > view.spendable:
                continue
            if not heavy and cell not in occupied:
                lights.append((d, cell))
            elif heavy and vid not in self.timed_out:
                heavies.append((d, cell))
        for group in (lights, heavies):                                            # rules 5, 6
            if group:
                a = move_towards(ctx, pos, min(group)[1], mask)
                if a is not None:
                    return a
        lower_here = any(j < self.i for j in mates_here)
        return explore(ctx, view, mask, self.region, allow_search=not lower_here)   # rule 7


def make_team(name: str) -> DecentralizedTeam:
    """Factory by name: 'random', 'greedy', 'cooperative'."""
    factories: dict[str, Callable[[int, StaticContext, int], AgentController]] = {
        "random": RandomController,
        "greedy": GreedyController,
        "cooperative": lambda i, ctx, seed: CooperativeController(i, ctx, seed),
    }
    if name not in factories:
        raise ValueError(f"unknown baseline {name!r}")
    return DecentralizedTeam(name, factories[name])
