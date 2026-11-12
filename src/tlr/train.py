"""IQL training runs with validation checkpoints and non-stationarity diagnostics (spec §2.1, §5 A5; preregistration §3, §6).

One run = one (configuration, budget level, budget mode, training seed, hyperparameters). It
  - draws training instances from a frozen training pool in a seed-determined order (identical across conditions -> CRN),
  - trains an IQLTeam with masked epsilon-greedy and TD(0) updates,
  - every `checkpoint_every` episodes (and before training) evaluates the greedy policy (epsilon = 0, CRN tie-breaks) on a
    frozen VALIDATION instance list and logs: rescue fraction, cooperation metrics, policy churn, mean |TD error|,
  - saves the final Q-tables (primary policy) and the best-on-validation Q-tables (sensitivity), plus CSV logs.
Test and shifted-test instances are never touched here.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .costs import CostModel
from .env import RescueEnv
from .iql import IQLParams, IQLTeam, eval_rngs
from .mapgen import Instance, MapStatics, compute_statics, generate_instance
from .metrics import episode_record


class InstancePool:
    """Instances (and their static tables) for a frozen list of seeds under one configuration."""

    def __init__(self, cfg: dict[str, Any], seeds: list[int]) -> None:
        cm = CostModel.from_config(cfg)
        r = [int(cfg["env"]["radius_passive"]), int(cfg["env"]["radius_search"])]
        self.items: list[tuple[Instance, MapStatics]] = []
        for s in seeds:
            inst = generate_instance(cfg, int(s))
            self.items.append((inst, compute_statics(inst, cm, r)))

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, k: int) -> tuple[Instance, MapStatics]:
        return self.items[k]


@dataclass
class RunSpec:
    """Everything that defines a training run (written to run.json)."""

    name: str
    seed: int
    b0: int
    horizon: int
    b_ref: int
    budget_mode: str = "per_agent"
    params: IQLParams = field(default_factory=IQLParams)
    checkpoint_every: int = 500
    n_agents: int | None = None          # None -> config value; 1 for A4 solo training
    agent_ids: list[int] | None = None   # exploration-stream slots (A4 solo agent k -> [k])
    max_env_steps: int | None = None     # A6: train until this many environment steps (epsilon scheduled by steps)


def episode_order(seed: int, pool_size: int, episodes: int) -> np.ndarray:
    """Training-instance index for each episode: a fresh permutation of the pool per epoch, from the seed only."""
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), 0x0D]))
    epochs = -(-episodes // pool_size)
    return np.concatenate([rng.permutation(pool_size) for _ in range(epochs)])[:episodes]


class EpisodeOrder:
    """Unbounded version of episode_order (same sequence, prefix-consistent), for step-budget runs (A6)."""

    def __init__(self, seed: int, pool_size: int) -> None:
        self.rng = np.random.default_rng(np.random.SeedSequence([int(seed), 0x0D]))
        self.n = pool_size
        self.buf: list[int] = []

    def __getitem__(self, e: int) -> int:
        while len(self.buf) <= e:
            self.buf.extend(self.rng.permutation(self.n).tolist())
        return self.buf[e]


def train_episode(env: RescueEnv, team: IQLTeam, inst: Instance, st: MapStatics, b0: int, eps: float
                  ) -> dict[str, Any]:
    """Play and learn one episode. Returns per-episode training statistics."""
    obs, masks = env.reset(inst, b0, statics=st, record=False)
    ret = np.zeros(team.n)
    td_abs, n_upd, heavy = 0.0, 0, 0
    while not env.done:
        dormant = env.dormant.copy()
        acts = team.act(obs, masks, eps)
        obs2, masks2, R, done, info = env.step(acts)
        ret += R
        heavy += sum(1 for e in info["events"] if e["type"] == "rescue" and e["heavy"])
        for i in range(team.n):
            if not dormant[i]:  # a dormant agent had no choice (only WAIT): nothing to learn (spec §2.1)
                td_abs += abs(team.update(i, obs[i], acts[i], float(R[i]), obs2[i], masks2[i], done))
                n_upd += 1
        obs, masks = obs2, masks2
    return {"steps": env.t, "rescued": env.n_rescued, "rescued_heavy": heavy, "V": inst.n_victims,
            "termination": env.termination, "collective_return": float(ret.sum()),
            "mean_abs_td": td_abs / n_upd if n_upd else 0.0, "updates": n_upd}


def evaluate_team(env: RescueEnv, team: IQLTeam, pool: InstancePool, b0: int, labels: dict[str, Any] | None = None
                  ) -> tuple[list[dict[str, Any]], list[set[int]]]:
    """Greedy (epsilon = 0) evaluation with CRN tie-breaks; returns per-episode metric rows and visited observations."""
    rows, visited = [], [set() for _ in range(team.n)]
    for k, (inst, st) in enumerate(pool.items):
        obs, masks = env.reset(inst, b0, statics=st, record=True)
        # CRN tie-breaks keyed by the instance seed (hand-written test instances have none: use their list position)
        rngs = eval_rngs(inst.seed if inst.seed is not None else k, team.n)
        while not env.done:
            for i in range(team.n):
                visited[i].add(int(obs[i]))
            acts = team.act(obs, masks, 0.0, rngs=rngs)
            obs, masks, _, _, _ = env.step(acts)
        rows.append(episode_record(inst, st, env.log, env.costs, env.r_v, **(labels or {})))
    return rows, visited


def _pooled_ratio(df: pd.DataFrame, num: str, den: str) -> float:
    d = df[den].sum()
    return float(df[num].sum() / d) if d else float("nan")


def summarize_eval(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Seed-level values (preregistration §3): means for per-episode metrics, pooled ratios for ratio metrics."""
    df = pd.DataFrame(rows)
    return {"rf": float(df.rf.mean()), "ms": float(df.ms.mean()), "rescued_heavy_share":
            float(df.rescued_heavy.sum() / df.n_heavy.sum()) if df.n_heavy.sum() else float("nan"),
            "rescued_light_share": float(df.rescued_light.sum() / (df.V - df.n_heavy).sum()),
            "collective_return": float(df.collective_return.mean()),
            "ear": _pooled_ratio(df, "ear_num", "ear_den"), "assist_actions": int(df.ear_den.sum()),
            "rsr": float((df.rsr_other_num.sum() + df.rsr_self_num.sum()) / df.rsr_den.sum())
            if df.rsr_den.sum() else float("nan"),
            "rsr_other": _pooled_ratio(df, "rsr_other_num", "rsr_den"), "tdi": float(df.tdi.mean()),
            "gini_consumption": float(df.gini_consumption.mean()),
            "pss": _pooled_ratio(df, "pss_num", "pss_den"), "cr": _pooled_ratio(df, "cr_num", "cr_den"),
            "e1_abandonment": float(df.e1_abandonment.mean()), "e2_duplicate": float(df.e2_duplicate.mean()),
            "failed_rescue": float(df.failed_rescue.mean()), "steps": float(df.steps.mean()),
            "exhausted": float((df.termination == "exhausted").mean()),
            "horizon": float((df.termination == "horizon").mean()), "coverage": float(df.coverage.mean())}


def churn(prev: np.ndarray | None, cur: np.ndarray, visited: list[set[int]]) -> float:
    """Policy churn (spec §5 A5): mean over agents of the share of validation-visited observations whose greedy
    (unmasked, lowest-index tie) action changed since the previous checkpoint. NaN at the first checkpoint."""
    if prev is None:
        return float("nan")
    vals = []
    for i, vis in enumerate(visited):
        if vis:
            idx = np.fromiter(vis, dtype=np.int64)
            vals.append(float(np.mean(prev[i, idx] != cur[i, idx])))
    return float(np.mean(vals)) if vals else float("nan")


def stability(ck: pd.DataFrame) -> dict[str, Any]:
    """Preregistration §6: churn < 5% between the last two checkpoints AND validation RF range < 0.02 over the last three."""
    last_churn = float(ck.churn.iloc[-1])
    rf_range = float(ck.rf.iloc[-3:].max() - ck.rf.iloc[-3:].min())
    return {"last_churn": last_churn, "last3_rf_range": rf_range,
            "stable": bool(last_churn < 0.05 and rf_range < 0.02)}


def train_run(cfg: dict[str, Any], spec: RunSpec, train_pool: InstancePool, val_pool: InstancePool,
              out_dir: Path | None = None) -> dict[str, Any]:
    """Train one IQL team; evaluate on validation at checkpoints; optionally write logs and Q-tables to out_dir."""
    t0 = time.time()
    p = spec.params
    env = RescueEnv(cfg, horizon=spec.horizon, b_ref=spec.b_ref, budget_mode=spec.budget_mode, n_agents=spec.n_agents)
    team = IQLTeam(env.n, p, spec.seed, agent_ids=spec.agent_ids)
    order = EpisodeOrder(spec.seed, len(train_pool))
    budget = spec.max_env_steps
    eps_of = (lambda e: p.epsilon(e)) if budget is None else (lambda e: p.epsilon_by_steps(total_steps, budget))
    ep_rows, ck_rows = [], []
    prev_greedy = None
    best = (-1.0, -1, None)
    final_eval_rows: list[dict[str, Any]] = []
    total_steps = 0

    def checkpoint(episode: int) -> None:
        nonlocal prev_greedy, best, final_eval_rows
        rows, visited = evaluate_team(env, team, val_pool, spec.b0, {"run": spec.name, "checkpoint": episode})
        s = summarize_eval(rows)
        g = team.greedy_actions()
        recent = ep_rows[-spec.checkpoint_every:]
        ck_rows.append({"episode": episode, "env_steps": total_steps, "epsilon": eps_of(episode),
                        "churn": churn(prev_greedy, g, visited),
                        "train_mean_abs_td": float(np.mean([r["mean_abs_td"] for r in recent])) if recent else np.nan,
                        "train_rf": float(np.mean([r["rescued"] / r["V"] for r in recent])) if recent else np.nan,
                        **s})
        prev_greedy = g
        if s["rf"] >= best[0]:          # ties -> later checkpoint
            best = (s["rf"], episode, team.Q.copy())
        final_eval_rows = rows

    checkpoint(0)
    e = 0
    while (e < p.episodes) if budget is None else (total_steps < budget):
        inst, st = train_pool[int(order[e])]
        eps = eps_of(e)
        r = train_episode(env, team, inst, st, spec.b0, eps)
        total_steps += r["steps"]
        ep_rows.append({"episode": e + 1, "instance_seed": inst.seed, "epsilon": eps, **r})
        e += 1
        last = (e == p.episodes) if budget is None else (total_steps >= budget)
        if e % spec.checkpoint_every == 0 or last:
            checkpoint(e)
    ck = pd.DataFrame(ck_rows)
    stab = stability(ck)
    summary = {"spec": {**asdict(spec), "params": asdict(p)}, "seconds": round(time.time() - t0, 1),
               "total_env_steps": total_steps, "final": ck.iloc[-1].to_dict(), "best_val_episode": best[1],
               "best_val_rf": best[0], **stab}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(ep_rows).to_csv(out_dir / "train_log.csv", index=False)
        ck.to_csv(out_dir / "checkpoints.csv", index=False)
        pd.DataFrame(final_eval_rows).to_csv(out_dir / "val_final_episodes.csv", index=False)
        np.savez_compressed(out_dir / "q_final.npz", Q=team.Q)
        np.savez_compressed(out_dir / "q_bestval.npz", Q=best[2], episode=best[1])
        (out_dir / "run.json").write_text(json.dumps(summary, indent=1, default=float))
    summary["team"] = team
    return summary
