"""Oracle REFERENCE (full-information centralized planner), a provable loose upper bound, and an exhaustive planner.

Implements: spec §1.4 (oracle reference, UB) and §2.2 (oracle).

IMPORTANT - what the oracle is and is not:
- It is NOT a learned policy and NOT decentralized. It sees the whole instance (every victim, type and budget) and
  plans for all agents jointly. Its numbers are always reported separately, labelled "oracle reference".
- It is NOT proven optimal. Exact optimisation is a multi-agent orienteering problem. The planner is a greedy
  insertion heuristic, so it is an ACHIEVABLE reference (a lower bound on the true optimum). Two checks bracket it:
  `upper_bound` (provable, loose) and `exhaustive_plan_count` (exact optimum over the same macro-plan space, feasible
  only for tiny instances; used in tests and the Phase 2 validation report).

Macro-plan model shared by the greedy and the exhaustive planner: each agent serves a sequence of victims, travelling
along cheapest paths (precomputed tables); for a heavy victim the rescuer and assister both travel there, the earlier
one WAITs (free), and both act in the same step. A plan is executed in the real environment, so every rule (masks,
costs, simultaneity, termination) applies to the oracle exactly as to everyone else.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .costs import Action, CostModel
from .mapgen import Instance, MapStatics

A = Action


@dataclass
class _AgentState:
    pos: int
    tf: int        # first step index at which the agent is free to start its next task


@dataclass(frozen=True)
class Task:
    """One planned rescue: victim, rescuer, optional assister, step index T at which the joint action happens."""

    victim: int
    rescuer: int
    assister: int | None
    T: int
    cost: int


def _options(inst: Instance, st: MapStatics, costs: CostModel, agents: list[_AgentState], budgets: list[int],
             pooled: bool, H: int, remaining: list[int]) -> list[tuple[tuple, Task, list[int]]]:
    """All feasible single-victim insertions from the current partial plan. Each item: (sort key, task, new budgets)."""
    n = len(agents)
    out = []
    for v in remaining:
        c = int(inst.victim_cells[v])
        d = [int(st.dist[a.pos, c]) for a in agents]
        s = [int(st.steps[a.pos, c]) for a in agents]
        if not inst.victim_heavy[v]:
            for i in range(n):
                cost = d[i] + costs.rescue
                T = agents[i].tf + s[i]
                if T + 1 > H:
                    continue
                nb = list(budgets)
                if pooled:
                    if cost > nb[0]:
                        continue
                    nb[0] -= cost
                else:
                    if cost > nb[i]:
                        continue
                    nb[i] -= cost
                out.append(((cost, T + 1, v, i, -1), Task(v, i, None, T, cost), nb))
        else:
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    ci, cj = d[i] + costs.rescue, d[j] + costs.assist
                    T = max(agents[i].tf + s[i], agents[j].tf + s[j])
                    if T + 1 > H:
                        continue
                    nb = list(budgets)
                    if pooled:
                        if ci + cj > nb[0]:
                            continue
                        nb[0] -= ci + cj
                    else:
                        if ci > nb[i] or cj > nb[j]:
                            continue
                        nb[i] -= ci
                        nb[j] -= cj
                    out.append(((ci + cj, T + 1, v, i, j), Task(v, i, j, T, ci + cj), nb))
    return out


def _apply(agents: list[_AgentState], inst: Instance, task: Task) -> list[_AgentState]:
    new = [_AgentState(a.pos, a.tf) for a in agents]
    c = int(inst.victim_cells[task.victim])
    for k in (task.rescuer, task.assister):
        if k is not None:
            new[k] = _AgentState(c, task.T + 1)
    return new


def greedy_insertion_plan(inst: Instance, st: MapStatics, costs: CostModel, n: int, H: int, budgets: list[int],
                          pooled: bool, start: list[int] | None = None) -> list[Task]:
    """Repeatedly insert the cheapest feasible remaining victim (ties: earliest finish, victim id, agents)."""
    agents = [_AgentState(p, 0) for p in (start or [inst.base] * n)]
    budgets = list(budgets)
    remaining = list(range(inst.n_victims))
    plan: list[Task] = []
    while remaining:
        opts = _options(inst, st, costs, agents, budgets, pooled, H, remaining)
        if not opts:
            break
        _, task, budgets = min(opts, key=lambda o: o[0])
        plan.append(task)
        agents = _apply(agents, inst, task)
        remaining.remove(task.victim)
    return plan


def exhaustive_plan_count(inst: Instance, st: MapStatics, costs: CostModel, n: int, H: int, budgets: list[int],
                          pooled: bool, max_victims: int = 4) -> int:
    """Exact maximum number of rescues over ALL macro-plans (every insertion order and assignment). Tiny instances only."""
    if inst.n_victims > max_victims:
        raise ValueError("exhaustive search is only for tiny instances")
    best = 0

    def dfs(agents: list[_AgentState], b: list[int], remaining: list[int], count: int) -> None:
        nonlocal best
        best = max(best, count)
        if count + len(remaining) <= best:
            return
        for _, task, nb in _options(inst, st, costs, agents, b, pooled, H, remaining):
            dfs(_apply(agents, inst, task), nb, [r for r in remaining if r != task.victim], count + 1)

    dfs([_AgentState(inst.base, 0) for _ in range(n)], list(budgets), list(range(inst.n_victims)), 0)
    return best


def upper_bound(inst: Instance, costs: CostModel, total_budget: int) -> int:
    """Provable loose upper bound (spec §1.4): action costs alone, free travel, perfectly shared budgets."""
    m = sorted(costs.rescue + (costs.assist if h else 0) for h in inst.victim_heavy)
    k, spent = 0, 0
    for x in m:
        if spent + x > total_budget:
            break
        spent += x
        k += 1
    return min(inst.n_victims, k)


def compile_plan(inst: Instance, st: MapStatics, n: int, plan: list[Task], start: list[int]) -> list[list[int]]:
    """Turn tasks into per-agent action sequences indexed by step (WAIT where nothing is planned)."""
    seqs: list[list[int]] = [[] for _ in range(n)]
    pos = list(start)
    tasks_by_agent: dict[int, list[tuple[Task, int]]] = {i: [] for i in range(n)}
    for task in plan:
        tasks_by_agent[task.rescuer].append((task, int(A.RESCUE)))
        if task.assister is not None:
            tasks_by_agent[task.assister].append((task, int(A.ASSIST)))
    for i in range(n):
        for task, act in sorted(tasks_by_agent[i], key=lambda x: x[0].T):
            c = int(inst.victim_cells[task.victim])
            while pos[i] != c:
                a = int(st.first_move[pos[i], c])
                seqs[i].append(a)
                pos[i] = int(st.move_target[pos[i], a])
            while len(seqs[i]) < task.T:
                seqs[i].append(int(A.WAIT))
            assert len(seqs[i]) == task.T, "plan timing inconsistent"
            seqs[i].append(act)
    return seqs


class OraclePolicy:
    """Full-information centralized oracle REFERENCE (not a learner, not decentralized)."""

    name = "oracle"
    full_information = True

    def plan(self, env) -> None:
        """Plan from the true initial state of the episode (all victims, types, budgets)."""
        pooled = env.mode == "pooled"
        budgets = [int(b) for b in env.budget]
        start = [int(p) for p in env.pos]
        self.tasks = greedy_insertion_plan(env.inst, env.st, env.costs, env.n, env.H, budgets, pooled, start)
        self.seqs = compile_plan(env.inst, env.st, env.n, self.tasks, start)
        self.t = 0

    def begin_episode(self, ctx, seed: int) -> None:  # pragma: no cover - never called for full-information policies
        raise RuntimeError("the oracle must be planned with full information via plan(env)")

    def act(self, views, masks: np.ndarray) -> list[int]:
        acts = [seq[self.t] if self.t < len(seq) else int(A.WAIT) for seq in self.seqs]
        for i, a in enumerate(acts):
            if not masks[i, a]:
                raise RuntimeError(f"oracle plan produced a masked action (agent {i}, t {self.t}, action {a})")
        self.t += 1
        return acts

    @property
    def planned_rescues(self) -> int:
        return len(self.tasks)
