"""Replay evidence from the frozen TEST episodes of the main block (final Q-tables), chosen by fixed rules, and
re-simulated deterministically. Each replay must reproduce its row in results/eval/learned exactly (checked; exit 1 if not).

Selection rules (written before looking at any replay):
  per level   : the seed whose test RF is the median-closest (ties -> lower seed); within it, the first test instance
                (frozen order) whose episode RF is closest to that seed's mean RF.
  heavy assist: main Abundant, seed with the highest test RF; first test instance containing a completed heavy rescue.
  redundant   : main Abundant; the episode (any seed) with the most redundant-other searches (ties -> lower seed, earlier
                instance).
  abandonment : main Abundant; the episode with the most E1 abandonment events (same tie rule).
  E3 conflict : main Abundant; the first flagged episode (best agent above the median individual return, team below the
                median collective return) in seed order.
Output: results/replays/phase6_*.txt and results/replays/phase6_index.csv
Usage: python scripts/make_replays.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.env import RescueEnv  # noqa: E402
from tlr.experiments import BLOCKS, LEVELS, SEEDS, load_q, seeds_for, setting, world_cfg  # noqa: E402
from tlr.iql import eval_rngs, masked_argmax  # noqa: E402
from tlr.mapgen import compute_statics, generate_instance  # noqa: E402
from tlr.metrics import e3_conflict_flags, episode_record  # noqa: E402
from tlr.replay import render_episode, write_replay  # noqa: E402

OUT = ROOT / "results" / "replays"
EVENTS = ["rescue", "failed_rescue", "failed_assist", "duplicate_rescue", "first_sighting", "stale_correction",
          "dormant"]


def replay(level: str, seed: int, inst_seed: int, title: str, fname: str, expect: pd.Series) -> dict:
    cfg = world_cfg("main")
    H, B_ref, b0 = setting(BLOCKS["main"], level)
    inst = generate_instance(cfg, int(inst_seed))
    st = compute_statics(inst, __import__("tlr.costs", fromlist=["CostModel"]).CostModel.from_config(cfg), [1, 2])
    env = RescueEnv(cfg, horizon=H, b_ref=B_ref)
    Qs = load_q("main", level, seed)
    obs, masks = env.reset(inst, b0, statics=st, record=True)
    rngs = eval_rngs(inst.seed, 3)
    while not env.done:
        obs, masks, _, _, _ = env.step([masked_argmax(Qs[i][obs[i]], masks[i], rngs[i]) for i in range(3)])
    rec = episode_record(inst, st, env.log, env.costs, env.r_v)
    ok = all(np.isclose(rec[k], expect[k]) for k in ("rescued", "steps", "collective_return", "spent"))
    text = render_episode(inst, env.log, f"{title} | main, {level} (b0 = {b0}), training seed {seed}, test instance "
                                         f"seed {inst_seed}, greedy final Q-tables", EVENTS)
    write_replay(OUT / fname, text)
    return {"file": fname, "level": level, "seed": seed, "instance_seed": int(inst_seed), "rescued": rec["rescued"],
            "steps": rec["steps"], "termination": rec["termination"], "matches_eval_csv": bool(ok)}


def main() -> None:
    idx = []
    sl = pd.read_csv(ROOT / "results" / "stats" / "seed_level_learned.csv")
    sl = sl[(sl.block == "main") & (sl.checkpoint == "final")]
    for level in LEVELS:
        E = pd.read_csv(ROOT / "results" / "eval" / "learned" / f"main__{level}.csv")
        E = E[E.checkpoint == "final"]
        d = sl[sl.level == level].sort_values("seed")
        med = d.rf.median()
        seed = int(d.iloc[int(np.argmin(np.abs(d.rf.values - med)))].seed)
        es = E[E.seed == seed].reset_index(drop=True)
        k = int(np.argmin(np.abs(es.rf.values - es.rf.mean())))
        idx.append(replay(level, seed, es.instance_seed[k], f"Representative episode ({level})",
                          f"phase6_representative_{level}.txt", es.iloc[k]))
    E = pd.read_csv(ROOT / "results" / "eval" / "learned" / "main__Abundant.csv")
    E = E[E.checkpoint == "final"].reset_index(drop=True)
    best = int(sl[sl.level == "Abundant"].sort_values(["rf", "seed"], ascending=[False, True]).iloc[0].seed)
    h = E[(E.seed == best) & (E.rescued_heavy > 0)].iloc[0]
    idx.append(replay("Abundant", best, h.instance_seed, "Successful heavy rescue (simultaneous RESCUE + ASSIST)",
                      "phase6_heavy_assist.txt", h))
    for col, title, fname in (("rsr_other_num", "Most redundant searching (SEARCH over others' area)",
                               "phase6_redundant_search.txt"),
                              ("e1_abandonment", "Most abandonment events (E1: partner action wasted)",
                               "phase6_abandonment.txt")):
        r = E.sort_values([col, "seed"], ascending=[False, True], kind="stable").iloc[0]
        idx.append(replay("Abundant", int(r.seed), r.instance_seed, title, fname, r))
    flags = e3_conflict_flags(E.to_dict("records"), 3)
    r = E[np.array(flags) == 1].sort_values("seed", kind="stable").iloc[0]
    idx.append(replay("Abundant", int(r.seed), r.instance_seed,
                      "E3 conflict: best individual above median, team below median", "phase6_e3_conflict.txt", r))
    I = pd.DataFrame(idx)
    I.to_csv(OUT / "phase6_index.csv", index=False)
    print(I.to_string(index=False))
    if not I.matches_eval_csv.all():
        sys.exit(1)


if __name__ == "__main__":
    main()
