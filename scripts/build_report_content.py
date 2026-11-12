"""Build the content of the final report (Phase 7) from the verified result files.

Outputs
  report/content.json        block list consumed by scripts/render_report.js (docx)
  report/report_source.md    the same content as Markdown (for reading and diffing)
  docs/report_numbers.yaml   every result number shown in the report with its source (checked by verify_results.py V7)

Inline markup inside text: **bold**, *italic*, `code`, _{subscript}, ^{superscript}.
Usage: python scripts/build_report_content.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_lib import Registry  # noqa: E402

R = Registry()
LV = ["Abundant", "Moderate", "Scarce", "Critical"]
CM = "results/stats/condition_means.csv"
OM = "results/stats/h1_h2_omnibus.csv"
PW = "results/stats/h1_h2_pairwise.csv"
H3 = "results/stats/h3_vs_baselines.csv"
H4 = "results/stats/h4_A1_mismatch.csv"
H6 = "results/stats/h6_A4_solo.csv"
A3 = "results/stats/a3_did_all.csv"
EX = "results/stats/exploratory_paired.csv"
A8 = "results/stats/a8_mediation.csv"
BT = "results/stats/baselines_test.csv"
E4 = "results/stats/exp4_individual_collective.csv"
TM = "results/stats/transfer_matrix.csv"
A2C = "results/stats/a2_cooperative_baseline.csv"
RJ = "results/stats/results.json"
TR = "results/phase5/training_runs.csv"
CAL = "config/calibrated.yaml"
DEF = "config/default.yaml"
CB = "results/calibration/table_bref.csv"
CS = "results/calibration/table_sweep_main.csv"
CSN = "results/calibration/table_sensitivity.csv"
CSUM = "results/calibration/calibration_summary.json"
PIL = "results/pilot/P0/analysis.json"
P2 = "results/phase2/metric_validation_summary.md"


# ---------- number shorthands ----------------------------------------------------------------------------------------
def m(level, metric, block="main", ck="final", nd=3, fmt="f"):
    return R.csv(CM, {"block": block, "checkpoint": ck, "level": level, "metric": metric}, "mean", nd, fmt)


def mci(level, metric, block="main", ck="final", nd=3):
    return R.ci(CM, {"block": block, "checkpoint": ck, "level": level, "metric": metric}, nd=nd)


def om(metric, col, fmt="p", nd=3):
    return R.csv(OM, {"metric": metric}, col, nd, fmt)


def bl(level, policy, col="rf", combo="main", nd=3):
    return R.csv(BT, {"combo": combo, "level": level, "policy": policy}, col, nd)


def h3(level, base, col, nd=3, fmt="f"):
    return R.csv(H3, {"level": level, "baseline": base}, col, nd, fmt)


def did(analysis, level, col="mean_did", nd=3, fmt="sf"):
    return R.csv(A3, {"analysis": analysis, "level_vs_abundant": level}, col, nd, fmt)


def didci(analysis, level, nd=3):
    w = {"analysis": analysis, "level_vs_abundant": level}
    return f"{R.csv(A3, w, 'mean_did', nd, 'sf')} [{R.csv(A3, w, 'ci_lo', nd)}, {R.csv(A3, w, 'ci_hi', nd)}]"


def ex(analysis, level, col="mean_diff", nd=3, fmt="f"):
    return R.csv(EX, {"analysis": analysis, "level": level}, col, nd, fmt)


def exci(analysis, level, nd=3):
    w = {"analysis": analysis, "level": level}
    return f"{R.csv(EX, w, 'mean_diff', nd, 'sf')} [{R.csv(EX, w, 'ci_lo', nd)}, {R.csv(EX, w, 'ci_hi', nd)}]"


def rj(path, nd=3, fmt="f"):
    return R.js(RJ, path, nd, fmt)


def p(x):  # p-value from a csv row helper
    return x


# ---------- block builders ------------------------------------------------------------------------------------------
DOC: list[dict] = []
FIGS: list[str] = []
TABS: list[str] = []


def H(level, text):
    DOC.append({"t": f"h{level}", "text": text})


def P(text, style=None):
    DOC.append({"t": "p", "text": text, **({"style": style} if style else {})})


def BUL(items, numbered=False):
    DOC.append({"t": "numbered" if numbered else "bullets", "items": items})


def EQ(text):
    DOC.append({"t": "eq", "text": text})


def CODE(lines, title=None):
    DOC.append({"t": "code", "lines": lines, "title": title})


def BOX(title, items, kind="understand"):
    DOC.append({"t": "box", "title": title, "items": items, "kind": kind})


def BREAK():
    DOC.append({"t": "pagebreak"})


def FIG(label, path, caption, width=6.3):
    assert (ROOT / path).exists(), path
    FIGS.append(label)
    DOC.append({"t": "figure", "label": label, "path": path, "caption": caption, "width": width})


def TAB(label, caption, header, rows, widths, note=None, font=9):
    TABS.append(label)
    assert all(len(r) == len(header) for r in rows), caption
    DOC.append({"t": "table", "label": label, "caption": caption, "header": header, "rows": rows, "widths": widths,
                "note": note, "font": font})


def tref(label):
    return f"Table {label}"


def fref(label):
    return f"Fig. {label}"


# =====================================================================================================================
# Title page and summary
# =====================================================================================================================
N_RUNS = R.files("results/runs/**/run.json")
N_TESTS = R.rx("results/logs/pytest.txt", r"(\d+) passed")
CPU_H = R.agg(TR, {}, "seconds", "sum", nd=2, fmt="f", scale=1 / 3600)

DOC.append({"t": "title", "title": "The Last Rescue",
            "subtitle": "Learning to Cooperate Under Resource Scarcity",
            "lines": ["Final project report, Fundamentals of AI, Group 14, IIT Gandhinagar",
                      "Kshitij Suresh Giri (23110177) · Panjari Maheshkumar Patel (23110236) · DV Snehal (23110083) · "
                      "Kshitish Madbhavi (24110175)",
                      "12 November 2026"],
            "note": ("Every result number in this report is inserted automatically from the result files of the "
                     "repository (scripts/build_report_content.py) and re-checked against those files by "
                     f"scripts/verify_results.py. Confirmatory analyses follow the preregistration frozen before any "
                     f"learning run (docs/preregistration.md, v1.0).")})

H(1, "Summary")
P("**Question.** How does resource scarcity affect the ability of independently learning agents to learn cooperative "
  "rescue strategies, and is any effect of scarcity on rescue performance attributable to cooperation?")
P("**What we built.** A grid-world search-and-rescue game for three agents with private, non-transferable resource "
  "budgets. Every action costs budget; half of the victims are *heavy* and can only be rescued when one agent plays "
  "RESCUE and a different agent plays ASSIST on the same cell in the same step. Budgets are set as a fraction ρ of a "
  "calibrated *just-enough* budget B_{ref}, so that the four scarcity levels (Abundant ρ = 1.0, Moderate 0.5, Scarce 0.3, "
  "Critical 0.2) mean comparable things on different maps (this holds for maps of 10 × 10 and larger, not for 8 × 8). Agents learn with independent tabular Q-learning (IQL). "
  "They are compared with a random, a greedy and a hand-designed cooperative baseline. A full-information planner is reported "
  "as an *oracle reference (full information, not a learner)*.")
P(f"**How we tested it.** All hypotheses, tests and analysis rules were preregistered and frozen before the first learning "
  f"run. {N_RUNS} training runs (10 training seeds per condition, 8,000 episodes each; {CPU_H} CPU-hours) were evaluated on "
  f"100 fixed test maps shared by all methods. The unit of analysis is the training seed, and all comparisons between "
  f"conditions are paired by seed.")
P("**Main findings** (performance is measured after 8,000 training episodes; the policies had not converged):")
BUL([
    f"Learning works. IQL beats the random baseline at Abundant in 10 of 10 seeds (rescue fraction RF "
    f"{mci('Abundant', 'rf')} vs {rj('H0.random_rf')}; exact one-sided p = {rj('H0.p', fmt='p')}).",
    f"Scarcity strongly reduces rescue performance (confirmatory H1). RF falls from {m('Abundant', 'rf')} to "
    f"{m('Moderate', 'rf')}, {m('Scarce', 'rf')} and {m('Critical', 'rf')} (Friedman χ²(3) = "
    f"{om('rf', 'friedman_chi2', 'f', 1)}, p = {om('rf', 'friedman_p')}, Kendall's W = {om('rf', 'kendall_w', 'f', 2)}). "
    f"The ordering is the same in every seed.",
    f"Cooperation collapses under scarcity (confirmatory H2). The cooperation rate CR falls from {m('Abundant', 'cr')} to "
    f"{m('Critical', 'cr')}, and the share of heavy victims rescued falls from {m('Abundant', 'rescued_heavy_share')} to "
    f"{m('Critical', 'rescued_heavy_share')}. Three of the seven cooperation metrics (effective assist rate, territory "
    f"division, load balance) do not change significantly.",
    "The learned teams contain co-adapted cooperation (confirmatory H4 and H6). Swapping in agents from other seeds lowers "
    "RF at three of four levels, and teams of agents trained alone perform far worse than jointly trained teams. The solo "
    "comparison is confounded by an observation distribution shift (Section 10.4).",
    f"The preregistered test of whether scarcity hurts *more* when cooperation is necessary (H5) gives a significant "
    f"result in the **opposite** direction on the absolute scale (difference-in-differences "
    f"{rj('H5.mean_did', fmt='sf')} [{rj('H5.ci_lo')}, {rj('H5.ci_hi')}], 0/10 seeds positive). The heavy-victim world "
    f"loses fewer points, but it starts much lower and is near the floor at Critical; it keeps a *smaller fraction* of its "
    f"Abundant performance "
    f"({did('raw_primary', 'Critical', 'retained_p05', 0, 'pct')} vs {did('raw_primary', 'Critical', 'retained_p0', 0, 'pct')}). The sign of this result depends on the scale and on the calibration. We therefore do not claim that "
    f"scarcity specifically destroys cooperation-dependent rescues (Section 10.5).",
    f"Seeds with more cooperation rescue more, even with the scarcity level held fixed (A8). This is an observational "
    f"association, not causal evidence. In the joint model only the productive-spend share keeps a confidence interval "
    f"that excludes zero, and that metric largely tracks reward.",
    f"IQL is clearly below the hand-designed cooperative baseline at every level and is not significantly better than "
    f"the greedy baseline at Critical (Holm p = {h3('Critical', 'greedy', 'p_holm12', fmt='p')}).",
])
P(f"**Main limitation.** The policies had not converged after 8,000 episodes. {rj('sensitivity.stable_runs_total', fmt='int')} "
  f"of {N_RUNS} runs meet the preregistered stability criterion, and none of the 40 main runs do. All results are "
  f"statements about policies after a fixed training budget, with 10 seeds per condition.")

DOC.append({"t": "toc"})
BREAK()

# =====================================================================================================================
# 1 Introduction
# =====================================================================================================================
H(1, "1. Introduction and research question")
H(2, "1.1 Motivation")
P("Teams of robots for search and rescue work under hard limits on battery, time and communication [2]. Two problems "
  "arise together. First, some tasks need more than one agent at the same time (lifting debris, carrying a casualty). "
  "Second, every action uses up a resource that cannot be refilled during the mission. Multi-agent reinforcement learning "
  "(MARL) is a natural tool for learning such team behaviour without hand-coding it [1, 3, 7]. Reinforcement learning has "
  "been used to coordinate disaster emergency response [5] and cooperative UAV search and rescue [6]. Earlier work on sequential "
  "social dilemmas showed that resource scarcity can change whether learned agents cooperate or compete [4]. Our "
  "project asks the corresponding question for a rescue task, where cooperation is sometimes physically required and "
  "resources are private.")
H(2, "1.2 Research question and hypotheses")
P("**Research question.** How does resource scarcity (ρ) affect the ability of independently learning agents to learn "
  "cooperative rescue strategies, and is any effect of ρ on rescue performance attributable to cooperation?")
P("The preregistration (frozen 12 November 2026, before any learning run) turns this into seven tests. The proposal "
  "assumed no direction, so all confirmatory tests except the learnability gate are two-sided.")
TAB("1", "Preregistered hypotheses. All tests are paired by training seed unless stated otherwise.",
    ["ID", "Statement", "Test (family correction)"],
    [["H0-gate", "At Abundant, IQL rescues more than random (learnability).", "one-sample Wilcoxon, one-sided; p < 0.05 and δ_{1} ≥ 0.33"],
     ["H1", "Rescue fraction differs across the four ρ levels.", "Friedman + Page's L; 6 pairwise Wilcoxon (Holm 6)"],
     ["H2", "Each of 7 cooperation metrics differs across ρ.", "Friedman per metric (Holm 7); pairwise (Holm 6)"],
     ["H3", "IQL differs from each baseline at each ρ.", "one-sample Wilcoxon (Holm 12)"],
     ["H4 (A1)", "Teams with mismatched teammates differ from original teams.", "Wilcoxon per ρ (Holm 4)"],
     ["H5 (A3)", "The scarcity effect differs between a world that needs cooperation and one that does not (DiD ≠ 0).", "Wilcoxon on per-seed DiD + bootstrap CI"],
     ["H6 (A4)", "Jointly trained teams differ from teams of solo-trained agents.", "Wilcoxon per ρ (Holm 4)"]],
    [1.0, 3.3, 2.2])
H(2, "1.3 What changed after the instructor's review")
P("The project-idea review raised three points. Each is handled by a dedicated part of the design (the full mapping is "
  "in Appendix E, the Review Response Matrix):")
BUL([
    "**R1, budgets, feasibility and operational cooperation metrics.** Budgets are per agent (main) with a pooled-budget "
    "ablation; the game is defined formally with exact feasibility and exhaustion rules (Section 3). Cooperation is "
    "measured by seven behavioural metrics computed from action logs, never from reward (Section 7).",
    "**R2, IQL non-stationarity and attribution.** Non-stationarity is measured directly (policy churn, TD error, stability "
    "criterion). Performance changes are attributed to cooperation only through interventions: teammate mismatch, agent "
    "ablation, a world where cooperation is unnecessary, and solo-trained agents (Section 10).",
    "**R3, calibration of B_{ref} and ρ.** The reference budget and horizon are calibrated from a cooperative baseline "
    "with pre-stated rules. The calibration is repeated on four other map configurations to check that ρ means the same "
    "thing across map sizes and densities (Section 5).",
])
H(2, "1.4 Contributions")
BUL([
    "A formally specified, tested resource-constrained Markov game with forced cooperation (heavy victims), per-agent "
    f"budgets and an action mask that uses only the agent's own information ({N_TESTS} automated tests).",
    "A calibration procedure that ties budgets to the map (H and B_{ref}), checked on five map configurations.",
    "A preregistered, paired experimental design with 10 seeds per condition and an intervention-based attribution "
    "analysis, all reported, including negative and inconclusive results.",
    f"A reproducibility package: frozen instance lists, hashes, a claims ledger, and a verifier that recomputes the "
    f"statistics and checks every reported number; all checks pass (results/logs/verify_results.txt).",
])

H(2, "1.5 How to read the evidence labels")
BOX("Evidence labels used throughout", [
    "**CONFIRMATORY**: hypotheses H0–H6, frozen before any learning run; Holm-corrected within their preregistered "
    "families; these carry the conclusions.",
    "**SECONDARY**: preregistered analyses reported as estimates or robustness checks (e.g. oracle-normalised A3, "
    "best-validation checkpoint, Kruskal–Wallis).",
    "**EXPLORATORY**: preregistered as exploratory (A2, A5, A6, A8, Exp4, Exp5, pooled budget, alternate map); "
    "unadjusted p-values, read as descriptive.",
    "**POST HOC**: added after seeing results (only the log-scale A3 analysis, deviations C4/C5); never used to "
    "replace a preregistered result.",
], kind="info")
# =====================================================================================================================
# 2 Background
# =====================================================================================================================
H(1, "2. Background and notation")
H(2, "2.1 Markov games with partial observation")
P("A Markov (stochastic) game generalises a Markov decision process to several agents that act at the same time [1, 3]. "
  "At each step every agent i chooses an action a_{t}^{i}; the joint action determines the next state and a reward for each "
  "agent. When agents see only part of the state, the game is *partially observable*, and each agent must act on its own "
  "observation o_{t}^{i}. Our game is finite-horizon (at most H steps) and fully cooperative in its team reward, but it also pays "
  "individual credit, so individual and collective interests can differ (Section 9.5).")
H(2, "2.2 Q-learning and independent Q-learning")
P("Q-learning learns an action-value table Q(o, a) from experience with the update [7]")
EQ("Q(o_{t}, a_{t}) ← Q(o_{t}, a_{t}) + α · [ r_{t} + γ · max_{a′ ∈ M(o_{t+1})} Q(o_{t+1}, a′) − Q(o_{t}, a_{t}) ]")
P("where α is the learning rate, γ the discount factor and M(o) the set of valid actions. For a single agent in a "
  "stationary environment, tabular Q-learning converges to the optimal values under standard conditions (Watkins and "
  "Dayan [8]). In *independent* Q-learning each agent keeps its own table and treats the other agents as "
  "part of the environment (Tan [9]). It is the simplest MARL method and the one named in the proposal.")
H(2, "2.3 Why IQL is non-stationary, and why that matters here")
P("From agent i's point of view, the environment includes its teammates' policies. These policies change while they learn, "
  "so the transition and reward probabilities that agent i experiences change too. The convergence guarantee above no "
  "longer holds, and an agent's values can chase a moving target [3, 9]. For this project the consequence is practical: "
  "a drop in performance under scarcity might come from less cooperation, from noisier learning, or from fewer "
  "training steps. We therefore (i) measure non-stationarity directly, (ii) hold the number of training episodes fixed "
  "and test the step-count confound separately, and (iii) attribute effects to cooperation only through interventions "
  "(Section 10).")
H(2, "2.4 Notation")
TAB("2", "Symbols used in this report (values are those of the main configuration).",
    ["Symbol", "Meaning", "Value"],
    [["L", "grid side length (grid is L × L)", R.ym(DEF, "env.grid_size")],
     ["n", "number of agents (common base cell b)", R.ym(DEF, "env.n_agents")],
     ["V", "number of victims; p_{heavy} = share of heavy victims", f"6; {R.ym(DEF, 'env.p_heavy', 1, 'f')}"],
     ["H", "horizon (maximum steps per episode), calibrated", R.ym(CAL, "configurations.main.H")],
     ["B_{ref}", "reference (just-enough) per-agent budget, calibrated", R.ym(CAL, "configurations.main.B_ref")],
     ["ρ", "scarcity level: fraction of B_{ref} given to each agent", "1.0 / 0.5 / 0.3 / 0.2"],
     ["B_{0}^{i}", "initial budget of agent i = round(ρ·B_{ref})",
      " / ".join(R.ym(CAL, f"configurations.main.b0_per_level.{l}") for l in LV)],
     ["B_{t}^{i}", "remaining budget of agent i at step t", "—"],
     ["c_{m}, c_{h}, c_{S}, c_{R}, c_{A}", "costs of move, hazard entry, SEARCH, RESCUE, ASSIST (WAIT costs 0)",
      " / ".join(R.ym(DEF, f"costs.{k}") for k in ["move", "move_hazard", "search", "rescue", "assist"])],
     ["r_{v}, r_{s}, r_{tm}", "radii of passive sensing, SEARCH and teammate visibility (Chebyshev)",
      " / ".join(R.ym(DEF, f"env.{k}") for k in ["radius_passive", "radius_search", "radius_teammate"])],
     ["o_{t}^{i}, M(o)", "observation of agent i; set of valid (unmasked) actions", "3,960 observations"],
     ["λ_{I}, λ_{T}, λ_{C}", "weights of individual reward, team reward and cost",
      " / ".join(R.ym(DEF, f"reward.lambda_{k}", 2, "f") for k in "ITC")],
     ["α, γ, ε", "learning rate, discount, exploration rate", "0.1, 0.98, 1.0 → 0.05"],
     ["RF", "rescue fraction = rescued / V (primary outcome)", "—"],
     ["s", "training seed (unit of analysis), s ∈ {0, …, 9}", "10 per condition"]],
    [1.3, 3.8, 1.4])

# =====================================================================================================================
# 3 Formal problem
# =====================================================================================================================
H(1, "3. Revised formal problem (review point R1)")
H(2, "3.1 The game")
P("The task is a finite-horizon, partially observed Markov game G = ⟨N, S, {A^{i}}, {O^{i}}, T, {R^{i}}, H, B_{0}⟩ with "
  "n = 3 agents. The state s_{t} contains the static map (walls, hazard cells, base), the victims (cell, type light or "
  "heavy, rescued or not), the agents' cells and their budgets B_{t}^{i}. The map is known to the agents in advance; "
  "victims and teammates are only partially observed. Transitions are deterministic given the joint action.")
H(2, "3.2 Per-agent and pooled budgets")
P("In the **main setting** each agent owns a private, non-transferable budget B_{t}^{i}, starting at B_{0}^{i} = round(ρ·B_{ref}). "
  "An action a is valid for agent i only if its cost c(a) ≤ B_{t}^{i}. This turns scarcity into a team allocation problem: "
  "an agent that spends its budget exploring may later be unable to provide the ASSIST that a teammate needs. "
  "In the **pooled ablation** the team shares one budget B_{team} = n·B_{0}; masks, payment and exhaustion use the pool, payment "
  "priority rotates with t so that no agent is favoured, and an action that can no longer be paid becomes WAIT. The "
  "budget *feature* that agents observe uses the per-capita share floor(B_{team}/n), so the observation space is the same "
  "in both settings (clarification P4).")
H(2, "3.3 Feasibility and exhaustion")
P("Three events end an episode, checked in this order after every step:")
BUL(["**all rescued**: every victim has been rescued;",
     "**exhausted**: max_{i} B_{t}^{i} < c_{R}, i.e. no agent can pay for a RESCUE any more, so no further rescue is possible "
     "(in the pooled setting: B_{team} < c_{R});",
     "**horizon**: t = H."], numbered=True)
P("An agent with B_{t}^{i} < 1 is *dormant*: only WAIT is valid, and its learner makes no update. An instance is *feasible* "
  "at a budget level if at least one victim can be rescued: an agent can reach a light victim and pay for the RESCUE, "
  "or two agents can reach a heavy victim and pay for RESCUE and ASSIST, within the horizon (an exact check on the known "
  "map). Test, validation and training instances that "
  "were infeasible at Critical were regenerated before freezing (rejection 1.0% on test). These definitions make the "
  "end of a mission exact: after exhaustion, no action can change the primary outcome.")
H(2, "3.4 Reward")
EQ("R_{t}^{i} = λ_{I} · r_{ind,t}^{i} + λ_{T} · r_{team,t} − λ_{C} · c(a_{t}^{i})")
P(f"The individual part r_{{ind}} pays {R.ym(DEF, 'reward.discovery', 1, 'f')} for discovering a victim, "
  f"{R.ym(DEF, 'reward.light_rescue', 1, 'f')} for a light rescue, and {R.ym(DEF, 'reward.heavy_rescuer', 1, 'f')} each to the "
  f"rescuer and the assister of a heavy victim. The team part r_{{team}} pays {R.ym(DEF, 'reward.team_per_rescue', 1, 'f')} to every "
  f"agent for each rescue by anyone. The cost term converts budget units into reward with "
  f"λ_{{C}} = {R.ym(DEF, 'reward.lambda_C', 2, 'f')}. The design gives a heavy rescue the same team value as a light one, but "
  "splits its individual credit, so a selfish agent prefers light victims.")
H(2, "3.5 Observation")
P("Each agent sees a compact discrete tuple o = (f1, …, f5), 3,960 values in total: f1 = the nearest victim the agent "
  "believes unrescued, from its own memory (none, here-light, here-heavy, or first step N/S/E/W of the cheapest path × "
  "near/far; 11 values); f2 = first step towards the nearest cell it has never observed (none or N/S/E/W; 5 values); "
  "f3 = the nearest teammate within r_{tm} (none, same cell, N/S/E/W; 6 values); f4 = own budget bucket (4 values); "
  "f5 = elapsed-time third (3 values). Directions are first moves on the cheapest path on the known map, so walls never "
  "trap an agent. Agents do not see teammates' budgets, memories or identities. The budget buckets are "
  "half-open intervals with integer thresholds τ_{1} = c_{R} = 3, τ_{2} = max(τ_{1}+1, ⌈0.25·B_{ref}⌉) and "
  "τ_{3} = max(τ_{2}+1, ⌈0.5·B_{ref}⌉). With B_{ref} = 64 these are 3, 16 and 32. Bucket 0 therefore means exactly "
  "*cannot pay for a RESCUE* in the per-agent setting (clarification P1). Thresholds are relative to B_{ref}, not to the "
  "agent's own starting budget, so the same bucket means the same absolute amount at every ρ.")

# =====================================================================================================================
# 4 Environment
# =====================================================================================================================
H(1, "4. Environment design")
H(2, "4.1 Maps and instances")
P("A map is a 10 × 10 grid with a common base cell. 15% of cells are walls and 10% of free cells are hazard cells; "
  "maps whose free cells are not all connected are rejected. Six victims are placed on free cells at Chebyshev distance at "
  "least 2 from the base (so none is visible at t = 0); exactly three are heavy. Each instance is generated from one "
  "integer seed. Disjoint seed ranges are used for the training pool (1,000 maps), validation (50), test (100), the "
  "shifted test (100, wall 0.25 and victim density 0.09) and calibration (200). The lists are frozen with SHA-256 hashes "
  "(results/calibration/instance_sets.json).")
FIG("0a", "results/figures/fig0a_environment.png",
    "An example instance (frozen test instance 0). The three agents start together at the base. They see victims "
    "within radius 1 at every step, within radius 2 when they spend 2 units on SEARCH, and teammates within radius 3. "
    "Heavy victims (squares) need two agents acting on the same step.", width=5.8)
H(2, "4.2 Actions and costs")
TAB("3", "Actions, costs (integer budget units) and validity conditions. Validity is checked on the agent's own "
         "observation and budget; invalid actions are masked for every policy (learners and baselines alike).",
    ["Action", "Cost", "Valid when (agent i, own information only)"],
    [["UP / DOWN / LEFT / RIGHT", f"{R.ym(DEF, 'costs.move')} ({R.ym(DEF, 'costs.move_hazard')} into hazard)",
      "target cell is inside the grid and not a wall; budget covers the cost"],
     ["SEARCH", R.ym(DEF, "costs.search"), "budget ≥ c_{S}; reveals all victims within r_{s} = 2"],
     ["RESCUE", R.ym(DEF, "costs.rescue"), "an unrescued victim is on the agent's own cell; budget ≥ c_{R}"],
     ["ASSIST", R.ym(DEF, "costs.assist"), "an unrescued heavy victim is on the own cell; budget ≥ c_{A}"],
     ["WAIT", R.ym(DEF, "costs.wait"), "always valid"]],
    [1.6, 1.2, 3.7])
H(2, "4.3 One step of the game")
P("All agents act at the same time. Fig. 0b shows the order of operations inside one step. A light victim is rescued "
  "by any RESCUE on its cell. A heavy victim is rescued only if, in the same step, one agent plays RESCUE and a different "
  "agent plays ASSIST on its cell. Extra simultaneous RESCUEs or ASSISTs on the same victim are paid for but wasted; "
  "two RESCUEs on the same light victim count as a duplicate rescue (event E2).")
FIG("0b", "results/figures/fig0b_step_pipeline.png",
    "Order of operations inside one simultaneous step (spec §1.3). Steps 1–3 use only the agent's own information; "
    "steps 4–9 are applied by the environment to the true state.")
H(2, "4.4 Information, masking and stale memory")
P("Each agent keeps a memory of the victims it has seen. The policy input and the action mask are computed only from "
  "this agent's own view, never from hidden state (clarification P3). The agent's own cell is observed at every step, "
  "so RESCUE is never offered on an already rescued victim. Memory about other cells can be stale (a teammate may "
  "have rescued a remembered victim); stale memory can mislead navigation only and is corrected as soon as the cell is "
  "observed. Every action is re-checked against the mask that was issued, and an invalid action raises an error. This "
  "makes masking identical for learners and baselines, and no policy can use information it should not have.")
H(2, "4.5 Testing")
P(f"The environment, metrics, baselines, oracle, learner and statistics are covered by {N_TESTS} automated tests "
  "(results/logs/pytest.txt). They include hand-written scripted episodes with known answers for every rule and metric, "
  "conservation of budget, determinism under a fixed seed, the masking guarantee, and mutation checks (deliberately "
  "breaking a rule and confirming that a test fails). Replays of example episodes are stored in results/replays/.")

# =====================================================================================================================
# 5 Calibration
# =====================================================================================================================
H(1, "5. Resource model and calibration (review point R3)")
H(2, "5.1 Why calibrate")
P("A budget of 30 units is generous on a small map and hopeless on a large one. If ρ is to mean *a fraction of what the "
  "task needs*, the reference budget must be measured on the task. The calibration rules were written and hashed "
  "before any calibration run (config/calibration.yaml). They use only 200 calibration instances, the cooperative "
  "baseline and the oracle, and never the learners or any validation or test instance.")
H(2, "5.2 Procedure")
BUL([
    "**Horizon.** With unlimited budget, run the cooperative baseline with a long cap. T_{90} = the 90th percentile over "
    "instances of the step at which 90% of victims are rescued; H = ⌈T_{90}/0.7⌉, so that time is not the binding "
    "constraint.",
    "**Reference budget.** With H fixed and unlimited budget, B_{ref} = the 90th percentile of per-agent consumption of the "
    "cooperative baseline: at ρ = 1 an agent has *just enough* in about 90% of cases.",
    "**Analytic cross-check.** A back-of-envelope formula (lawn-mower coverage + rescue costs + heavy-victim convergence) "
    "predicts consumption from L, density and costs.",
    "**Scarcity levels.** For ρ = 1.0, 0.9, …, 0.1, run the cooperative baseline and the oracle and choose the ρ whose "
    "cooperative RF is closest to the targets ≈ 1.0, 0.70, 0.40 and 0.10–0.15, subject to the oracle rescuing at least "
    "one victim in ≥ 95% of instances at Critical.",
    "**Sensitivity.** Repeat everything for L ∈ {8, 12} × victim density ∈ {0.04, 0.08}.",
], numbered=True)
H(2, "5.3 Results")
P(f"For the main configuration T_{{90}} = {R.csv(CB, {'configuration': 'main'}, 'T90', 0, 'int')}, so "
  f"H = {R.csv(CB, {'configuration': 'main'}, 'H', 0, 'int')}, and B_{{ref}} = {R.csv(CB, {'configuration': 'main'}, 'B_ref_empirical_q90', 0, 'int')} "
  f"(mean consumption {R.csv(CB, {'configuration': 'main'}, 'consumption_mean', 1)}). "
  f"Table 4 lists the calibrated values of all configurations. The analytic formula tracks the empirical consumption "
  f"almost perfectly across configurations (Pearson r = {R.rx('results/calibration/derived_numbers.txt', r'Pearson r = ([0-9.]+)', 3, 'f')}) "
  f"but predicts only about half of it (ratio to mean consumption "
  f"{R.csv(CB, {'configuration': 'main'}, 'analytic_over_mean', 2)} in the main configuration). The planner-free "
  "estimate misses detours, waiting for a partner and re-visits; this is a finding, and the empirical value is used.")
cb_rows = []
for c in ["main", "L8_d04", "L8_d08", "L12_d04", "L12_d08", "main_p0"]:
    w = {"configuration": c}
    cb_rows.append([c, R.csv(CB, w, "L", 0, "int"), R.csv(CB, w, "density", 2), R.csv(CB, w, "p_heavy", 1),
                    R.csv(CB, w, "T90", 0, "int"), R.csv(CB, w, "H", 0, "int"), R.csv(CB, w, "B_ref_empirical_q90", 0, "int"),
                    R.csv(CB, w, "B_ref_analytic", 1), R.csv(CB, w, "reach_90pct_within_H", 3)])
TAB("4", "Calibrated horizon and reference budget per configuration (200 calibration instances each). 'Reach 90%' = share of "
         "instances where the cooperative baseline rescues ≥ 90% of victims within H with unlimited budget.",
    ["Config.", "L", "Density", "p_{heavy}", "T_{90}", "H", "B_{ref}", "B_{ref} analytic", "Reach 90%"], cb_rows,
    [1.0, 0.4, 0.7, 0.7, 0.6, 0.5, 0.6, 1.0, 0.9])
sw_rows = []
for rho in ["1.0", "0.9", "0.8", "0.7", "0.6", "0.5", "0.4", "0.3", "0.2", "0.1"]:
    w = {"rho": rho}
    sel = {"1.0": "Abundant", "0.5": "Moderate", "0.3": "Scarce", "0.2": "Critical"}.get(rho, "")
    sw_rows.append([rho, R.csv(CS, w, "b0", 0, "int"), R.csv(CS, w, "rf_cooperative"), R.csv(CS, w, "rf_oracle"),
                    R.csv(CS, w, "rf_greedy"), R.csv(CS, w, "feasible_share", 2), sel])
TAB("5", "ρ sweep on the calibration instances (main configuration). The four selected levels are marked. Feasible = share "
         "of instances where at least one victim can be rescued (exact check).",
    ["ρ", "b_{0}", "RF cooperative", "RF oracle ref.", "RF greedy", "Feasible", "Selected as"], sw_rows,
    [0.5, 0.5, 1.1, 1.1, 0.9, 0.8, 1.1])
P(f"The selected levels are ρ = 1.0, 0.5, 0.3 and 0.2, i.e. budgets b_{{0}} = 64, 32, 19 and 13 per agent. The Critical "
  f"level misses its target band: its cooperative RF is {R.csv(CS, {'rho': '0.2'}, 'rf_cooperative')} rather than 0.10–0.15. "
  f"The band-matching value ρ = 0.1 leaves the oracle unable to rescue anyone in most instances (feasible share "
  f"{R.csv(CS, {'rho': '0.1'}, 'feasible_share', 2)}), so the pre-stated feasibility rule moved Critical up to ρ = 0.2 "
  f"(feasible share {R.csv(CS, {'rho': '0.2'}, 'feasible_share', 2)}). The grid was not refined after seeing this "
  "(note N1). Critical is therefore *severe but solvable*, and less extreme than originally intended.")
FIG("C1", "results/calibration/figures/fig_cal_main.png",
    "Calibration of the main configuration: rescue fraction of the cooperative baseline, the oracle reference, greedy "
    "and random as ρ falls, with the four selected levels. Performance degrades smoothly, and the oracle reference stays "
    "well above the cooperative baseline at Scarce and Critical, so these levels leave room for better coordination.", width=5.6)
H(2, "5.4 Does ρ mean the same thing on other maps?")
P(f"If ρ measures *a fraction of a just-enough budget*, the cooperative baseline's RF(ρ) curves should overlap across "
  f"configurations. For maps with L ≥ 10 they nearly do: the spread is at most "
  f"{R.rx('results/calibration/derived_numbers.txt', r'Scarce   rho=0.3: coop RF main [0-9.]+; L>=10 spread ([0-9.]+)', 3, 'f')} "
  "at the selected levels. On 8 × 8 maps the curves fall faster, because fixed costs (walking out from the base, the "
  "RESCUE and ASSIST themselves) are a larger part of a smaller budget (Fig. C2). The calibration therefore normalises "
  "scale well for medium and large maps but not for small ones. We state this limit rather than claim full scale "
  "invariance.")
FIG("C2", "results/calibration/figures/fig_cal_sensitivity.png",
    "Sensitivity of the calibration: cooperative-baseline RF against ρ for five map configurations and the all-light "
    "world. Curves for L ≥ 10 nearly coincide; 8 × 8 maps and the all-light world fall faster.", width=5.6)
P(f"The calibration also shows how much cooperation costs. In the all-light world (same maps, every victim light) "
  f"B_{{ref}} is {R.ym(CAL, 'configurations.main_p0.B_ref')} instead of {R.ym(CAL, 'configurations.main.B_ref')} and "
  f"H is {R.ym(CAL, 'configurations.main_p0.H')} instead of {R.ym(CAL, 'configurations.main.H')}. Requiring two agents for half "
  f"of the victims raises the just-enough budget by about 56%. Fig. C3 shows the distribution of per-agent consumption.")
FIG("C3", "results/calibration/figures/fig_cal_consumption.png",
    "Per-agent budget consumption of the cooperative baseline with unlimited budget (main configuration). B_{ref} is its "
    "90th percentile; the analytic estimate lies far below the empirical distribution.", width=5.6)

# =====================================================================================================================
# 6 Algorithms
# =====================================================================================================================
H(1, "6. Algorithms")
H(2, "6.1 Independent Q-learning")
P("Each agent has its own Q-table over the 3,960 observations and 8 actions, initialised to zero. Exploration is "
  "ε-greedy restricted to valid actions, with random tie-breaking. ε decreases linearly from 1.0 to 0.05 over the first "
  "70% of the 8,000 training episodes and then stays at 0.05. Each episode is played on a map drawn from the training pool "
  "in an order fixed by the seed. Evaluation is greedy (ε = 0) on the 100 test maps, with ties broken by a random "
  "generator seeded by (instance, agent), so every method sees the same tie-breaking stream (common random numbers).")
CODE([
    "for episode e = 1 … E (E = 8,000):",
    "    map ← training_pool[order_s[e]];  ε ← schedule(e)",
    "    reset: every agent at the base, budget B0 = round(ρ·B_ref)",
    "    while episode not over:",
    "        for each agent i (independently):",
    "            o_i ← observe_i(state);  M_i ← valid_actions(view_i)",
    "            with prob. ε:  a_i ← uniform random action in M_i",
    "            otherwise:     a_i ← argmax_{a∈M_i} Q_i(o_i, a)   (random tie-break)",
    "        state, rewards, done ← env.step(a_1, …, a_n)",
    "        for each agent i that was not dormant:",
    "            target ← r_i                                if done",
    "                     r_i + γ · max_{a∈M_i'} Q_i(o_i', a)  otherwise",
    "            Q_i(o_i, a_i) ← Q_i(o_i, a_i) + α · (target − Q_i(o_i, a_i))",
    "    every 500 episodes: save Q_i; greedy validation on 50 maps;",
    "                        record policy churn and mean |TD error|",
], title="Algorithm 1. Independent Q-learning (per training run; α = 0.1, γ = 0.98)")
P("Termination of any kind (all rescued, exhausted, horizon) is treated as terminal (done = 1). Including the horizon "
  "keeps the targets consistent with the time bucket f5, at the cost of ignoring the true future beyond H.")
H(2, "6.2 Baselines")
P("All baselines are decentralised, use the same observations and masks as the learners, and are evaluated on the "
  "same test maps.")
BUL([
    "**Random**: a uniformly random valid action (10 evaluation seeds, 1,000 episodes per level).",
    "**Greedy (uncoordinated identical agents)**: each agent walks to the nearest affordable victim it believes "
    "unrescued, rescues lights, attempts each heavy victim at most once, never ASSISTs, and explores otherwise. All three "
    "agents run the same deterministic rule from the same base, so they tend to move in lockstep. It is therefore *not* the "
    "best selfish policy, and comparisons with it are read as 'IQL vs uncoordinated identical agents' (group decision D22).",
    "**Cooperative (hand-designed)**: agents split the map into sectors, call for help on finding a heavy victim, use a "
    "fixed role convention (the lowest-index agent RESCUEs, the other ASSISTs), wait at most 2L steps for a partner, and do "
    "not SEARCH while a lower-index teammate stands on their cell (P7). It is a strong, interpretable reference for what "
    "coordinated behaviour can achieve with the same information.",
])
H(2, "6.3 Oracle reference (full information, not a learner)")
P(f"The oracle sees the whole state and plans centrally with greedy insertion: it repeatedly adds the victim whose "
  f"insertion into some agent's route gives the most rescues per unit of budget, pairing two agents for heavy victims, and "
  f"then executes the plan. On small instances it equals the exhaustive macro-plan optimum in "
  f"{R.rx(P2, r'oracle equals the optimum in (\d+)')} of "
  f"{R.rx(P2, r'(\d+) cases; oracle equals')} cases "
  f"({R.rx(P2, r'total rescues oracle \d+ vs optimum \d+ \(([0-9.]+)%\)', 1, 'f')}% of total optimal rescues). It is not a "
  "true optimum on the test maps and never takes part in a hypothesis test. It shows how much of a level's difficulty "
  "comes from the budget itself and how much from imperfect information and coordination. A separate provable upper "
  "bound (ignoring travel) equals V at all four levels, so it is uninformative here and is not used further.")

# =====================================================================================================================
# 7 Metrics
# =====================================================================================================================
H(1, "7. Cooperation metrics (review point R1)")
P("Reward cannot measure cooperation: a team of selfish agents that each rescue lights earns positive team reward. We "
  "therefore measure cooperation from behaviour in the per-step action logs. Each metric has a fixed formula, a "
  "direction, and scripted test episodes with known answers. Ratio metrics are pooled per seed over the 100 test "
  "episodes (sum of numerators ÷ sum of denominators).")
TAB("6", "Cooperation metrics (formal definitions in docs/phase0_design_spec.md §3).",
    ["ID", "Name", "Definition", "Cooperative direction"],
    [["C1", "Effective assist rate EAR", "heavy rescues / ASSIST actions (each heavy rescue uses exactly one effective ASSIST)", "higher"],
     ["C2", "Redundant search ratio RSR, RSR_other", "share of SEARCHes whose footprint is ≥ 50% already covered (by others, incl. same-step lower-index searches, for RSR_other)", "lower"],
     ["C3", "Territory division TDI", "1 − mean pairwise Jaccard overlap of the cells visited by the agents", "higher"],
     ["C4a", "Productive spend share PSS", "minimal required rescue cost of all rescues / total budget spent", "higher (tracks reward)"],
     ["C4b", "Consumption Gini", "Gini coefficient of the budget each agent spent", "lower = balanced load"],
     ["C5", "Cooperation rate CR", "cooperative non-WAIT actions / non-WAIT actions; cooperative = effective RESCUE or ASSIST of a heavy rescue, or a move of its participants that converges on the victim in the 2L steps before", "higher"]],
    [0.5, 1.5, 3.4, 1.1], font=8.5)
P("Three event counts describe individual versus collective interest (Exp4): **E1 abandonment** (two agents on a heavy "
  "victim's cell, one plays RESCUE or ASSIST, the other does not complete it), **E2 duplicate light rescue**, and **E3 "
  "conflict episodes** (the episode's best agent is above the median individual return while the team is below the median "
  "collective return; redefined before freezing because the original wording flagged half of all episodes by construction, P6).")
P(f"**Construct validity.** Before any learning run, each metric was checked on scripted episodes and on the baselines: "
  f"{R.rx(P2, r'\*\*(\d+)/\d+ checks passed')} of {R.rx(P2, r'\*\*\d+/(\d+) checks passed')} checks passed. The three "
  "failures concern PSS. PSS is almost a monotone function of collective return (Spearman 0.95–1.00 across "
  "episodes). We kept it in the preregistered H2 family, as decided by the group (D22), but it is never presented as "
  "independent evidence of cooperation. CR, the headline cooperation metric, is zero by construction in the all-light "
  "world, because no rescue there requires a partner.")

# =====================================================================================================================
# 8 Protocol
# =====================================================================================================================
H(1, "8. Experimental protocol")
H(2, "8.1 Preregistration and phases")
P("The design was written first (Phase 0) and revised only before the freeze (changes P1–P8, all logged). The "
  "preregistration was frozen at the end of calibration, before any learning run, and its SHA-256 hash was recorded. "
  "A learnability pilot on validation maps only (Phase 4) was allowed to change four named settings; it passed its gate, "
  f"and **no setting was changed** (validation RF {R.js(PIL, 'iql_val_rf_mean')} vs random {R.js(PIL, 'random_val_rf')}, "
  f"{R.js(PIL, 'seeds_above_random', 0, 'int')}/5 seeds above, p = {R.js(PIL, 'wilcoxon_one_sided_p', fmt='p')}). Every "
  "later change is listed in Appendix C (C1–C6, N2–N5); none changed a frozen design choice, parameter or hypothesis.")
H(2, "8.2 Conditions and runs")
blocks = [("main", "Main sweep (Exp1, Exp2, H1–H4, H6)", "per-agent budgets, p_heavy = 0.5, main H and B_ref"),
          ("p0", "A3 all-light world, primary (H5)", "p_heavy = 0, same maps and main H, B_ref"),
          ("p0sec", "A3 all-light world, own calibration", "p_heavy = 0, H = 48, B_ref = 41 (secondary)"),
          ("solo", "A4 solo-trained agents (H6)", "each agent trained alone (n = 1), deployed as a team"),
          ("eqsteps", "A6 equal environment steps", "train until the Abundant run's step count (Moderate–Critical)"),
          ("pooled", "Pooled-budget ablation", "B_team = 3·b0 shared"),
          ("alt", "Alternate configuration", "L = 12, density 0.04, H = 150, B_ref = 87")]
rows = []
for b, name, desc in blocks:
    w = {"block": b}
    rows.append([name, desc, R.agg(TR, w, "seed", "count", 0, "int")])
TAB("7", "Training blocks. Every block uses training seeds 0–9 at each of its levels; seed s has the same training-map "
         "order and exploration stream in every block, so conditions are paired by seed. Solo runs count one run per "
         "agent slot.",
    ["Block", "What changes", "Runs"], rows, [2.4, 3.3, 0.8])
P(f"In total {N_RUNS} training runs were made ({CPU_H} CPU-hours). The test-time interventions A1 (teammate mismatch) "
  "and A2 (agent ablation) and the transfer matrix (Exp5) reuse the trained main-block agents. Every run was checked "
  "for completeness and every raw evaluation file is hashed (results/phase5/phase5_manifest.json).")
H(2, "8.3 Statistical analysis")
BUL([
    "**Unit of analysis**: the training seed. Each seed contributes one number per condition: its mean over the 100 test "
    "maps. Test episodes are repeated measurements of one trained team and are never counted as n.",
    "**Paired designs**: conditions are compared within seed. Across the four levels we use the Friedman test [11] with "
    "Kendall's W and Page's L trend test [12] (two-sided). Two conditions are compared with the Wilcoxon signed-rank test [13], "
    "with the matched-pairs rank-biserial correlation r_{rb} as effect size.",
    "**One-sample designs**: greedy, cooperative and oracle are deterministic, so IQL's 10 seed values are tested against "
    "the baseline's single value (one-sample Wilcoxon; effect size δ_{1} = (seeds above − seeds below)/10).",
    "**Multiple comparisons**: Holm correction [10] within each preregistered family (Table 1); α = 0.05.",
    "**Uncertainty**: mean and 95% percentile bootstrap CI [14] over seeds (10,000 resamples; for paired contrasts, the seed's "
    "conditions are resampled together). With n = 10 the smallest attainable two-sided Wilcoxon p is 2/1024 ≈ 0.002.",
    "**Ties**: zero differences are dropped before the Wilcoxon test (preregistered); differences below 10^{−9} are "
    "treated as exact zeros (C6).",
    "**Secondary**: Kruskal–Wallis and Cliff's δ (unpaired) are reported for comparability only.",
])
P(f"All statistics are produced by one script (scripts/run_stats.py). The verifier recomputes the confirmatory tests "
  f"independently from the seed-level files, re-runs the statistics script and checks that every output is byte-identical, "
  f"and checks every number in this report against its source file (Section 13).")
BREAK()

# =====================================================================================================================
# 9 Results
# =====================================================================================================================
H(1, "9. Results")
P("All values are for the final checkpoint after 8,000 training episodes, on the 100 test maps, as mean [95% bootstrap "
  "CI] over 10 training seeds, unless stated otherwise. All seeds are included, whether or not a run met the stability "
  "criterion.")
H(2, "9.1 Learnability and learning dynamics (H0-gate, A5)")
P(f"**H0-gate passed (CONFIRMATORY).** At Abundant, all 10 seeds exceed the random baseline (RF {m('Abundant', 'rf')} vs "
  f"{rj('H0.random_rf')}; one-sided exact Wilcoxon W^{{+}} = {rj('H0.W_plus', 0, 'int')}, p = {rj('H0.p', fmt='p')}, "
  f"δ_{{1}} = {rj('H0.delta_1', 2)}). The main sweep could therefore proceed as preregistered.")
P(f"Fig. 1 shows the learning curves. Validation RF rises steeply while ε falls and then flattens, but it does not "
  f"settle. Policy churn at the last checkpoint (the share of visited observations whose greedy action changed in the last "
  f"500 episodes) averages {R.agg(TR, {'block': 'main', 'level': 'Abundant'}, 'last_churn', 'mean', 1, 'pct')} at "
  f"Abundant and {R.agg(TR, {'block': 'main', 'level': 'Critical'}, 'last_churn', 'mean', 1, 'pct')} at Critical. "
  f"None of the 40 main runs meets the preregistered stability criterion. **Every result below describes policies after "
  f"a fixed budget of 8,000 episodes, not converged policies.**")
FIG("1", "results/figures/fig1_learning_curves.png",
    "Learning curves of the main sweep (validation RF, mean of 10 seeds with 95% CI band). Performance rises while "
    "exploration decays and then plateaus with continuing fluctuation; the curves are ordered by scarcity throughout "
    "training.")
H(2, "9.2 Exp1: scarcity reduces rescue performance (H1)")
P(f"**H1 confirmed (CONFIRMATORY).** RF falls monotonically with scarcity (Table 8, Fig. 2): Friedman "
  f"χ²(3) = {om('rf', 'friedman_chi2', 'f', 1)}, p = {om('rf', 'friedman_p')}, Kendall's W = {om('rf', 'kendall_w', 'f', 2)}; "
  f"Page's trend test two-sided p = {om('rf', 'page_p_two_sided')}. All six pairwise differences are significant "
  f"(each Holm p = {R.csv(PW, {'metric': 'rf', 'pair': 'Scarce - Critical'}, 'p_holm6', fmt='p')}, every seed in the same "
  f"direction). W = 1 means every seed ranks the four levels in the same order. Even the smallest step, Scarce to "
  f"Critical, costs {R.csv(PW, {'metric': 'rf', 'pair': 'Scarce - Critical'}, 'mean_diff')} "
  f"[{R.csv(PW, {'metric': 'rf', 'pair': 'Scarce - Critical'}, 'ci_lo')}, "
  f"{R.csv(PW, {'metric': 'rf', 'pair': 'Scarce - Critical'}, 'ci_hi')}] of RF.")
P(f"Scarcity removes heavy rescues first. At Abundant the teams rescue {m('Abundant', 'rescued_heavy_share')} of heavy "
  f"and {m('Abundant', 'rescued_light_share')} of light victims; at Critical {m('Critical', 'rescued_heavy_share')} of "
  f"heavy and {m('Critical', 'rescued_light_share')} of light victims. Heavy rescues need two agents with enough budget "
  "in the same place at the same time, so they are the first casualties of scarcity.")
rows = []
for l in LV:
    rows.append([l, mci(l, "rf"), mci(l, "rescued_heavy_share"), mci(l, "rescued_light_share"),
                 m(l, "exhausted", fmt="f", nd=2), m(l, "horizon", fmt="f", nd=2), m(l, "steps", nd=1)])
TAB("8", "Exp1, main sweep: learned performance by scarcity level (n = 10 seeds; test set; final checkpoint). "
         "Exhausted / horizon = share of episodes ending for that reason; steps = mean episode length.",
    ["Level", "RF", "Heavy share", "Light share", "Exhausted", "Horizon", "Steps"], rows,
    [0.9, 1.35, 1.35, 1.35, 0.75, 0.7, 0.6], font=8.5)
P(f"The termination shares show two different regimes. At Abundant most episodes end at the horizon (share "
  f"{m('Abundant', 'horizon', nd=2)}): the learned teams are slow, not poor. At Scarce and Critical almost every episode ends "
  "with budget exhaustion. The learners therefore face a time limit at Abundant and a budget limit under scarcity.")
FIG("2", "results/figures/fig2_exp1_rescue.png",
    "Exp1: rescue fraction by scarcity level, with per-seed lines connecting the same seed across levels (the pairing "
    "used by the tests), and the split into heavy and light victims. Every seed declines monotonically; heavy rescues "
    "vanish first.")
H(2, "9.3 Comparison with baselines (H3)")
rows = []
for l in LV:
    rows.append([l, mci(l, "rf"), bl(l, "random"), bl(l, "greedy"), bl(l, "cooperative"), bl(l, "oracle")])
TAB("9", "Rescue fraction of IQL (mean [95% CI], n = 10 seeds) and of the baselines on the same 100 test maps. The oracle "
         "reference has full information and is not a learner; it is shown for scale and never tested.",
    ["Level", "IQL", "Random", "Greedy", "Cooperative", "Oracle reference"], rows, [0.9, 1.4, 0.8, 0.8, 1.0, 1.2])
P(f"**H3 (CONFIRMATORY, Holm across 12 tests).** IQL is above random at every level (10/10 seeds each; Holm p = "
  f"{h3('Abundant', 'random', 'p_holm12', fmt='p')}). It is above the greedy baseline at Abundant (Holm p = "
  f"{h3('Abundant', 'greedy', 'p_holm12', fmt='p')}; {h3('Abundant', 'greedy', 'n_above', 0, 'int')}/10 seeds above), "
  f"Moderate and Scarce (Holm p = {h3('Moderate', 'greedy', 'p_holm12', fmt='p')} each; 10/10). **At Critical the "
  f"difference from greedy is not significant**: {h3('Critical', 'greedy', 'mean_diff')} "
  f"[{h3('Critical', 'greedy', 'ci_lo')}, {h3('Critical', 'greedy', 'ci_hi')}], "
  f"{h3('Critical', 'greedy', 'n_above', 0, 'int')} seeds above, {h3('Critical', 'greedy', 'n_below', 0, 'int')} below and "
  f"one exact tie, Holm p = {h3('Critical', 'greedy', 'p_holm12', fmt='p')}. IQL is **below** the cooperative baseline at "
  f"every level (0/10 seeds above; Holm p = {h3('Critical', 'cooperative', 'p_holm12', fmt='p')} each). The gap is "
  f"{h3('Abundant', 'cooperative', 'mean_diff', fmt='sf')} at Abundant and {h3('Critical', 'cooperative', 'mean_diff', fmt='sf')} "
  "at Critical.")
P("Two cautions apply. The greedy baseline's agents move in lockstep, so beating it shows that IQL improves on "
  "*uncoordinated identical agents*, not on the best selfish strategy. The large gap to the cooperative baseline shows "
  "that independent learners with 8,000 episodes learn only part of the coordination that a simple hand-written "
  "convention achieves with the same information.")
H(2, "9.4 Exp2: cooperation under scarcity (H2)")
rows = []
names = {"cr": "C5 cooperation rate CR", "ear": "C1 effective assist rate EAR", "rsr": "C2 redundant search RSR",
         "rsr_other": "C2 redundant search, others RSR_other", "tdi": "C3 territory division TDI",
         "pss": "C4a productive spend share PSS", "gini_consumption": "C4b consumption Gini"}
for k in ["cr", "pss", "rsr", "rsr_other", "ear", "tdi", "gini_consumption"]:
    rows.append([names[k], m("Abundant", k), m("Critical", k), om(k, "n_complete", "int", 0),
                 om(k, "friedman_p_holm"), om(k, "kendall_w", "f", 2), om(k, "page_p_holm")])
TAB("10", "H2 (CONFIRMATORY): cooperation metrics at Abundant and Critical (means, n = 10) and the Friedman test across all four "
          "levels, Holm-corrected across the 7 metrics; the Page trend p-values are also Holm-corrected.",
    ["Metric", "Abundant", "Critical", "n", "Friedman p (Holm)", "W", "Page p (Holm)"], rows,
    [2.3, 0.75, 0.75, 0.35, 1.0, 0.45, 0.9], font=8.5)
P(f"Four of the seven metrics change significantly with scarcity (Table 10, Fig. 3):")
BUL([
    f"**CR falls sharply** from {mci('Abundant', 'cr')} to {mci('Critical', 'cr')} (Holm p = {om('cr', 'friedman_p_holm')}, "
    f"W = {om('cr', 'kendall_w', 'f', 2)}). Abundant and Moderate do not differ significantly (paired difference "
    f"{R.csv(PW, {'metric': 'cr', 'pair': 'Abundant - Moderate'}, 'mean_diff')}); the collapse happens from Moderate to "
    "Critical, where budgets no longer allow two agents to converge on a heavy victim.",
    f"**PSS falls** (Holm p = {om('pss', 'friedman_p_holm')}). This mostly restates that fewer rescues are made per unit "
    "spent; PSS tracks reward (Section 7) and is not independent evidence of cooperation.",
    f"**RSR changes** (Holm p = {om('rsr', 'friedman_p_holm')}), and **RSR_other changes non-monotonically** (Holm p = "
    f"{om('rsr_other', 'friedman_p_holm')}; trend test Holm p = {om('rsr_other', 'page_p_holm', 'f', 2)}). Redundant "
    f"searching of others' areas peaks at Scarce ({m('Scarce', 'rsr_other')}, against {m('Abundant', 'rsr_other')} at "
    "Abundant). At Critical agents barely SEARCH at all, so there is little left to be redundant.",
    f"**No significant change** in the effective assist rate (Holm p = {om('ear', 'friedman_p_holm', 'f', 2)}; only "
    f"{om('ear', 'n_complete', 'int', 0)} seeds have defined values at all levels), territory division (Holm p = "
    f"{om('tdi', 'friedman_p_holm', 'f', 2)}) or the load-balance Gini (Holm p = {om('gini_consumption', 'friedman_p_holm', 'f', 2)}). "
    "An ASSIST, when it happens, is about as likely to complete a rescue under scarcity as with abundant budgets, and "
    "we find no evidence that territory division or load balance change. With 10 seeds, small changes cannot be ruled out.",
])
P("The pattern is specific. Scarcity removes *joint* actions (convergence on heavy victims) and the rescues that depend "
  "on them, while the more generic aspects of teamwork (spreading out, balancing load) show no significant change.")
FIG("3", "results/figures/fig3_exp2_cooperation.png",
    "Exp2 / H2: the seven cooperation metrics by scarcity level (per-seed lines; mean ± 95% CI). The cooperation rate CR "
    "collapses under scarcity, while territory division, load balance and assist efficiency show no significant trend.")
H(2, "9.5 Exp4: individual versus collective interest (exploratory)")
rows = []
for l in LV:
    rows.append([l, R.ci(E4, {"level": l, "measure": "e1"}, "mean_per_seed"), R.ci(E4, {"level": l, "measure": "e2"}, "mean_per_seed"),
                 R.ci(E4, {"level": l, "measure": "e3"}, "mean_per_seed"),
                 R.csv(E4, {"level": l, "measure": "spearman(best individual return, collective return)"}, "mean_per_seed", 2)])
TAB("11", "Exp4 (EXPLORATORY): abandonment (E1) and duplicate light rescues (E2) per episode, share of conflict episodes "
          "(E3), and Spearman correlation between the best agent's individual return and the collective return across "
          "episodes.",
    ["Level", "E1 abandonment", "E2 duplicates", "E3 conflict share", "Spearman"], rows, [0.9, 1.5, 1.5, 1.5, 0.8], font=8.5)
P(f"Abandonment events fall from {R.csv(E4, {'level': 'Abundant', 'measure': 'e1'}, 'mean_per_seed')} to "
  f"{R.csv(E4, {'level': 'Critical', 'measure': 'e1'}, 'mean_per_seed')} per episode. This most likely does not reflect better coordination: "
  "under scarcity agents rarely meet at a heavy victim at all, so there is nothing to abandon. The best individual "
  "and the collective return remain strongly aligned at every level (Spearman about 0.95). Within this reward design, "
  "individual and collective interests rarely diverge; the main obstacle is the difficulty of joint action rather than "
  "a social dilemma. This differs from the resource-scarcity dilemmas of [4]; one plausible reason is that our team reward term makes every "
  "rescue valuable to every agent.")

# =====================================================================================================================
# 10 Attribution
# =====================================================================================================================
H(1, "10. Attribution: is the scarcity effect due to cooperation? (review point R2)")
H(2, "10.1 Logic")
P("Scarcity is manipulated with everything else held fixed (same maps, seeds, exploration streams and evaluation "
  "tie-breaks). The statement *scarcity lowers rescue performance in this environment and with this training "
  "procedure* is therefore causal. The statement *it does so through cooperation* is not identified by correlations "
  "between metrics and performance. We test it with interventions: A1 changes who the teammates are, A2 removes a "
  "teammate, A4 removes joint training, and A3 removes the need for cooperation. A5 and A6 check two alternative "
  "explanations (non-stationarity and sample size), and A8 reports the observational association.")
H(2, "10.2 A1: teammate mismatch (H4)")
rows = []
for l in LV:
    w = {"level": l}
    rows.append([l, R.csv(H4, w, "original_mean"), R.csv(H4, w, "mismatch_mean"),
                 f"{R.csv(H4, w, 'mean_diff', 4 if l == 'Abundant' else 3)} [{R.csv(H4, w, 'ci_lo')}, {R.csv(H4, w, 'ci_hi')}]",
                 R.csv(H4, w, "relative_drop", 0, "pct"), R.csv(H4, w, "seeds_original_better", 0, "int"),
                 R.csv(H4, w, "p_holm4", fmt="p")])
TAB("12", "H4 / A1 (CONFIRMATORY): original teams vs mismatched teams built from agents of different seeds (paired by "
          "seed; Holm across 4 levels).",
    ["Level", "Original", "Mismatched", "Difference [95% CI]", "Relative drop", "Seeds original better", "p (Holm)"], rows,
    [0.9, 0.8, 0.9, 1.6, 0.8, 0.9, 0.7], font=8.5)
P(f"**H4 confirmed at three of four levels.** Mixing agents from different training seeds lowers RF by "
  f"{R.csv(H4, {'level': 'Abundant'}, 'relative_drop', 0, 'pct')}, {R.csv(H4, {'level': 'Moderate'}, 'relative_drop', 0, 'pct')} "
  f"and {R.csv(H4, {'level': 'Scarce'}, 'relative_drop', 0, 'pct')} (relative to the original team) at "
  f"Abundant, Moderate and Scarce. At Critical the drop ({R.csv(H4, {'level': 'Critical'}, 'mean_diff')}) is not "
  f"significant (Holm p = {R.csv(H4, {'level': 'Critical'}, 'p_holm4', fmt='p')}), consistent with there being little "
  "joint behaviour left to disrupt. Each seed's agents therefore learn conventions that work with *their own* "
  "teammates and only partly with others. Each agent appears in several mismatched teams, so the 10 paired differences "
  "are not fully independent (preregistered caveat); the per-seed points in Fig. 4 show the effect is not driven by one "
  "seed.")
H(2, "10.3 A2: removing a teammate (exploratory)")
P(f"Replacing one learned agent at test time by a random agent lowers RF at Abundant by "
  f"{ex('A2 RF intact - ablated (random)', 'Abundant')} (to {ex('A2 RF intact - ablated (random)', 'Abundant', 'mean_b')}); "
  f"replacing it by an agent that only WAITs lowers RF by {ex('A2 RF intact - ablated (wait)', 'Abundant')} "
  f"(to {ex('A2 RF intact - ablated (wait)', 'Abundant', 'mean_b')}). The drops shrink with scarcity "
  f"(WAIT replacement at Critical: {ex('A2 RF intact - ablated (wait)', 'Critical')}). For comparison, the same ablation "
  f"lowers the cooperative baseline at Abundant from {R.csv(A2C, {'level': 'Abundant', 'replacement': 'none'}, 'rf')} to "
  f"{R.csv(A2C, {'level': 'Abundant', 'replacement': 'random'}, 'rf')} (random) or "
  f"{R.csv(A2C, {'level': 'Abundant', 'replacement': 'wait'}, 'rf')} (WAIT). A WAIT-only teammate hurts the learned team more "
  "than a random one, plausibly because a random teammate still sometimes ASSISTs by chance. Part of the drop is simply the loss "
  "of one third of the team's search and budget, so A2 alone does not isolate cooperation.")
H(2, "10.4 A4: jointly trained vs solo-trained agents (H6)")
rows = []
for l in LV:
    w = {"level": l}
    rows.append([l, R.csv(H6, w, "joint_mean"), R.csv(H6, w, "solo_mean"),
                 f"{R.csv(H6, w, 'mean_diff')} [{R.csv(H6, w, 'ci_lo')}, {R.csv(H6, w, 'ci_hi')}]",
                 R.csv(H6, w, "seeds_joint_better", 0, "int"), R.csv(H6, w, "p_holm4", fmt="p")])
TAB("13", "H6 / A4 (CONFIRMATORY): teams of jointly trained agents vs teams of three agents each trained alone (paired by "
          "seed; Holm across 4 levels).",
    ["Level", "Joint", "Solo team", "Difference [95% CI]", "Seeds joint better", "p (Holm)"], rows,
    [0.9, 0.8, 0.9, 1.9, 1.0, 0.8])
P(f"**H6 confirmed at every level**, with large effects (difference {R.csv(H6, {'level': 'Abundant'}, 'mean_diff')} at "
  f"Abundant). Agents that learned with teammates are far better teammates. **Limitation:** a solo agent never "
  "observes a teammate during training (its teammate feature f3 is always *none*). At deployment it meets observations "
  "it has never seen, with untrained, zero-valued entries in its Q-table. The gap therefore combines two effects: what "
  "was learned from teammates, and an observation distribution shift. A4 shows that joint training matters, but it "
  "overstates how much of that is coordination.")
FIG("4", "results/figures/fig4_attribution.png",
    "Attribution checks (mean ± 95% CI over 10 seeds). Mismatching teammates (A1), replacing one agent (A2) and solo "
    "training (A4) all lower rescue performance, and the effects shrink as scarcity grows. The right panel (A6) shows that "
    "the scarcity trend survives equal training steps.")
H(2, "10.5 A3: does scarcity hurt more when cooperation is necessary? (H5)")
P("A3 trains the full sweep in a second world that is identical (same maps, victim cells, seeds and absolute budgets) "
  "except that every victim is light, so cooperation is never necessary. If scarcity acts mainly by making the "
  "necessary cooperation impossible, the heavy-victim world should lose more from Abundant to Critical. The "
  "preregistered contrast is the per-seed difference-in-differences (DiD):")
EQ("DiD_{s} = [RF_{s}(Abundant) − RF_{s}(Critical)]_{heavy world} − [RF_{s}(Abundant) − RF_{s}(Critical)]_{all-light world}")
rows = []
for l in LV:
    rows.append([l, m(l, "rf"), m(l, "rf", block="p0"), R.js(RJ, f"A3_oracle.main.{l}"), R.js(RJ, f"A3_oracle.p0.{l}")])
TAB("14", "A3 inputs: learned RF (n = 10) and oracle reference RF in the heavy-victim world and the all-light world, both at "
          "the main H = 105 and B_ref = 64.",
    ["Level", "IQL heavy world", "IQL all-light world", "Oracle ref. heavy", "Oracle ref. all-light"], rows,
    [1.0, 1.3, 1.4, 1.3, 1.4])
P(f"**H5: significant, in the opposite direction to the cooperation-bottleneck prediction (CONFIRMATORY).** "
  f"DiD = {rj('H5.mean_did', fmt='sf')} [{rj('H5.ci_lo')}, {rj('H5.ci_hi')}], {rj('H5.seeds_positive', 0, 'int')}/10 seeds "
  f"positive, exact Wilcoxon p = {rj('H5.p', fmt='p')}. In absolute points, scarcity costs the *all-light* world more. "
  "Table 15 shows why this cannot be read as 'cooperation protects against scarcity':")
rows = [["Raw RF (H5, primary)", "CONFIRMATORY", f"{rj('H5.mean_did', fmt='sf')} [{rj('H5.ci_lo')}, {rj('H5.ci_hi')}]",
         did("raw_primary", "Critical", "seeds_positive", 0, "int"),
         f"{did('raw_primary', 'Critical', 'retained_p05', 3, 'f')} vs {did('raw_primary', 'Critical', 'retained_p0', 3, 'f')}"],
        ["Oracle-normalised RF", "SECONDARY", didci("oracle_normalised_primary", "Critical"),
         did("oracle_normalised_primary", "Critical", "seeds_positive", 0, "int"),
         f"{did('oracle_normalised_primary', 'Critical', 'retained_p05', 3, 'f')} vs {did('oracle_normalised_primary', 'Critical', 'retained_p0', 3, 'f')}"],
        ["Raw RF, all-light world at own calibration", "SECONDARY", didci("raw_secondary_own_calibration", "Critical"),
         did("raw_secondary_own_calibration", "Critical", "seeds_positive", 0, "int"),
         f"{did('raw_secondary_own_calibration', 'Critical', 'retained_p05', 3, 'f')} vs {did('raw_secondary_own_calibration', 'Critical', 'retained_p0', 3, 'f')}"],
        ["Oracle-normalised, own calibration", "SECONDARY", didci("oracle_normalised_secondary", "Critical"),
         did("oracle_normalised_secondary", "Critical", "seeds_positive", 0, "int"),
         f"{did('oracle_normalised_secondary', 'Critical', 'retained_p05', 3, 'f')} vs {did('oracle_normalised_secondary', 'Critical', 'retained_p0', 3, 'f')}"],
        ["Log of RF drop (main budgets)", "POST HOC", didci("posthoc_log_ratio_primary", "Critical"),
         did("posthoc_log_ratio_primary", "Critical", "seeds_positive", 0, "int"),
         f"{did('posthoc_log_ratio_primary', 'Critical', 'retained_p05', 3, 'f')} vs {did('posthoc_log_ratio_primary', 'Critical', 'retained_p0', 3, 'f')}"],
        ["Log of RF drop, own calibration", "POST HOC", didci("posthoc_log_ratio_secondary", "Critical"),
         did("posthoc_log_ratio_secondary", "Critical", "seeds_positive", 0, "int"),
         f"{did('posthoc_log_ratio_secondary', 'Critical', 'retained_p05', 3, 'f')} vs {did('posthoc_log_ratio_secondary', 'Critical', 'retained_p0', 3, 'f')}"]]
TAB("15", "A3 difference-in-differences, Abundant vs Critical, under all analyses. Positive = scarcity removes more in the "
          "heavy-victim world. 'Retained' = RF(Critical)/RF(Abundant) in the heavy vs all-light world (for oracle-normalised "
          "rows, of the normalised RF). Only the first row is a hypothesis test.",
    ["Analysis", "Family", "DiD [95% CI]", "Seeds > 0", "Retained heavy vs all-light"], rows,
    [1.8, 1.25, 1.55, 0.55, 1.35], font=8.5,
    note="The H5 interval comes from the confirmatory bootstrap (results.json); the curve analyses in "
         "a3_did_all.csv use their own bootstrap stream, so the raw Critical interval there differs in the third decimal.")
P("Three observations decide the interpretation:")
BUL([
    f"**Floor and ceiling effects.** The all-light world starts much higher at Abundant ({m('Abundant', 'rf', block='p0')} vs "
    f"{m('Abundant', 'rf')}), and the heavy-victim world is already near the floor at Critical ({m('Critical', 'rf')}). "
    "A world near the floor cannot lose many more points, so an additive DiD can be pulled negative by scale alone.",
    f"**On a proportional scale the sign reverses.** The heavy-victim world keeps "
    f"{did('raw_primary', 'Critical', 'retained_p05', 0, 'pct')} of its Abundant RF at Critical, the all-light world "
    f"{did('raw_primary', 'Critical', 'retained_p0', 0, 'pct')}. The post hoc log-scale DiD is "
    f"{didci('posthoc_log_ratio_primary', 'Critical')}. This analysis was added after seeing the result (C4; a sign "
    "error in its first version was corrected, C5) and is exploratory only.",
    f"**The result depends on calibration.** When the all-light world receives its own calibration (smaller B_{{ref}} = "
    f"{R.ym(CAL, 'configurations.main_p0.B_ref')}), the oracle-normalised DiD is "
    f"{didci('oracle_normalised_secondary', 'Critical')}, with a CI that includes zero, and the post hoc log DiD becomes "
    f"negative ({didci('posthoc_log_ratio_secondary', 'Critical')}). Its own-calibration Critical budget (b_{{0}} = 8) is "
    f"severe: even the oracle reference rescues only {R.js(RJ, 'A3_oracle.p0sec.Critical')} of victims there.",
])
P("**Conclusion on A3.** The preregistered test rejects 'no difference', but in the direction that does *not* support "
  "a specific cooperation bottleneck, and the sign depends on the scale (points or proportions) and on how the comparison "
  "world is calibrated. We therefore make **no claim** that scarcity specifically destroys cooperation-dependent "
  "rescues more than independent ones. What A3 does show robustly is that scarcity strongly reduces performance in "
  f"both worlds (trend test p = {rj('trend_p0.page.p', fmt='p')} in the all-light world), so a large scarcity effect "
  "arises even when cooperation is never required.")
FIG("5", "results/figures/fig5_a3_did.png",
    "A3: the heavy-victim and all-light worlds across scarcity levels (means ± 95% CI, with oracle reference curves) and "
    "the DiD at the main budgets: raw (primary), oracle-normalised (secondary) and log-scale (post hoc). "
    "The absolute DiD is negative (the all-light world loses more points); proportionally the heavy-victim world keeps "
    "less. The sign is scale- and calibration-dependent.")
H(2, "10.6 A6: is it just fewer training steps? (exploratory)")
steps = {l: R.agg(TR, {"block": "main", "level": l}, "env_steps", "mean", 0, "int") for l in LV}
P(f"With equal episodes, scarce runs see far fewer environment steps, because their episodes end early on exhaustion "
  f"(mean per run: {steps['Abundant']} at Abundant, {steps['Moderate']} at Moderate, {steps['Scarce']} at Scarce, "
  f"{steps['Critical']} at Critical). In A6 the scarce levels are trained until they have used as many steps as the "
  f"Abundant run of the same seed. RF changes by {exci('A6 RF equal-steps - equal-episodes', 'Moderate')} at Moderate "
  f"(unadjusted p = {ex('A6 RF equal-steps - equal-episodes', 'Moderate', 'p_unadjusted', fmt='p')}), "
  f"{exci('A6 RF equal-steps - equal-episodes', 'Scarce')} at Scarce and "
  f"{exci('A6 RF equal-steps - equal-episodes', 'Critical')} at Critical. The scarcity trend is unchanged (Page "
  f"p = {rj('A6_equal_steps_trend.page.p', fmt='p')}). Fewer training steps explain a small part of the Moderate "
  "result and none of the overall trend.")
H(2, "10.7 A5: non-stationarity (exploratory)")
P(f"Fig. 7 shows the diagnostics. Policy churn stays at or above the 5% stability threshold at the end of training, "
  f"validation RF still fluctuates between checkpoints (Fig. 1), and the mean absolute TD error is still rising at "
  f"8,000 episodes. Only "
  f"{rj('sensitivity.stable_runs_total', fmt='int')} of {N_RUNS} runs meet the preregistered stability criterion (0 of 40 "
  "in the main block). The preregistered *stable runs only* sensitivity analysis could therefore not be computed. "
  f"The preregistered best-validation checkpoint gives the same H1 conclusion (Friedman p = "
  f"{rj('sensitivity.bestval_friedman.p', fmt='p')}, W = {rj('sensitivity.bestval_friedman.kendall_w', 2)}), with higher "
  f"RF at Abundant ({m('Abundant', 'rf', ck='bestval')} vs {m('Abundant', 'rf')}). The learners are still moving, but the "
  "scarcity ordering is the same wherever the policy is sampled.")
FIG("7", "results/figures/fig7_a5_nonstationarity.png",
    "A5 non-stationarity diagnostics: policy churn between checkpoints and mean |TD error| for the main sweep, and the "
    "number of runs per block that meet the stability criterion. Policies keep changing at 8,000 episodes, the TD error is "
    "still rising, and only 5 of 350 runs are stable.")
H(2, "10.8 A8: association between cooperation and performance (exploratory, observational)")
P(f"A8 regresses each seed's RF on the six standardised cooperation metrics plus the scarcity level (n = "
  f"{rj('A8.n_obs', fmt='int')} seed-level observations; {rj('A8.n_excluded_undefined_ear', fmt='int')} excluded because EAR "
  f"was undefined). The level dummies alone explain R² = {rj('A8.r2_levels_only')}; adding the metrics raises this to "
  f"{rj('A8.r2_joint')}. In single-metric models with the level held fixed, CR has a coefficient of "
  f"{R.csv(A8, {'model': 'single', 'term': 'cr'}, 'coef')} [{R.csv(A8, {'model': 'single', 'term': 'cr'}, 'ci_lo')}, "
  f"{R.csv(A8, {'model': 'single', 'term': 'cr'}, 'ci_hi')}] RF per standard deviation; seeds that cooperate more rescue more. "
  f"In the joint model only PSS keeps a CI that excludes zero ({R.csv(A8, {'model': 'joint', 'term': 'pss'}, 'coef')} "
  f"[{R.csv(A8, {'model': 'joint', 'term': 'pss'}, 'ci_lo')}, {R.csv(A8, {'model': 'joint', 'term': 'pss'}, 'ci_hi')}]). "
  f"CR's interval includes zero ({R.csv(A8, {'model': 'joint', 'term': 'cr'}, 'coef')} "
  f"[{R.csv(A8, {'model': 'joint', 'term': 'cr'}, 'ci_lo')}, {R.csv(A8, {'model': 'joint', 'term': 'cr'}, 'ci_hi')}]). PSS and CR "
  f"are strongly collinear (VIF {rj('A8.vif.pss', 1)} and {rj('A8.vif.cr', 1)}), and PSS largely restates reward.")
P("**This is association, not causation.** Seeds differ in many ways at once, the metrics are outcomes of the same "
  "policy as RF, and 38 observations from 10 seeds cannot separate them. A8 is consistent with the intervention results, "
  "but adds no causal evidence of its own.")
FIG("8", "results/figures/fig8_a8_association.png",
    "A8 (observational): seed-level RF against the cooperation rate, coloured by scarcity level, and the regression "
    "coefficients of the single-metric and joint models. Higher cooperation goes with higher RF within a level, but in "
    "the joint model only C4a PSS (which tracks reward) remains distinguishable from zero. Not a causal estimate.")
H(2, "10.9 What we can and cannot conclude")
BOX("We can conclude (within this environment, IQL, and 8,000 episodes)", [
    "Scarcity causes a large, monotone fall in rescue performance, in every seed, and in every robustness variant tested.",
    "Under scarcity the learned teams stop performing joint rescues; the cooperation rate and heavy-victim rescues "
    "collapse, while territory division and load balance do not change significantly.",
    "Learned teams rely on co-adapted conventions: mismatched teammates lower performance at three of four levels, and "
    "jointly trained teams far outperform solo-trained ones (the latter partly due to distribution shift).",
    "A large scarcity effect does not need cooperation to arise: an otherwise identical world without heavy victims "
    "also shows a steep decline.",
], kind="good")
BOX("We cannot conclude", [
    "That scarcity hurts *more* when cooperation is necessary: the preregistered DiD is significant in the opposite "
    "direction on the absolute scale, and its sign changes with the scale and the calibration.",
    "That cooperation *causes* the higher performance of some seeds: A8 is observational.",
    "Anything about converged or optimal IQL behaviour: no main run met the stability criterion.",
    "That IQL beats a selfish strategy in general: the greedy baseline is uncoordinated and moves in lockstep, and IQL "
    "does not beat it significantly at Critical.",
    "That the results extend to other algorithms, team sizes, small maps, or a ρ = 0.1 regime.",
], kind="bad")

# =====================================================================================================================
# 11 Generalisation
# =====================================================================================================================
H(1, "11. Generalisation and robustness (exploratory)")
H(2, "11.1 Transfer across scarcity levels")
rows = []
for tr in LV:
    rows.append([tr] + [R.ci(TM, {"train_level": tr, "test_level": te}, "mean_rf") for te in LV])
TAB("16", "Exp5 transfer matrix (EXPLORATORY): rows = level trained at, columns = level tested at; mean RF [95% CI], n = 10.",
    ["Trained at", "Test Abundant", "Test Moderate", "Test Scarce", "Test Critical"], rows, [1.0, 1.4, 1.4, 1.4, 1.4],
    font=8.5)
P(f"Policies are specialised to their training budget. A policy trained at Abundant collapses when deployed at Critical "
  f"({R.csv(TM, {'train_level': 'Abundant', 'test_level': 'Critical'}, 'mean_rf')}, against "
  f"{R.csv(TM, {'train_level': 'Critical', 'test_level': 'Critical'}, 'mean_rf')} for the Critical-trained policy). Most likely it "
  "spends as if budget were plentiful and runs out before reaching victims. Conversely, Moderate- and Scarce-trained policies do "
  "better at Critical than Critical-trained ones "
  f"({R.csv(TM, {'train_level': 'Moderate', 'test_level': 'Critical'}, 'mean_rf')} and "
  f"{R.csv(TM, {'train_level': 'Scarce', 'test_level': 'Critical'}, 'mean_rf')}). A plausible reason is that training at Critical "
  "yields few successful episodes to learn from. Policies do not transfer well across budget levels, even though the "
  "budget feature f4 means the same absolute amount at every level.")
FIG("6", "results/figures/fig6_exp5_generalization.png",
    "Exp5 generalisation: cross-ρ transfer matrix and the same-distribution vs shifted test set. Policies trained with "
    "abundant budgets fail under scarcity; the shifted maps lower performance but preserve the scarcity ordering.")
H(2, "11.2 Shifted test maps, alternate configuration, pooled budgets")
rows = []
for l in LV:
    rows.append([l, m(l, "rf"), ex("Shifted test - same-distribution test RF", l, "mean_a"), m(l, "rf", block="pooled"),
                 m(l, "rf", block="alt"), m(l, "rf", block="eqsteps") if l != "Abundant" else "(= main)"])
TAB("17", "Learned RF in the robustness variants (mean of 10 seeds). Shifted: same policies on denser, more cluttered test "
          "maps. Pooled: shared team budget. Alternate: 12 × 12 maps with their own calibration. Equal steps: A6.",
    ["Level", "Main", "Shifted test", "Pooled budget", "Alternate config.", "Equal steps"], rows,
    [0.9, 0.9, 1.1, 1.1, 1.2, 1.1])
BUL([
    f"**Shifted test maps** (wall share 0.25, victim density 0.09): RF is lower at every level (e.g. "
    f"{ex('Shifted test - same-distribution test RF', 'Abundant', 'mean_a')} vs {m('Abundant', 'rf')} at Abundant), and the "
    "scarcity ordering is unchanged.",
    f"**Pooled budgets** raise RF somewhat (Moderate {exci('Pooled - per-agent RF', 'Moderate')}, unadjusted p = "
    f"{ex('Pooled - per-agent RF', 'Moderate', 'p_unadjusted', fmt='p')}; Critical {exci('Pooled - per-agent RF', 'Critical')}, "
    f"p = {ex('Pooled - per-agent RF', 'Critical', 'p_unadjusted', fmt='p')}). Plausibly, sharing removes the risk that "
    "the agent that needs to pay is the one that has run out. The scarcity trend is just as strong.",
    f"**Alternate configuration** (12 × 12, density 0.04, own calibration H = 150, B_{{ref}} = 87): RF is "
    f"{m('Abundant', 'rf', block='alt')} / {m('Moderate', 'rf', block='alt')} / {m('Scarce', 'rf', block='alt')} / "
    f"{m('Critical', 'rf', block='alt')}. At Abundant almost all episodes end at the horizon on the larger map "
    f"(share {m('Abundant', 'horizon', block='alt', fmt='pct', nd=1)}), so performance there is limited by time. Main and alternate configurations use "
    "different maps, so they are compared descriptively only.",
])
rows = []
for k, name in [("trend_pooled", "Pooled budget"), ("trend_alt", "Alternate configuration"), ("trend_p0", "All-light world (A3)"),
                ("trend_p0sec", "All-light, own calibration"), ("trend_shifted", "Shifted test maps"),
                ("A6_equal_steps_trend", "Equal environment steps (A6)")]:
    rows.append([name, rj(f"{k}.friedman.chi2", 1), rj(f"{k}.friedman.kendall_w", 2), rj(f"{k}.page.p", fmt="p")])
TAB("18", "The scarcity trend in every robustness variant (Friedman across the 4 levels, n = 10 seeds; Page two-sided). "
          "EXPLORATORY.",
    ["Variant", "Friedman χ²(3)", "Kendall's W", "Page p"], rows, [2.6, 1.3, 1.2, 1.3])
FIG("9", "results/figures/fig9_robustness.png",
    "Robustness: learned RF by scarcity level across budget scope, map configuration and victim mix. The decline with "
    "scarcity appears in every variant.", width=5.6)

# =====================================================================================================================
# 12 Limitations
# =====================================================================================================================
H(1, "12. Limitations and threats to validity")
BUL([
    f"**No convergence (most important).** All results are for 8,000 training episodes. Only "
    f"{rj('sensitivity.stable_runs_total', fmt='int')}/{N_RUNS} runs, and none of the main runs, meet the preregistered "
    "stability criterion; churn and TD error are still changing. With more training, absolute levels and possibly "
    "the size of some effects could change. The scarcity ordering held at the final and the best-validation "
    "checkpoint, but we cannot claim it would hold at convergence.",
    "**Ten seeds.** n = 10 per condition gives exact Wilcoxon p-values with a floor of about 0.002. It detects large, "
    "consistent effects (all confirmatory positives here have 8–10 seeds in the same direction) but has little power for "
    "small ones. The non-significant results (EAR, TDI, Gini, greedy at Critical, A1 at Critical) are inconclusive, not "
    "evidence of no effect.",
    "**A3 depends on scale and calibration.** The preregistered additive DiD is negative; a proportional version is "
    "positive; calibrating the comparison world on its own makes the normalised DiD null. No single reading is "
    "privileged, so we draw no conclusion about a cooperation-specific bottleneck (Section 10.5).",
    "**A4 confound.** Solo agents never observed a teammate in training, so the joint–solo gap includes an observation "
    "distribution shift, not only coordination learning.",
    "**Greedy baseline.** Its agents run identical deterministic rules and move in lockstep (kept as implemented by "
    "group decision D22). It is a weak representative of selfish behaviour; IQL's advantage over it should not be read "
    "as an advantage over selfishness in general.",
    "**A8 is observational.** Metrics and RF are outcomes of the same policies; collinearity (VIF ≈ 8) prevents separating "
    "CR from PSS; PSS largely tracks reward.",
    "**Metric validity.** PSS failed its independence check (it tracks reward) and is interpreted accordingly. EAR is "
    "undefined for seeds that never ASSIST, which reduced its n to 8 in H2.",
    "**Calibration limits.** Critical (ρ = 0.2) misses the intended target band because ρ = 0.1 is mostly infeasible. ρ "
    "is comparable across maps with L ≥ 10 but not on 8 × 8 maps. The analytic budget estimate is about half the "
    "empirical consumption.",
    "**Time-limited Abundant regime.** At Abundant most learned episodes end at the horizon, so this level partly measures "
    "speed rather than budget use, especially on the 12 × 12 maps.",
    "**Scope.** One environment family, three agents, tabular IQL with a hand-designed observation, and no communication. "
    "Other MARL methods (e.g. centralised training with decentralised execution) may cope with scarcity differently.",
    "**Multiple analyses.** Confirmatory families are Holm-corrected; exploratory p-values are not and should be read "
    "descriptively. One analysis (log-scale A3) is post hoc and labelled as such.",
])

# =====================================================================================================================
# 13 Reproducibility
# =====================================================================================================================
H(1, "13. Reproducibility")
P("Everything in this report can be regenerated from the repository with Python 3 and the pinned scientific packages (NumPy, SciPy, pandas, matplotlib; no deep-learning "
  "framework); the Word file is rendered with Node.js and the docx package. Package versions are pinned in requirements.txt. The main commands are:")
CODE([
    "pip install -r requirements.txt",
    "python scripts/run_all.py --quick     # whole pipeline, reduced scale, < 10 min",
    "python scripts/run_all.py --full      # the full study (about 2.5 h on 2 cores)",
    "pytest -q                            # all tests",
    "python scripts/run_calibration.py    # Phase 3 calibration",
    "python scripts/run_experiments.py train   # 350 runs, resumable",
    "python scripts/run_experiments.py eval    # frozen test sets",
    "python scripts/run_stats.py          # all statistics",
    "python scripts/make_tables.py && python scripts/make_figures.py",
    "bash scripts/build_report.sh         # this report (docx + pdf)",
    "python scripts/verify_results.py     # re-check results and report",
], title="Regenerating the results and this report")
P("The quick run trains the main sweep with 3 seeds × 3,000 episodes, evaluates it and all baselines on 30 test maps, and "
  "runs the H0 and H1 statistics, writing to results_quick/ (never to results/). It checks that every stage of the "
  "pipeline works; its numbers are not results of the study (3 seeds cannot reach the preregistered significance gate). "
  "On two CPU cores it completes in about three minutes; the timing is logged in results_quick/quick_summary.md.")
BUL([
    "**Seeds and common random numbers.** Instance seeds, training seeds, exploration streams, evaluation tie-breaks, "
    "A1 permutations and bootstrap generators are all fixed and recorded.",
    "**Frozen inputs.** Instance lists with SHA-256 hashes; the preregistration, design spec, calibration rules and "
    "outputs are hashed in results/calibration/freeze_manifest.json.",
    f"**Integrity.** results/phase5/phase5_manifest.json hashes every raw evaluation file; results/manifest.json hashes "
    "every result file.",
    f"**Verification.** scripts/verify_results.py recomputes the confirmatory statistics from the seed-level data, re-runs "
    f"the statistics script and requires byte-identical outputs, checks every claim in docs/claims.yaml, and checks every "
    f"number in this report (docs/report_numbers.yaml: source file, locator, raw value, displayed text). All checks pass; the list of checks and the "
    f"current count are in results/logs/verify_results.txt.",
    "**Decision trail.** docs/design_decisions.md (D1–D29) and docs/deviations_log.md (P1–P8, N1–N5, C1–C6).",
])

# =====================================================================================================================
# 14 Success criteria
# =====================================================================================================================
H(1, "14. Check against the eight success criteria")
P("The proposal defined eight success criteria. The preregistration (§10) made each of them checkable before any "
  "result was known.")
rows = [
    ["1 Functional environment", "all tests pass", f"{N_TESTS} tests pass", "Met"],
    ["2 Learning improvement", "H0-gate passes", f"10/10 seeds above random, p = {rj('H0.p', fmt='p')}", "Met"],
    ["3 Scarcity sensitivity", "H1 Friedman rejects at α = 0.05", f"p = {om('rf', 'friedman_p')}, W = {om('rf', 'kendall_w', 'f', 2)}", "Met"],
    ["4 Cooperation measurement", "C1–C5 computed and validated on scripted episodes",
     f"all computed; validity {R.rx(P2, r'\*\*(\d+)/\d+ checks passed')}/{R.rx(P2, r'\*\*\d+/(\d+) checks passed')}; PSS tracks reward",
     "Met, with caveat"],
    ["5 Baseline comparison", "H3 reported for all baselines", "12 tests reported; not better than greedy at Critical; below cooperative everywhere", "Met (criterion is reporting)"],
    ["6 Robustness across seeds", "per-seed plots; principal findings hold in ≥ 8/10 seeds",
     "H1 10/10 seeds; H4 ≥ 8/10 where significant; H6 10/10; per-seed lines on every plot", "Met"],
    ["7 Generalisation", "test and shifted-test evaluations reported", "test, shifted test, transfer matrix, alternate map", "Met"],
    ["8 Reproducibility", "verify_results.py exits 0; manifest complete", "all checks pass (results/logs/verify_results.txt); manifests complete", "Met"],
]
TAB("19", "The eight success criteria of the proposal, as operationalised in the preregistration.",
    ["Criterion", "Operationalisation", "Evidence", "Status"], rows, [1.5, 1.8, 2.3, 0.9], font=8.5)
P("Meeting the criteria does not mean that every hypothesis was supported. The criteria are about whether the study "
  "worked and was reported properly. The scientific answer is mixed: scarcity clearly degrades performance and "
  "suppresses joint rescues, but the preregistered test of a cooperation-specific bottleneck (H5) does not support it. "
  "Also, none of the criteria required convergence, and none was reached.")

# =====================================================================================================================
# References
# =====================================================================================================================
H(1, "References")
P("[1]–[7] are the references of the project proposal. [8]–[14] were added for methods used in this report. Every "
  "added reference was checked against its original publication record (title, authors, venue, volume, issue, pages, "
  "year) on 12 November 2026; the record is in docs/references_verification.md.", style="small")
refs = [
    "[1] Y. Shoham and K. Leyton-Brown, *Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations*. Cambridge University Press, 2008.",
    "[2] J. Peña Queralta, J. Taipalmaa, B. C. Pullinen, V. K. Sarker, T. N. Gia, H. Tenhunen, M. Gabbouj, J. Raitoharju and T. Westerlund, “Collaborative multi-robot search and rescue: Planning, coordination, perception, and active vision,” *IEEE Access*, vol. 8, pp. 191617–191643, 2020.",
    "[3] K. Zhang, Z. Yang and T. Başar, “Multi-agent reinforcement learning: A selective overview of theories and algorithms,” in *Handbook of Reinforcement Learning and Control*, Studies in Systems, Decision and Control, vol. 325, pp. 321–384, Springer, 2021.",
    "[4] J. Z. Leibo, V. Zambaldi, M. Lanctot, J. Marecki and T. Graepel, “Multi-agent reinforcement learning in sequential social dilemmas,” in *Proc. 16th Int. Conf. on Autonomous Agents and Multiagent Systems (AAMAS)*, pp. 464–473, 2017.",
    "[5] L. H. Nguyen, Z. Yang, J. Zhu, J. Li and F. Jin, “Coordinating disaster emergency response with heuristic reinforcement learning,” arXiv:1811.05010, 2018.",
    "[6] T. Hickling, M. Hogan, A. Tammam and N. Aouf, “Deep reinforcement learning based autonomous decision-making for cooperative uncrewed aerial vehicles: A search and rescue real world application,” *Journal of Field Robotics*, vol. 43, no. 7, pp. 4382–4401, 2026, doi:10.1002/rob.70248.",
    "[7] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed. MIT Press, 2018.",
    "[8] C. J. C. H. Watkins and P. Dayan, “Q-learning,” *Machine Learning*, vol. 8, no. 3–4, pp. 279–292, 1992, doi:10.1007/BF00992698.",
    "[9] M. Tan, “Multi-agent reinforcement learning: Independent vs. cooperative agents,” in *Proc. 10th Int. Conf. on Machine Learning (ICML)*, Morgan Kaufmann, pp. 330–337, 1993, doi:10.1016/B978-1-55860-307-3.50049-6.",
    "[10] S. Holm, “A simple sequentially rejective multiple test procedure,” *Scandinavian Journal of Statistics*, vol. 6, no. 2, pp. 65–70, 1979.",
    "[11] M. Friedman, “The use of ranks to avoid the assumption of normality implicit in the analysis of variance,” *Journal of the American Statistical Association*, vol. 32, no. 200, pp. 675–701, 1937, doi:10.2307/2279372.",
    "[12] E. B. Page, “Ordered hypotheses for multiple treatments: A significance test for linear ranks,” *Journal of the American Statistical Association*, vol. 58, no. 301, pp. 216–230, 1963, doi:10.2307/2282965.",
    "[13] F. Wilcoxon, “Individual comparisons by ranking methods,” *Biometrics Bulletin*, vol. 1, no. 6, pp. 80–83, 1945.",
    "[14] B. Efron, “Bootstrap methods: Another look at the jackknife,” *The Annals of Statistics*, vol. 7, no. 1, pp. 1–26, 1979, doi:10.1214/aos/1176344552.",
]
for r_ in refs:
    P(r_, style="ref")

# =====================================================================================================================
# Appendices
# =====================================================================================================================
BREAK()
H(1, "Appendix A. Hyperparameters and settings")
TAB("A1", "All settings of the main configuration (config/default.yaml, config/calibrated.yaml). Nothing was tuned on "
          "test data; the pilot changed nothing.",
    ["Group", "Setting", "Value"],
    [["Map", "grid L × L; walls; hazard share of free cells", f"{R.ym(DEF, 'env.grid_size')} × {R.ym(DEF, 'env.grid_size')}; "
                                                               f"{R.ym(DEF, 'env.wall_fraction', 2, 'f')}; {R.ym(DEF, 'env.hazard_fraction', 2, 'f')}"],
     ["Map", "victims V, density, heavy share", f"6, {R.ym(DEF, 'env.victim_density', 2, 'f')}, {R.ym(DEF, 'env.p_heavy', 1, 'f')}"],
     ["Agents", "n, radii r_{v} / r_{s} / r_{tm}", f"{R.ym(DEF, 'env.n_agents')}, " + " / ".join(R.ym(DEF, f"env.{k}") for k in ["radius_passive", "radius_search", "radius_teammate"])],
     ["Costs", "move / hazard / SEARCH / RESCUE / ASSIST / WAIT",
      " / ".join(R.ym(DEF, f"costs.{k}") for k in ["move", "move_hazard", "search", "rescue", "assist", "wait"])],
     ["Reward", "discovery / light / heavy rescuer / heavy assister / team per rescue",
      " / ".join(R.ym(DEF, f"reward.{k}", 1, "f") for k in ["discovery", "light_rescue", "heavy_rescuer", "heavy_assister", "team_per_rescue"])],
     ["Reward", "λ_{I} / λ_{T} / λ_{C}", " / ".join(R.ym(DEF, f"reward.lambda_{k}", 2, "f") for k in "ITC")],
     ["Calibrated", "horizon H; B_{ref}", f"{R.ym(CAL, 'configurations.main.H')}; {R.ym(CAL, 'configurations.main.B_ref')}"],
     ["Calibrated", "ρ levels; b_{0}", "1.0 / 0.5 / 0.3 / 0.2; " + " / ".join(R.ym(CAL, f"configurations.main.b0_per_level.{l}") for l in LV)],
     ["IQL", "α; γ; Q initialisation", "0.1; 0.98; 0"],
     ["IQL", "ε schedule", "1.0 → 0.05 linearly over the first 70% of episodes, then 0.05"],
     ["IQL", "episodes per run; checkpoint interval", "8,000; 500"],
     ["Evaluation", "policy; tie-breaks", "greedy (ε = 0); RNG seeded by (instance, agent)"],
     ["Data", "train / validation / test / shifted test / calibration maps", "1,000 / 50 / 100 / 100 / 200"],
     ["Statistics", "seeds; bootstrap resamples; α", "10 (0–9); 10,000; 0.05 after Holm"]],
    [1.1, 2.9, 2.5], font=8.5)

H(1, "Appendix B. Design decision log (summary)")
P("Full entries with alternatives, reasons and risks are in docs/design_decisions.md.", style="small")
dd = []
for line in (ROOT / "docs" / "design_decisions.md").read_text().splitlines():
    if line[:1] == "D" and line[1:2].isdigit():
        k, _, rest = line.partition(" ")
        dd.append([k, rest.split(" [")[0].rstrip(":").strip(), (rest.split(" [")[1].rstrip("]") if " [" in rest else "—")])
TAB("B1", "Design decisions D1–D29; the last column names the review point (R1–R3) each addresses.", ["ID", "Decision", "Review"],
    dd, [0.5, 5.2, 0.8], font=8)

H(1, "Appendix C. Deviations log (summary)")
P("Full text with dates, reasons and affected results is in docs/deviations_log.md. P-entries were made before the "
  "freeze; all later entries (N, C) are post-freeze notes or corrections. None changed a frozen hypothesis, parameter, "
  "test or test instance.", style="small")
dv = [
    ["P1", "pre-freeze", "Budget feature f4: integer thresholds and half-open buckets"],
    ["P2", "pre-freeze", "Paired confirmatory tests (Friedman, Page, Wilcoxon); unit = seed; one-sample tests vs baselines"],
    ["P3", "pre-freeze", "Masks and policy inputs use only observed information; stale-memory rules"],
    ["P4", "pre-freeze", "Pooled ablation: per-capita budget feature vs actual pool"],
    ["P5", "pre-freeze", "Implementation details (victim distance from base, seeding, rounding, tie-breaks)"],
    ["P6", "pre-freeze", "Metric clarifications (minimal-requirement rule, C2 same-step searches, E3 redefined)"],
    ["P7", "pre-freeze", "Cooperative baseline search convention; greedy affordable targets and one heavy attempt"],
    ["P8", "pre-freeze", "A3 primary comparison at the main H and B_ref; own calibration secondary"],
    ["N1", "note", "Critical cooperative RF 0.220 outside the target band (feasibility rule)"],
    ["N2", "post-freeze note", "Pilot passed; no permitted parameter changed"],
    ["C1", "post-freeze", "Mechanics of A1, A2, A3-secondary, A4, A6 fixed before any confirmatory run"],
    ["C2", "post-freeze", "Logging bug in a chunk script's exit code; completeness verified separately"],
    ["N3", "post-freeze note", "Interpretation notes recorded before Phase 6 tests (stability, A3 scale, A4 shift)"],
    ["C3", "post-freeze", "Analysis mechanics fixed before any test statistic (D26)"],
    ["C4", "post-freeze, POST HOC", "Log-scale A3 DiD added after seeing H5 (exploratory)"],
    ["C5", "post-freeze", "Sign-convention bug in the post hoc log DiD corrected"],
    ["C6", "post-freeze", "Floating-point ties snapped to zero before Wilcoxon; H3 Critical-vs-greedy p corrected"],
    ["N4", "post-freeze note", "Report written from verified result files; no analysis changed"],
    ["N5", "post-freeze note", "Quick mode, reference verification, viva package; no result changed; remaining gaps listed"],
]
TAB("C1", "Deviations and notes.", ["ID", "Type", "Change"], dv, [0.5, 1.4, 4.6], font=8.5)

H(1, "Appendix D. Glossary")
gl = [
    ["Ablation", "removing or replacing a component (here, one agent) to see how much the result depends on it"],
    ["Bootstrap CI", "confidence interval obtained by resampling the seeds with replacement many times"],
    ["Calibration", "measuring the task to set H and B_ref before any experiment"],
    ["Checkpoint", "a saved copy of the Q-tables during training (every 500 episodes)"],
    ["Churn", "share of visited observations whose greedy action changed since the last checkpoint"],
    ["Common random numbers", "using the same random streams in every condition so that differences come from the manipulation"],
    ["DiD", "difference-in-differences: how much more one world's drop is than another's"],
    ["Dormant agent", "an agent with budget below 1; it can only WAIT"],
    ["Exhaustion", "end of episode when no agent can afford a RESCUE"],
    ["Friedman test", "rank test for differences among several paired conditions [11]"],
    ["Heavy victim", "victim requiring RESCUE and ASSIST by two different agents on the same step"],
    ["Holm correction", "step-down method to control the family-wise error rate [10]"],
    ["IQL", "independent Q-learning: each agent learns its own Q-table and treats others as part of the environment"],
    ["Kendall's W", "effect size for Friedman: 1 = every seed ranks the conditions identically"],
    ["Mask", "the set of actions allowed in the current observation"],
    ["Non-stationarity", "the environment changes from an agent's view because its teammates are learning"],
    ["Oracle reference", "full-information planner used for scale; not a learner, never tested"],
    ["Page's L", "rank test for an ordered trend across paired conditions [12]"],
    ["Preregistration", "hypotheses and analysis plan fixed before data are collected"],
    ["Rank-biserial r", "effect size for the Wilcoxon test, from −1 to 1"],
    ["Rescue fraction (RF)", "rescued victims / V; the primary outcome"],
    ["ρ (rho)", "scarcity level: budget as a fraction of B_ref"],
    ["Seed", "one independent repetition of the whole training process; the unit of analysis"],
    ["Wilcoxon signed-rank", "rank test for paired differences or for differences from a constant [13]"],
]
TAB("D1", "Glossary.", ["Term", "Meaning"], gl, [1.7, 4.8], font=8.5)

H(1, "Appendix E. Review Response Matrix")
rr = [
    ["R1", "Per-agent vs global budgets", "Per-agent main design; pooled ablation with exact payment rule", "§3.2, §11.2, D1", "Pooled raises RF modestly; trend unchanged"],
    ["R1", "Feasibility at exhaustion", "Exact termination rules; dormant agents; feasibility rejection of instances", "§3.3, D2", "Scarce/Critical episodes end by exhaustion"],
    ["R1", "Operational cooperation metrics", "C1–C5 + E1–E3 from logs; scripted validation; PSS caveat", "§7, D9, D21, D22", "CR collapses; EAR, TDI, Gini unchanged"],
    ["R2", "IQL non-stationarity", "Churn, TD error, stability criterion; best-val checkpoint; equal-steps control", "§10.6–10.7, A5, A6", "No main run stable; trend robust"],
    ["R2", "Attribute performance changes to cooperation", "Interventions A1, A2, A3, A4; A8 labelled observational", "§10", "Co-adaptation shown (A1, A4); cooperation-specific bottleneck not supported (A3)"],
    ["R3", "Calibrate B_ref and ρ vs map size, density, costs, horizon", "Pre-stated rules; H and B_ref from cooperative baseline; 5 configurations; analytic check", "§5, D11, D23", "ρ comparable for L ≥ 10; not on 8 × 8"],
    ["R3", "Choice of ρ levels", "Targets on cooperative RF with oracle feasibility constraint", "§5.3, N1", "Critical = 0.2 (above target band)"],
]
TAB("E1", "How each review point was addressed, where it is documented, and what was found.",
    ["Point", "Issue", "Response", "Where", "Outcome"], rr, [0.45, 1.35, 2.15, 1.05, 1.5], font=8)

H(1, "Appendix F. Where every result comes from")
P(f"Every result number in this report is listed in docs/report_numbers.yaml with its source file, locator (row filter "
  f"and column, or JSON/YAML path), raw value and displayed text. The verifier re-reads each entry and checks that the "
  f"displayed text appears in this document. The main result files are:", style="small")
TAB("F1", "Result files behind the report's sections.",
    ["Content", "File(s)"],
    [["Calibration (§5)", "results/calibration/table_bref.csv, table_sweep_main.csv, table_sensitivity.csv, calibration_summary.json"],
     ["Condition means (§9–§11)", "results/stats/condition_means.csv (from seed_level_learned.csv)"],
     ["H0, H5, trends, A3 oracle, A8 summary", "results/stats/results.json"],
     ["H1, H2", "results/stats/h1_h2_omnibus.csv, h1_h2_pairwise.csv"],
     ["H3, baselines", "results/stats/h3_vs_baselines.csv, baselines_test.csv"],
     ["H4, H6", "results/stats/h4_A1_mismatch.csv, h6_A4_solo.csv"],
     ["A3 all analyses", "results/stats/a3_did_all.csv"],
     ["A2, A6, pooled, shifted", "results/stats/exploratory_paired.csv, a2_cooperative_baseline.csv"],
     ["A8, Exp4, transfer", "results/stats/a8_mediation.csv, exp4_individual_collective.csv, transfer_matrix.csv"],
     ["Training runs, A5", "results/phase5/training_runs.csv, results/runs/"],
     ["Figures", "results/figures/fig0a–fig9 (figure numbers in this report match the file names), results/calibration/figures/"]],
    [2.0, 4.5], font=8.5)


# =====================================================================================================================
def to_markdown(doc):
    out = []
    for b in doc:
        t = b["t"]
        if t == "title":
            out += [f"# {b['title']}: {b['subtitle']}", ""] + [f"*{x}*  " for x in b["lines"]] + ["", f"> {b['note']}", ""]
        elif t in ("h1", "h2", "h3"):
            out += ["#" * (int(t[1]) + 1) + " " + b["text"], ""]
        elif t == "p":
            out += [b["text"], ""]
        elif t in ("bullets", "numbered"):
            out += [("1. " if t == "numbered" else "- ") + x for x in b["items"]] + [""]
        elif t == "eq":
            out += [f"    {b['text']}", ""]
        elif t == "code":
            out += [f"**{b['title']}**", "", "```"] + b["lines"] + ["```", ""]
        elif t == "box":
            out += [f"> **{b['title']}**"] + [f"> - {x}" for x in b["items"]] + [""]
        elif t == "figure":
            out += [f"![Fig. {b['label']}]({'../' + b['path']})", "", f"*Fig. {b['label']}. {b['caption']}*", ""]
        elif t == "table":
            out += [f"*Table {b['label']}. {b['caption']}*", "", "| " + " | ".join(b["header"]) + " |",
                    "|" + "---|" * len(b["header"])] + ["| " + " | ".join(r) + " |" for r in b["rows"]]
            out += ([f"", f"*{b['note']}*"] if b.get("note") else []) + [""]
        elif t == "toc":
            out += ["[Table of contents]", ""]
    return "\n".join(out)


def main():
    (ROOT / "report").mkdir(exist_ok=True)
    fig_order = [b["label"] for b in DOC if b["t"] == "figure"]
    assert len(set(fig_order)) == len(fig_order), "duplicate figure label"
    tab_order = [b["label"] for b in DOC if b["t"] == "table"]
    assert len(set(tab_order)) == len(tab_order), "duplicate table label"
    (ROOT / "report" / "content.json").write_text(json.dumps({"blocks": DOC}, ensure_ascii=False, indent=1))
    (ROOT / "report" / "report_source.md").write_text(to_markdown(DOC))
    n = R.dump(ROOT / "docs" / "report_numbers.yaml")
    words = sum(len(json.dumps(b, ensure_ascii=False).split()) for b in DOC)
    print(f"blocks {len(DOC)}, figures {len(fig_order)}, tables {len(tab_order)}, registered numbers {n}, ~words {words}")


if __name__ == "__main__":
    main()
