"""Independent tabular Q-learning (IQL) for the n rescue agents (spec §2.1; preregistration §3, §9).

Each agent i has its own table Q_i[o, a] (o = encoded observation tuple f1..f5, 3,960 rows; a = 8 actions) and learns from
its own reward R_i only:

    Q_i(o,a) <- Q_i(o,a) + alpha * [ R_i + gamma * (1 - done) * max_{a' valid in o'} Q_i(o',a') - Q_i(o,a) ]

- Action selection is epsilon-greedy over VALID actions only (the environment's mask); the max in the target is also over the
  next state's valid actions (the agent knows its own next mask, so this uses no hidden information).
- Ties among maximal Q-values are broken uniformly at random by the agent's own RNG (training) or by an RNG seeded with
  (instance seed, agent id) (evaluation, common random numbers: every condition and method sees the same tie-break stream).
- done = 1 on every termination (all victims rescued, budget exhaustion, horizon): the game really ends there.
- A dormant agent (budget below the cheapest costly action, only WAIT valid) makes no learnable choice, so its transitions are
  not used for updates (spec §2.1).
- Teammates are part of the environment from each learner's point of view; because they learn too, the environment is
  non-stationary for every learner. Nothing here corrects for that: measuring its consequences is the point (A1-A6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .costs import N_ACTIONS
from .observation import N_OBS


@dataclass(frozen=True)
class IQLParams:
    """Hyperparameters of spec §2.1 (frozen defaults; the pilot may change alpha, episodes and the epsilon length)."""

    alpha: float = 0.1
    gamma: float = 0.98
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_decay_fraction: float = 0.7   # epsilon reaches eps_end after this fraction of the training episodes
    episodes: int = 8000

    def epsilon_by_steps(self, steps_used: int, step_budget: int) -> float:
        """A6 equal-steps runs: the same linear decay, measured in environment steps instead of episodes
        (eps_end is reached after eps_decay_fraction of the step budget)."""
        decay = max(1, int(round(self.eps_decay_fraction * step_budget)))
        if steps_used >= decay:
            return self.eps_end
        return self.eps_start + (self.eps_end - self.eps_start) * steps_used / decay

    def epsilon(self, episode: int) -> float:
        """Linear decay from eps_start to eps_end over the first eps_decay_fraction * episodes, then constant."""
        decay = max(1, int(round(self.eps_decay_fraction * self.episodes)))
        if episode >= decay:
            return self.eps_end
        return self.eps_start + (self.eps_end - self.eps_start) * episode / decay


def masked_argmax(q: np.ndarray, mask: np.ndarray, rng: np.random.Generator) -> int:
    """argmax of q over valid actions, ties broken uniformly at random with `rng`."""
    vals = np.where(mask, q, -np.inf)
    best = vals.max()
    cands = np.flatnonzero(vals == best)
    return int(cands[0]) if len(cands) == 1 else int(cands[rng.integers(len(cands))])


def masked_max(q: np.ndarray, mask: np.ndarray) -> float:
    """max of q over valid actions (WAIT is always valid, so this is never empty)."""
    return float(np.max(q[mask]))


class IQLTeam:
    """n independent Q-tables plus their own exploration RNGs."""

    def __init__(self, n_agents: int, params: IQLParams, seed: int, q_init: float = 0.0,
                 agent_ids: list[int] | None = None) -> None:
        self.n = n_agents
        self.p = params
        self.Q = np.full((n_agents, N_OBS, N_ACTIONS), q_init, dtype=np.float64)
        # One exploration stream per agent SLOT, derived from the training seed only (identical across conditions).
        # `agent_ids` maps local agents to team slots; a solo-trained agent for slot k (A4) uses agent_ids = [k] and so
        # gets exactly the stream joint agent k gets. Default: slots 0..n-1 (unchanged Phase 4 behaviour).
        ids = list(range(n_agents)) if agent_ids is None else list(agent_ids)
        self.rngs = [np.random.default_rng(np.random.SeedSequence([int(seed), k, 0xE7])) for k in ids]

    def act(self, obs: list[int], masks: np.ndarray, epsilon: float,
            rngs: list[np.random.Generator] | None = None) -> list[int]:
        """Epsilon-greedy joint action. `rngs` overrides the training RNGs (used for CRN evaluation)."""
        rngs = rngs or self.rngs
        acts = []
        for i in range(self.n):
            r = rngs[i]
            if epsilon > 0 and r.random() < epsilon:
                acts.append(int(r.choice(np.flatnonzero(masks[i]))))
            else:
                acts.append(masked_argmax(self.Q[i, obs[i]], masks[i], r))
        return acts

    def update(self, i: int, o: int, a: int, r: float, o2: int, mask2: np.ndarray, done: bool) -> float:
        """One TD(0) update for agent i; returns the TD error."""
        target = r if done else r + self.p.gamma * masked_max(self.Q[i, o2], mask2)
        td = target - self.Q[i, o, a]
        self.Q[i, o, a] += self.p.alpha * td
        return float(td)

    def greedy_actions(self) -> np.ndarray:
        """Unmasked greedy action per (agent, observation), lowest index on ties - used only for the churn diagnostic."""
        return np.argmax(self.Q, axis=2)


def eval_rngs(instance_seed: int, n_agents: int) -> list[np.random.Generator]:
    """Evaluation tie-break RNGs seeded by (instance seed, agent): identical for every condition and method (CRN)."""
    return [np.random.default_rng(np.random.SeedSequence([int(instance_seed), i, 0xC2])) for i in range(n_agents)]
