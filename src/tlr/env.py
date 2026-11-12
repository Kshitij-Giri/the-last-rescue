"""The Last Rescue environment: a finite-horizon, partially observed, resource-constrained Markov game.

Implements spec §1 end to end:
- §1.2 actions/costs and masking (masks come from observation.compute_mask on the agent's own view);
- §1.3 simultaneous transition: pay -> move -> resolve RESCUE/ASSIST -> observe -> t+1 -> terminate?;
- §1.3a information discipline, stale memory, re-validation of actions (InvalidActionError), event logging;
- §1.4 dormancy and termination (all_rescued, exhausted, horizon);
- §1.5 pooled-budget ablation (rotating payment priority, preemption, spendable pool vs per-capita feature);
- §1.6 reward components (combined in rewards.py).

API (not Gym, deliberately small):
    env = RescueEnv(cfg, horizon=H, b_ref=B_ref)
    obs, masks = env.reset(instance, b0)          # obs: list[int] (encoded f1..f5), masks: (n, 8) bool
    obs, masks, R, done, info = env.step(actions)  # actions: sequence of n ints
The environment itself is deterministic given actions; it owns no random generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .costs import Action, CostModel, N_ACTIONS
from .mapgen import Instance, MapStatics, compute_statics
from .observation import (AgentView, budget_thresholds, compute_mask, encode, features,
                          nearest_known_victim)
from .rewards import RewardComponents, RewardModel, combine


class InvalidActionError(ValueError):
    """Raised when an agent submits an action outside the mask the environment issued for it (spec §1.3a item 5)."""


TERMINATION_REASONS = ("all_rescued", "exhausted", "horizon")


@dataclass
class EpisodeLog:
    """Per-step record of an episode, used by metrics (Phase 2), replays and verification.

    All per-step lists have one entry per executed step. `positions` has one more entry (the state after the last step).
    Budgets: shape (n,) per entry in per-agent mode; a single-element array (the pool) in pooled mode.
    """

    n_agents: int
    budget_mode: str
    horizon: int
    b0: int
    instance_seed: int | None
    positions: list[np.ndarray] = field(default_factory=list)
    budgets: list[np.ndarray] = field(default_factory=list)
    actions: list[np.ndarray] = field(default_factory=list)            # requested actions
    effective_actions: list[np.ndarray] = field(default_factory=list)  # after pooled preemption
    costs: list[np.ndarray] = field(default_factory=list)              # cost actually paid
    rewards: list[np.ndarray] = field(default_factory=list)
    r_ind: list[np.ndarray] = field(default_factory=list)
    r_team: list[float] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    # f1 target victim id of each agent at the start of each step (-1 = none); one more entry than steps.
    # This is the agent's OWN belief (used offline for the stale-travel diagnostic, spec §1.3a).
    f1_targets: list[np.ndarray] = field(default_factory=list)
    initial_budgets: np.ndarray | None = None
    termination: str | None = None
    steps: int = 0


class RescueEnv:
    """Multi-agent search-and-rescue grid world with integer resource budgets."""

    def __init__(self, cfg: dict[str, Any], horizon: int, b_ref: int, budget_mode: str | None = None,
                 n_agents: int | None = None) -> None:
        e = cfg["env"]
        self.cfg = cfg
        self.n = int(n_agents if n_agents is not None else e["n_agents"])
        self.H = int(horizon)
        self.b_ref = int(b_ref)
        self.mode = budget_mode or cfg["budget"]["mode"]
        if self.mode not in ("per_agent", "pooled"):
            raise ValueError(f"unknown budget mode {self.mode!r}")
        if self.H < 1:
            raise ValueError("horizon must be >= 1")
        self.r_v = int(e["radius_passive"])
        self.r_s = int(e["radius_search"])
        self.r_tm = int(e["radius_teammate"])
        self.near_steps = int(e["near_steps"])
        self.costs = CostModel.from_config(cfg)
        self.rewards = RewardModel.from_config(cfg)
        self.thresholds = budget_thresholds(self.b_ref, self.costs.c_rescue)
        self.done = True

    # ------------------------------------------------------------------------------------------------------------
    # Episode control
    # ------------------------------------------------------------------------------------------------------------
    def reset(self, instance: Instance, b0: int, statics: MapStatics | None = None,
              start_positions: Sequence[int] | None = None, budgets: Sequence[int] | None = None,
              record: bool = True) -> tuple[list[int], np.ndarray]:
        """Start an episode on `instance` with initial per-agent budget b0 (pooled: pool = n * b0).

        `statics` may be passed to reuse precomputed tables for the same map (they depend only on the map and costs).
        `start_positions` and `budgets` are TEST/SCENARIO HOOKS ONLY (hand-written scripted episodes); experiments
        always start every agent on the base with equal budgets b0. In pooled mode `budgets` is a 1-element pool.
        """
        self.inst = instance
        self.st = statics if statics is not None else compute_statics(instance, self.costs,
                                                                      [self.r_v, self.r_s])
        L = instance.L
        V = instance.n_victims
        self.b0 = int(b0)
        self.pos = np.array(start_positions if start_positions is not None else [instance.base] * self.n,
                            dtype=np.int64)
        if len(self.pos) != self.n or not all(self.st.free[p] for p in self.pos):
            raise ValueError("invalid start positions")
        if self.mode == "per_agent":
            self.budget = np.array(budgets if budgets is not None else [self.b0] * self.n, dtype=np.int64)
            if len(self.budget) != self.n:
                raise ValueError("need one budget per agent")
        else:
            self.budget = np.array(budgets if budgets is not None else [self.n * self.b0], dtype=np.int64)
            if len(self.budget) != 1:
                raise ValueError("pooled mode takes a single pool value")
        if (self.budget < 0).any():
            raise ValueError("budgets must be non-negative")

        self.cell_to_vid = np.full(L * L, -1, dtype=np.int64)
        self.cell_to_vid[instance.victim_cells] = np.arange(V)
        self.v_rescued = np.zeros(V, dtype=bool)
        self.v_rescue_t = np.full(V, -1, dtype=np.int64)
        self.v_participants: list[frozenset[int]] = [frozenset()] * V
        self.team_seen = np.zeros(V, dtype=bool)
        self.observed = [np.zeros(L * L, dtype=bool) for _ in range(self.n)]
        self.known: list[dict[int, tuple[int, bool]]] = [{} for _ in range(self.n)]
        self.dormant = np.zeros(self.n, dtype=bool)
        self.t = 0
        self.done = False
        self.termination: str | None = None
        self.record = record
        self.log = EpisodeLog(self.n, self.mode, self.H, self.b0, instance.seed) if record else None
        if self.log is not None:
            self.log.initial_budgets = self.budget.copy()
        self._step_events: list[dict[str, Any]] = []

        # Initial observation of the start cells. No reward: rewards are paid on transitions only.
        first_obs: dict[int, list[int]] = {}
        for i in range(self.n):
            self._observe(i, self.st.views[self.r_v][self.pos[i]], first_obs)
        for vid in first_obs:
            self.team_seen[vid] = True
            self._event({"type": "initial_sighting", "victim": int(vid), "agents": first_obs[vid]})
        self._update_dormancy()
        if self.log is not None:
            self.log.positions.append(self.pos.copy())
            self.log.budgets.append(self.budget.copy())
            self.log.events.extend(self._step_events)
        self._step_events = []
        self._check_termination()
        return self._observe_all()

    def step(self, actions: Sequence[int]) -> tuple[list[int], np.ndarray, np.ndarray, bool, dict[str, Any]]:
        """Execute one simultaneous joint action (spec §1.3)."""
        if self.done:
            raise RuntimeError("step() called on a finished episode; call reset()")
        acts = np.asarray(actions, dtype=np.int64)
        if acts.shape != (self.n,):
            raise ValueError(f"expected {self.n} actions, got shape {acts.shape}")
        for i, a in enumerate(acts):
            # Re-validate against the mask issued at the previous observation (spec §1.3a item 5).
            if not (0 <= a < N_ACTIONS) or not self.masks[i, a]:
                raise InvalidActionError(f"agent {i} chose {a} which is not in its mask {self.masks[i].astype(int)}")
        st, t, n = self.st, self.t, self.n
        self._step_events = []

        # 1. Payment.
        req = np.array([self.costs.action_cost(int(a), int(st.entry_cost[st.move_target[self.pos[i], a]])
                                               if a <= Action.RIGHT else 0) for i, a in enumerate(acts)],
                       dtype=np.int64)
        eff = acts.copy()
        paid = np.zeros(n, dtype=np.int64)
        if self.mode == "per_agent":
            self.budget -= req  # every action is affordable by construction of the mask
            paid[:] = req
        else:
            # Rotating priority (t mod n), (t+1 mod n), ... avoids systematically favouring agent 0 (spec §1.5).
            for k in range(n):
                i = (t + k) % n
                if req[i] <= self.budget[0]:
                    self.budget[0] -= req[i]
                    paid[i] = req[i]
                else:
                    eff[i] = Action.WAIT
                    self._event({"type": "preempted", "agent": i, "action": int(acts[i]), "cost": int(req[i]),
                                 "pool_left": int(self.budget[0])})
        assert (self.budget >= 0).all()
        pos_before = self.pos.copy()

        # 2. Moves (agents may share cells).
        for i in range(n):
            if eff[i] <= Action.RIGHT:
                self.pos[i] = st.move_target[self.pos[i], eff[i]]

        # 3. RESCUE / ASSIST resolution, per cell (these agents did not move, so ordering with step 2 is irrelevant).
        V = self.inst.n_victims
        light = np.zeros(n)
        h_res = np.zeros(n)
        h_ass = np.zeros(n)
        n_rescued = 0
        by_cell: dict[int, tuple[list[int], list[int]]] = {}
        for i in range(n):
            if eff[i] == Action.RESCUE or eff[i] == Action.ASSIST:
                by_cell.setdefault(int(self.pos[i]), ([], []))[0 if eff[i] == Action.RESCUE else 1].append(i)
        for cell, (R, A) in sorted(by_cell.items()):
            vid = int(self.cell_to_vid[cell])
            # The mask was built from the agent's fresh view of its own cell, so the victim must be waiting.
            assert vid >= 0 and not self.v_rescued[vid], "mask/observation invariant violated"
            heavy = bool(self.inst.victim_heavy[vid])
            rescued = False
            if not heavy:
                assert not A, "ASSIST on a light victim cannot pass the mask"
                if R:
                    rescued = True
                    for i in R:
                        light[i] += 1.0 / len(R)
                    if len(R) > 1:
                        self._event({"type": "duplicate_rescue", "victim": vid, "cell": cell, "agents": R,
                                     "n_wasted": len(R) - 1})
            else:
                if R and A:
                    rescued = True
                    for i in R:
                        h_res[i] += 1.0 / len(R)
                    for i in A:
                        h_ass[i] += 1.0 / len(A)
                else:
                    for i in R:
                        self._event({"type": "failed_rescue", "agent": i, "victim": vid, "cell": cell})
                    for i in A:
                        self._event({"type": "failed_assist", "agent": i, "victim": vid, "cell": cell})
            if rescued:
                self.v_rescued[vid] = True
                self.v_rescue_t[vid] = t
                self.v_participants[vid] = frozenset(R + A)
                n_rescued += 1
                self._event({"type": "rescue", "victim": vid, "heavy": heavy, "cell": cell,
                             "rescuers": R, "assisters": A})

        # 4. Observation update on the post-transition state.
        first_obs: dict[int, list[int]] = {}
        for i in range(n):
            self._observe(i, st.views[self.r_v][self.pos[i]], first_obs)
            if eff[i] == Action.SEARCH:
                fp = st.views[self.r_s][self.pos[i]]
                self._event({"type": "search", "agent": i, "cell": int(self.pos[i]), "footprint": fp.tolist()})
                self._observe(i, fp, first_obs)
        disc = np.zeros(n)
        for vid, obs_agents in first_obs.items():
            self.team_seen[vid] = True
            for i in obs_agents:
                disc[i] += 1.0 / len(obs_agents)
            self._event({"type": "first_sighting", "victim": int(vid), "agents": obs_agents})

        # 5. Rewards, time, dormancy, termination.
        comp = RewardComponents(disc, light, h_res, h_ass, n_rescued, paid)
        R_vec, r_ind, r_team = combine(self.rewards, comp)
        self.t += 1
        self._update_dormancy()
        self._check_termination()
        if self.log is not None:
            self.log.actions.append(acts.copy())
            self.log.effective_actions.append(eff.copy())
            self.log.costs.append(paid.copy())
            self.log.rewards.append(R_vec.copy())
            self.log.r_ind.append(r_ind.copy())
            self.log.r_team.append(r_team)
            self.log.positions.append(self.pos.copy())
            self.log.budgets.append(self.budget.copy())
            self.log.events.extend(self._step_events)
            self.log.steps = self.t
            self.log.termination = self.termination
        obs, masks = self._observe_all()
        info = {"t": self.t, "termination": self.termination, "events": self._step_events,
                "effective_actions": eff, "paid": paid, "r_ind": r_ind, "r_team": r_team,
                "pos_before": pos_before, "n_rescued_step": n_rescued}
        return obs, masks, R_vec, self.done, info

    # ------------------------------------------------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------------------------------------------------
    def _event(self, ev: dict[str, Any]) -> None:
        ev = {"t": self.t, **ev}
        self._step_events.append(ev)

    def _observe(self, i: int, cells: np.ndarray, first_obs: dict[int, list[int]]) -> None:
        """Agent i observes `cells`: its memory for those cells is overwritten with the true current contents."""
        obs_mask = self.observed[i]
        known = self.known[i]
        for c in cells:
            c = int(c)
            obs_mask[c] = True
            vid = int(self.cell_to_vid[c])
            if vid >= 0 and not self.v_rescued[vid]:
                known[c] = (vid, bool(self.inst.victim_heavy[vid]))
                if not self.team_seen[vid]:
                    lst = first_obs.setdefault(vid, [])
                    if i not in lst:
                        lst.append(i)
            elif c in known:
                old_vid, _ = known.pop(c)
                # Memory said "waiting", truth says rescued: a stale belief is corrected (spec §1.3a item 2).
                # Participants of the rescue learn it in the same transition; that is not staleness.
                if i not in self.v_participants[old_vid]:
                    self._event({"type": "stale_correction", "agent": i, "victim": old_vid, "cell": c,
                                 "steps_since_rescue": int(self.t - self.v_rescue_t[old_vid])})

    def _update_dormancy(self) -> None:
        """Agent is dormant iff its spendable budget < c_min (only WAIT remains valid)."""
        c_min = self.costs.c_min
        for i in range(self.n):
            spend = self.budget[i] if self.mode == "per_agent" else self.budget[0]
            if spend < c_min and not self.dormant[i]:
                self.dormant[i] = True
                self._event({"type": "dormant", "agent": i})

    def _check_termination(self) -> None:
        """Order: all_rescued, exhausted (no agent can pay for RESCUE), horizon (spec §1.4)."""
        if self.v_rescued.all():
            self.termination = "all_rescued"
        elif int(self.budget.max()) < self.costs.c_rescue:
            self.termination = "exhausted"
        elif self.t >= self.H:
            self.termination = "horizon"
        else:
            return
        self.done = True
        if self.log is not None:
            self.log.termination = self.termination
            self.log.steps = self.t

    def view(self, i: int) -> AgentView:
        """Build agent i's legitimate view (spec §1.3a). The ONLY bridge from env state to policy inputs and masks."""
        if self.mode == "per_agent":
            spend = int(self.budget[i])
            feat = spend
        else:
            spend = int(self.budget[0])
            feat = spend // self.n  # per-capita share: feature only, never used for feasibility (P4)
        L = self.inst.L
        r, c = divmod(int(self.pos[i]), L)
        mates = []
        for j in range(self.n):
            if j != i:
                rj, cj = divmod(int(self.pos[j]), L)
                if max(abs(rj - r), abs(cj - c)) <= self.r_tm:
                    mates.append((j, int(self.pos[j])))
        # Policies get a COPY of the memory dict and a read-only view of the observed mask, so no policy can
        # modify environment state (a policy bug cannot leak into ground truth).
        obs_ro = self.observed[i].view()
        obs_ro.flags.writeable = False
        return AgentView(agent_id=i, pos=int(self.pos[i]), t=self.t, horizon=self.H, spendable=spend,
                         budget_feature_value=feat, known=dict(self.known[i]), observed=obs_ro,
                         teammates=mates)

    def features(self, i: int) -> tuple[int, ...]:
        """Agent i's observation tuple (f1..f5) - convenience for tests and analysis."""
        return features(self.view(i), self.st, self.thresholds, self.near_steps)

    def _observe_all(self) -> tuple[list[int], np.ndarray]:
        obs = []
        masks = np.zeros((self.n, N_ACTIONS), dtype=bool)
        targets = np.full(self.n, -1, dtype=np.int64)
        for i in range(self.n):
            v = self.view(i)
            obs.append(encode(features(v, self.st, self.thresholds, self.near_steps)))
            masks[i] = compute_mask(v, self.st, self.costs)
            if self.log is not None:
                tgt = nearest_known_victim(v, self.st)
                targets[i] = -1 if tgt is None else tgt[1]
        self.masks = masks
        if self.log is not None:
            self.log.f1_targets.append(targets)
        return obs, masks.copy()

    # Ground-truth accessors (for evaluation, oracle and tests; never used to build observations or masks).
    @property
    def n_rescued(self) -> int:
        return int(self.v_rescued.sum())

    @property
    def coverage(self) -> float:
        """Fraction of free cells observed by at least one agent."""
        union = np.logical_or.reduce(self.observed) & self.st.free
        return float(union.sum()) / self.st.n_free
