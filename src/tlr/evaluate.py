"""Episode runner shared by baselines, the oracle and (later) learned policies.

Implements the evaluation loop of spec §2 / preregistration §3. Phase 2 provides `run_episode`; condition-level
evaluation over instance sets is added in later phases.

Information discipline: decentralized policies receive only a `StaticContext` (a-priori knowledge) and, each step,
the agents' views and masks. Only a policy that declares `full_information = True` (the oracle reference) is given the
environment itself, and it is labelled as such everywhere it is reported.
"""

from __future__ import annotations

from .baselines import StaticContext, TeamPolicy
from .env import EpisodeLog, RescueEnv
from .mapgen import Instance, MapStatics


def run_episode(env: RescueEnv, inst: Instance, b0: int, policy: TeamPolicy, statics: MapStatics | None = None,
                seed: int = 0, record: bool = True) -> EpisodeLog | None:
    """Play one episode to termination and return its log (None if record=False)."""
    env.reset(inst, b0, statics=statics, record=record)
    if getattr(policy, "full_information", False):
        policy.plan(env)  # type: ignore[attr-defined]  # oracle only
    else:
        policy.begin_episode(StaticContext.from_env(env), seed)
    masks = env.masks.copy()
    while not env.done:
        views = [env.view(i) for i in range(env.n)]
        actions = policy.act(views, masks)
        _, masks, _, _, _ = env.step(actions)
    return env.log
