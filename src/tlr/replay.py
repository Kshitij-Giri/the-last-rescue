"""ASCII replays of recorded episodes (proof that the rules behave as specified; spec deliverable "replay evidence").

Legend (printed in every replay):
  #  wall        ~  hazard      .  free        B  base
  h/l  heavy/light victim not yet seen by any agent
  H/L  heavy/light victim seen by the team, still waiting
  x  rescued victim (evacuated)
  1..n  agent (1-based), *  two or more agents on one cell (overrides everything else)
Each frame shows the state BEFORE the joint action of that step, then the actions and events of the step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .costs import Action
from .env import EpisodeLog
from .mapgen import HAZARD, WALL, Instance

ACTION_NAMES = {int(a): a.name for a in Action}
LEGEND = ("Legend: # wall  ~ hazard  . free  B base  h/l unseen heavy/light  H/L seen waiting heavy/light  "
          "x rescued  1..n agents  * several agents on a cell")


def _frame(inst: Instance, log: EpisodeLog, k: int) -> list[str]:
    """Grid lines for the state before step k (k = log.steps gives the final state)."""
    L = inst.L
    seen_before: set[int] = set()
    rescued_before: set[int] = set()
    for ev in log.events:
        # initial sightings have t = 0 and happen before step 0; sightings logged at step t take effect after it.
        if ev["type"] == "initial_sighting" or (ev["type"] == "first_sighting" and ev["t"] < k):
            seen_before.add(ev["victim"])
        if ev["type"] == "rescue" and ev["t"] < k:
            rescued_before.add(ev["victim"])
    chars = []
    for cell in range(L * L):
        g = inst.grid[cell]
        chars.append("#" if g == WALL else "~" if g == HAZARD else ".")
    chars[inst.base] = "B"
    for vid, cell in enumerate(inst.victim_cells):
        if vid in rescued_before:
            chars[cell] = "x"
        else:
            ch = "h" if inst.victim_heavy[vid] else "l"
            chars[cell] = ch.upper() if vid in seen_before else ch
    pos = log.positions[k]
    for i, p in enumerate(pos):
        chars[p] = "*" if sum(1 for q in pos if q == p) > 1 else str(i + 1)
    return ["".join(chars[r * L:(r + 1) * L]) for r in range(L)]


def render_episode(inst: Instance, log: EpisodeLog, title: str = "", event_types: Iterable[str] | None = None) -> str:
    """Render a full episode as text."""
    keep = set(event_types) if event_types is not None else {
        "rescue", "failed_rescue", "failed_assist", "duplicate_rescue", "first_sighting", "stale_correction",
        "preempted", "dormant"}
    out = [f"=== {title} ===" if title else "=== episode ===",
           f"instance seed={inst.seed} L={inst.L} V={inst.n_victims} heavy={int(inst.victim_heavy.sum())} "
           f"n_agents={log.n_agents} mode={log.budget_mode} b0={log.b0} H={log.horizon}", LEGEND, ""]
    for k in range(log.steps + 1):
        budgets = log.budgets[k].tolist()
        out.append(f"--- t={k}  budgets={budgets}")
        out.extend(_frame(inst, log, k))
        if k < log.steps:
            acts = [ACTION_NAMES[int(a)] for a in log.actions[k]]
            eff = log.effective_actions[k]
            pre = [ACTION_NAMES[int(a)] for a in eff]
            line = "actions: " + "  ".join(f"A{i + 1}={a}" + (f"(->{pre[i]})" if pre[i] != a else "")
                                          for i, a in enumerate(acts))
            out.append(line)
            out.append("rewards: " + "  ".join(f"{x:+.3f}" for x in log.rewards[k]))
            for ev in log.events:
                if ev["t"] == k and ev["type"] in keep:
                    out.append("event: " + ", ".join(f"{key}={val}" for key, val in ev.items() if key != "footprint"))
        out.append("")
    term = log.termination if log.termination is not None else "none (episode still running when the script stopped)"
    out.append(f"END: termination={term} steps={log.steps} "
               f"rescued={sum(1 for e in log.events if e['type'] == 'rescue')}/{inst.n_victims}")
    return "\n".join(out) + "\n"


def write_replay(path: str | Path, text: str) -> None:
    """Write a replay to disk, creating directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
