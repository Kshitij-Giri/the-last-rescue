# Phase 9 — Complete Understanding Guide: *The Last Rescue*

*Fundamentals of AI, Group 14, IIT Gandhinagar.*

This guide teaches the whole project from first principles: the problem, the environment, the AI concepts, the code, the experiments, the results, the design decisions, the weaknesses, and the viva.

**How this guide was written.** Every statement about how the system works was checked against the repository itself, not against file names:
- the code in `src/tlr/` and `scripts/`;
- the settings in `config/`;
- the files in `results/` and `docs/`.

Every number is copied from:
- `results/` files;
- `report/report_source.md` (the text of the final report, whose numbers are machine-checked against `results/`);
- `docs/viva_guide.md`.

**Integrity rules for Phase 9.** Nothing in `src/`, `config/`, `scripts/`, `tests/`, `results/` or `report/` was changed. No experiment was re-run. Before writing, I checked all 2,426 hashed files in those folders against `results/manifest.json`, and every one matched.

**Where I add interpretation.** Where this guide goes beyond what the repository documents, it is labelled **[Interpretation]**. Documented facts carry a file reference.


**Contents**
- §0 Report vs implementation: discrepancies found
- Part A — The research problem
- Part B — The environment from scratch, including a worked episode
- Part C — AI, RL and statistics concepts used (each linked to code and results)
- Part D — The codebase module by module; architecture (D.1); execution flow (D.14)
- Part E — Experimental design
- Part F — Results and how to interpret them (F.15: what we can and cannot claim)
- Part G — Design decisions
- Part H — Limitations and critical analysis
- Part I — 45 viva questions at three levels
- Reference 1 — Maths and algorithms on one page
- Reference 2 — Concepts to master before presenting

**Relation to `docs/viva_guide.md`.** That file (Phase 8) is a short revision sheet: pitch, key numbers and 41 short answers. It was reused here and is unchanged. This guide is the full teaching version. Where they overlap, the numbers agree. One addition here: §0 item 0.1, which `viva_guide.md` does not mention.

---

## 0. Read this first: places where the report and the implementation disagree

You asked me to flag disagreements explicitly rather than resolve them silently. While reading the code and results against the report, I found the following. None of them changes a hypothesis test, a p-value or a frozen design choice. But **item 0.1 is a factual error in the report's interpretation text**, and you should know it before the viva. Phase 9 rules forbid changing the report, so none of these has been corrected there. Whether to issue an erratum is the group's decision.

| # | Report says | Repository shows | Severity |
|---|---|---|---|
| 0.1 | §9.2: "At Scarce and Critical almost every episode ends with budget exhaustion. The learners therefore face a time limit at Abundant and a budget limit under scarcity." The Review Response Matrix (Appendix E) also says "Scarce/Critical episodes end by exhaustion". | The report's **own Table 8** (from `results/stats/condition_means.csv`, final test evaluation) gives exhausted / horizon shares of **0.56 / 0.44 at Scarce and 0.51 / 0.49 at Critical**. About half of the test episodes at Scarce and Critical end at the **horizon**, meaning at least one agent still held ≥ 3 units when time ran out. During **training**, which includes exploration, exhaustion does dominate: 92% at Scarce and 95% at Critical (`results/runs/main/*/seed_*/train_log.csv`, all 10 seeds). | **Real interpretation error.** The sentence fits training episodes, not the greedy test policies it describes. The numbers in the table are correct; the sentence is not. |
| 0.2 | Table 3: ASSIST is valid when "an unrescued heavy victim is on the own cell; budget ≥ c_A". | `observation.compute_mask` also requires **at least one teammate visible on the same cell**. The design spec §1.2 states this condition too. | Omission in the report table. The code follows the frozen spec. |
| 0.3 | §6.2: "All baselines … use the same observations and masks as the learners." | The baselines receive the same **information source** (the agent's `AgentView`: its memory, its view, nearby teammates with their identities, its own budget) and the same masks. IQL instead sees a **compressed 5-feature summary** of that view (3,960 possible values) with teammate identity dropped. The cooperative baseline uses teammate *indices* for its role convention. | Imprecise wording. It matters when you explain why IQL is below the cooperative baseline (§F.3). |
| 0.4 | §6.3: the oracle "repeatedly adds the victim whose insertion into some agent's route gives the most rescues per unit of budget". | `oracle.greedy_insertion_plan` repeatedly **appends the cheapest feasible next rescue**. Ties go to the earliest finish time, then victim id, then agents. Each option is exactly one rescue, so "cheapest" is the same as "most rescues per unit of budget" for that one step. Victims are appended to the end of an agent's sequence, not inserted mid-route. | Wording only; the effect is the same. |
| 0.5 | §4.1: "maps whose free cells are not all connected are rejected." | `mapgen.generate_instance` never creates a disconnected map: it places walls one at a time and **keeps a wall only if the map stays connected**. | Mechanism differs; the outcome (always connected) is the same. |
| 0.6 | §3.5: "Directions are first moves on the cheapest path on the known map." | True for f1 and f2. f3 (teammate direction) uses the **straight-line dominant axis** (`_dominant_dir`), not a path. | Minor. |

**How to handle these in the viva.**
- If asked about 0.1, say: *"Table 8 is the evidence. During greedy test play, roughly half of Scarce and Critical episodes end at the horizon with some budget unspent. The sentence in §9.2 overstates exhaustion. Exhaustion dominates during training, which is what A6 relies on."*
- Items 0.2 to 0.6 are precision points. Know the correct version.

---

# PART A — The research problem

## A.1 Start with a real situation

Imagine an earthquake. Three rescue robots start at one base station. They must find trapped people in a damaged building and get them out. Three things make this hard:

1. **They cannot see everything.** Each robot sees only what is near it. A robot that has not visited an area does not know who is there.
2. **Some people need two robots at once.** A person under a heavy beam cannot be freed by one robot. One robot must lift while another pulls, *at the same moment*.
3. **Every movement uses battery, and batteries cannot be recharged during the mission.** A robot that wanders around exploring may later be too weak to help a teammate lift the beam.

Now ask: *if the batteries are smaller (scarcer), do the robots still manage to work together? Or does scarcity make cooperation collapse?* That is the spirit of our project.

## A.2 The same idea in our game

Our game, *The Last Rescue*, is a small computer version of this situation:

- **The map.** A 10 × 10 grid (100 cells). Some cells are walls (15%). Some free cells are hazards (10% of free cells; entering one costs extra).
- **The agents.** **Three agents** (our "robots") all start on the same **base** cell.
- **The victims.** Six per map. **Three are light**: one agent can rescue a light victim alone. **Three are heavy**: a heavy victim is rescued only if, **in the same time step**, one agent plays RESCUE and a *different* agent plays ASSIST on that victim's cell.
- **The budgets.** Every agent has its own **budget**, a number of resource units. Every action except WAIT costs units. The budget cannot be refilled or given to a teammate.

**Resource scarcity** means giving the agents smaller budgets. We control it with a single number ρ (rho):

> initial budget per agent  B₀ = round(ρ × B_ref)

Here B_ref = 64 is a *calibrated* "just enough" budget (explained in Part B.8 and Part E.3). The four scarcity levels are:

| Level | ρ | Budget per agent B₀ |
|---|---|---|
| Abundant | 1.0 | 64 |
| Moderate | 0.5 | 32 |
| Scarce | 0.3 | 19 (0.3 × 64 = 19.2) |
| Critical | 0.2 | 13 (0.2 × 64 = 12.8) |

Source: `config/calibrated.yaml`. Rounding is round-half-up in `utils.initial_budget`.

## A.3 What "cooperation" means in our problem

In everyday language, cooperation is vague. In our project it has a precise, physical meaning:

- **Necessary cooperation.** A heavy victim *cannot* be rescued without two agents acting together, on the same cell, in the same step. This is built into the rules (`env.step`, part 3).
- **Helpful cooperation.** Even for light victims, a good team spreads out instead of all searching the same area, and shares the work. This is not required, only useful.

We **measure** cooperation from what agents *do*, never from the reward they get. Part B.10 explains the seven measures. The most important one is the **cooperation rate (CR)**: the share of an agent's non-WAIT actions that were part of a successful heavy rescue (the RESCUE, the ASSIST, and the moves that brought the two agents together).

## A.4 Why multi-agent cooperation is hard

There are five difficulties, and our project has all of them:

1. **Timing.** Two agents must arrive and act *in the same step*. If one arrives early, it must wait; if one leaves, the attempt fails and the units it spent are wasted.
2. **Partial information.** An agent does not know where its teammates are unless they are within 3 cells, and it does not know their budgets.
3. **Learning at the same time (non-stationarity).** Each agent learns while the others also learn. From agent 1's point of view, its "world" includes agents 2 and 3. Because they keep changing their behaviour, agent 1's world keeps changing. Part C.6 explains this carefully.
4. **Credit assignment.** When the team succeeds, which agent's action deserved credit? A good ASSIST earns little if the partner never shows up.
5. **Scarcity adds a trade-off.** Exploring finds victims but spends budget that may be needed later for a RESCUE or ASSIST.

## A.5 The research question

From the report §1.2:

> **How does resource scarcity (ρ) affect the ability of independently learning agents to learn cooperative rescue strategies, and is any effect of ρ on rescue performance attributable to cooperation?**

There are two halves:
- **First half (descriptive and causal for scarcity):** does lowering ρ lower performance and change cooperative behaviour?
- **Second half (attribution):** *if* performance drops, is it *because* cooperation broke down, or for some other reason?

The second half is much harder, and it is where most of our honest "we cannot conclude" statements come from.

## A.6 The hypotheses we preregistered

"Preregistered" means: written down and frozen, with a cryptographic hash recorded, **before** any learning run (`docs/preregistration.md`, frozen 12 Nov 2026; hash in `results/calibration/freeze_manifest.json`). This prevents us from choosing tests after seeing the data.

| ID | Plain-English claim | Outcome |
|---|---|---|
| H0-gate | Learning works at all: at Abundant, IQL beats random agents. | **Supported** (10/10 seeds) |
| H1 | Rescue performance differs across the four scarcity levels. | **Supported** (strong, identical ordering in every seed) |
| H2 | Each of 7 cooperation metrics differs across scarcity levels. | **Supported for 4 of 7**; 3 not significant |
| H3 | IQL differs from each baseline at each level (12 tests). | IQL > random everywhere; IQL > greedy at 3 levels, **not at Critical**; IQL **< cooperative everywhere** |
| H4 (A1) | Mixing teammates from different training runs changes performance. | **Supported at 3 of 4 levels**, not at Critical |
| H5 (A3) | Scarcity hurts *more* when cooperation is necessary. | **Significant but in the opposite direction** on the preregistered scale; scale- and calibration-dependent; **no claim made** |
| H6 (A4) | Agents trained together beat agents trained alone. | **Supported at all 4 levels**, with a confound (distribution shift) |

## A.7 What the project is trying to establish, and what it establishes

**Trying to establish:** whether scarcity damages the learning of cooperation, and whether the damage to rescue performance flows through cooperation.

**Actually established (within this environment, with IQL, after 8,000 training episodes):**
- Scarcity causes a large fall in rescues.
- The learned teams stop doing joint (heavy) rescues under scarcity.
- The learned teams do rely on conventions co-adapted with their own training partners.

**Not established:**
- That the scarcity effect is *specifically* a cooperation effect. H5 went the other way and is not robust.
- Anything about converged or optimal behaviour.

---

# PART B — The environment, from scratch

The environment lives in `src/tlr/env.py` (class `RescueEnv`). Its helpers are `mapgen.py` (maps), `costs.py` (actions and costs), `observation.py` (what agents see and may do) and `rewards.py` (rewards).

## B.1 Agents and their roles

- **There are three agents, numbered 0, 1, 2** in code. In replays they are drawn as 1, 2, 3.
- **They have no fixed roles.** Any agent can explore, rescue or assist. Roles appear only through behaviour: through learning (IQL), or through a hand-written convention (the cooperative baseline, where the lowest-index agent present RESCUEs and the others ASSIST).
- **They share no communication channel.** An agent learns about teammates only by seeing them within 3 cells.

## B.2 The environment state

The **state** is everything that is true about the world at time t (spec §1.1, `env.reset`):

| Part | Code variable | Changes during an episode? |
|---|---|---|
| Map: walls, hazards, base | `inst.grid`, `inst.base` | No (static) |
| Victim cells and types (light/heavy) | `inst.victim_cells`, `inst.victim_heavy` | No |
| Which victims are rescued | `env.v_rescued` | Yes |
| Agent positions | `env.pos` | Yes |
| Agent budgets | `env.budget` | Yes |
| Time step | `env.t` | Yes |
| Each agent's memory of victims it has seen | `env.known[i]`, `env.observed[i]` | Yes |

**The map is known in advance; victims are not.** Each agent knows the static map from the start. It does not know where victims are until it sees them. This models a building whose floor plan you have but whose occupants you don't know.

**Maps are generated from one integer seed** (`mapgen.generate_instance`):
1. Choose a base near a random corner.
2. Add walls one at a time in random order. A wall is kept only if all non-wall cells stay connected to the base, so every free cell is reachable.
3. Mark 10% of free non-base cells as hazards.
4. Place V = round(0.06 × 100) = **6 victims** on non-wall cells at Chebyshev distance ≥ 2 from the base, so no victim is visible at the start. Victims can sit on hazard cells.
5. Make exactly round(0.5 × 6) = **3** of them heavy, chosen by a random permutation.

A neat detail matters for experiment A3. The random draws are made in the same order whatever the heavy share is, so the same seed with "no heavy victims" gives **exactly the same map and victim positions**; only the types change. This is what makes the A3 comparison *paired* (`mapgen.py` docstring).

## B.3 Actions and their costs

There are 8 actions (`costs.Action`). Their integer values are the column indices of the Q-table:

| Code | Action | Cost (units) | Valid only if (checked on the agent's own information) |
|---|---|---|---|
| 0–3 | UP, DOWN, LEFT, RIGHT | 1 (2 if entering a hazard) | the target cell is in the grid, not a wall, and affordable |
| 4 | SEARCH | 2 | affordable |
| 5 | RESCUE | 3 | the agent's own cell holds a victim it sees as unrescued; affordable |
| 6 | ASSIST | 2 | the own cell holds an unrescued **heavy** victim **and a teammate is on the same cell**; affordable |
| 7 | WAIT | 0 | always valid |

Source: `config/default.yaml` costs; `observation.compute_mask`.

**Why WAIT is free.** The code refuses any configuration where WAIT has a cost (`CostModel.validate`). If WAIT cost something, an agent with zero budget would have no legal action at all.

**Why ASSIST is cheaper than RESCUE.** The assister is a helper; the design spec §1.2 gives this reason. The asymmetry also means a heavy rescue costs the team 3 + 2 = 5 units, against 3 for a light one.

## B.4 Observations: what an agent sees

An agent does not see the full state. Its policy input is a **5-number summary** (`observation.features`):

| Feature | What it encodes | Number of values |
|---|---|---|
| f1 | The nearest victim the agent *believes* is still waiting, from its own memory: none, "light here", "heavy here", or the first step (UP/DOWN/LEFT/RIGHT) of the cheapest path to it × near (≤ 3 steps) / far | 3 + 4×2 = **11** |
| f2 | First step towards the cheapest-to-reach cell the agent has **never observed**, or none | 1 + 4 = **5** |
| f3 | The nearest teammate within 3 cells (Chebyshev): none, same cell, or its dominant direction | 1 + 1 + 4 = **6** |
| f4 | The agent's own budget bucket | **4** |
| f5 | Which third of the horizon we are in | **3** |

Total: 11 × 5 × 6 × 4 × 3 = **3,960** possible observations (`N_OBS`). Each 5-tuple is converted to one row number by mixed-radix encoding (`observation.encode`):

> o = (((f1·5 + f2)·6 + f3)·4 + f4)·3 + f5

**The budget buckets (f4)** use thresholds that depend on B_ref, not on the agent's own starting budget (`budget_thresholds`):
- τ1 = c_R = 3;
- τ2 = max(τ1+1, ⌈B_ref/4⌉) = 16;
- τ3 = max(τ2+1, ⌈B_ref/2⌉) = 32.

So the buckets are [0,3), [3,16), [16,32) and [32,∞). Bucket 0 means exactly "I cannot pay for a RESCUE". Because the thresholds are fixed, the same bucket means the same absolute amount at every scarcity level. This is what makes the transfer experiment (Part E.6) meaningful.

**Memory and stale information.** Each agent remembers victims it has seen (`env.known[i]`). Its memory of cells it can currently see is overwritten with the truth every step (`env._observe`). Memory of other cells can be **stale**: a teammate may already have rescued that victim. Stale memory can only misdirect *walking*. It cannot trick an agent into an illegal RESCUE, because the agent's own cell is always within its view and therefore always up to date.

**Information discipline.** The policy input and the action mask are built **only** from `env.view(i)`, an `AgentView` object containing the agent's own memory (a copy), its read-only observed-cells mask, nearby teammates, its own budget and the time. Nothing in `observation.py` can access the hidden ground truth. If any policy submits an action outside its mask, `env.step` raises `InvalidActionError`.

## B.5 Rewards

Every step, agent i receives (`rewards.combine`):

> **R_i = λ_I · r_ind,i + λ_T · r_team − λ_C · cost_i**, with λ_I = 1, λ_T = 1, λ_C = 0.02.

| Component | Paid for | Value |
|---|---|---|
| r_ind (individual) | first discovery of a victim by the team | 0.1, split among agents that see it first in the same step |
| | a light rescue | 1.0 to the rescuer (split if several RESCUE together) |
| | a heavy rescue | 0.5 to the rescuer + 0.5 to the assister |
| r_team (team) | every rescue by anyone | 1.0 to **every** agent |
| cost | units spent this step | −0.02 per unit |

**The design intent** (spec §1.6, D8):
- **A heavy rescue pays each participant only 0.5 individually; a light rescue pays its rescuer 1.0.** So a purely selfish agent should prefer light victims. This creates a possible individual-versus-collective tension.
- **The team term makes every rescue worth 1.0 to every agent.** This pulls the other way.
- **The cost weight is small.** Spending the whole Abundant budget (64 units) costs 64 × 0.02 = 1.28 reward, about one rescue's worth. So costs nudge behaviour but do not dominate it. **[Interpretation]** This is why budget limits act mostly through *feasibility* (what you can still afford) rather than through the reward signal.

**Worked example from a real replay.** `results/replays/phase1_scripted_heavy_assist.txt` shows a scripted heavy rescue at t = 5. Agent 1 plays RESCUE, agent 2 plays ASSIST, and agent 3 is WAITing elsewhere:
- **Rescuer:** 0.5 (heavy rescuer) + 1.0 (team) − 0.02 × 3 = **1.44**.
- **Assister:** 0.5 + 1.0 − 0.02 × 2 = **1.46**.
- **Idle agent:** 0 + 1.0 − 0 = **1.00**. It gets team credit for doing nothing.

That last line is exactly why credit assignment is hard: the team reward does not tell an agent whether *its* action helped.

## B.6 Scarcity levels and budgets

| | Abundant | Moderate | Scarce | Critical |
|---|---|---|---|---|
| ρ | 1.0 | 0.5 | 0.3 | 0.2 |
| B₀ per agent | 64 | 32 | 19 | 13 |
| Horizon H | 105 | 105 | 105 | 105 |

Only the budget changes between levels. The maps, horizon, rewards and seeds are identical. That is what makes "scarcity" a clean experimental manipulation.

**A feel for Critical.** At Critical (13 units), an agent that walks 5 cells out (5 units) and SEARCHes once (2) has 6 left. That is enough for one RESCUE (3) and a little walking. A heavy rescue needs *two* such agents to be in the same place at the same time.

## B.7 Episode structure and one step of the game

An **episode** is one mission on one map. At `reset`, all agents stand on the base with budget B₀, observe their surroundings, and the clock is t = 0.

Each call to `env.step(actions)` is one **simultaneous** step. In order (`env.step`):

1. **Check the actions.** Every submitted action must be in the mask issued at the previous observation; otherwise `InvalidActionError`.
2. **Pay.** Each agent's budget is reduced by the cost of its action. (Pooled mode: payment goes in rotating priority order, and an unaffordable action becomes WAIT.)
3. **Move.** Moving agents change cell. Several agents may share a cell.
4. **Resolve rescues, cell by cell.**
   - Light victim: rescued if ≥ 1 agent plays RESCUE there. If several do, the credit is split and the extras count as a *duplicate rescue* (wasted).
   - Heavy victim: rescued only if ≥ 1 RESCUE **and** ≥ 1 ASSIST are played there by different agents. A lone RESCUE or a lone ASSIST *fails*, and the units are still spent.
5. **Sense.** Each agent observes cells within radius 1 of its new position; after a SEARCH, it also observes radius 2. Memory is overwritten with the truth for those cells. First sightings by the team earn the discovery reward.
6. **Reward.** R_i = λ_I r_ind + λ_T r_team − λ_C cost_i.
7. **Advance time, update dormancy, check termination.**

**Termination** is checked in this order (`env._check_termination`):
1. **all_rescued**: every victim rescued.
2. **exhausted**: max over agents of budget < c_R = 3. No agent can pay for a RESCUE, so no further rescue is possible and the result is fixed.
3. **horizon**: t = H = 105.

**Dormancy.** An agent with budget < c_min = 1 can only WAIT. The learner makes **no Q-update** for an agent that was dormant at the start of a step (`train.train_episode`), because it had no choice to learn from.

## B.8 One complete episode, step by step

We use the scripted replay `results/replays/phase1_scripted_heavy_assist.txt`. It is a hand-written 5 × 5 test map with one heavy victim (h) and one light victim (l), budgets 40 and H = 30. It was written to test the rules, so the moves were chosen by a script, not learned.

```
t=0  budgets [40,40,40]     all three agents on the base (bottom-left, shown *)
     A1=UP  A2=RIGHT  A3=WAIT            rewards -0.02  -0.02  0.00
t=1  A1=UP  A2=RIGHT  A3=WAIT            (moves cost 1 unit = -0.02 reward)
t=2  A1=RIGHT  A2=UP  A3=WAIT            rewards +0.03 +0.03 0.00
     event: first_sighting of heavy victim 0 by agents 0 and 1
     (discovery 0.1 split two ways = 0.05, minus 0.02 for the move = +0.03)
t=3  A1=RIGHT  A2=WAIT  A3=WAIT          agent 1 reaches the heavy victim's cell
t=4  A1=RESCUE  A2=UP  A3=WAIT           event: failed_rescue (no ASSIST that step)
     rewards -0.06 (3 units wasted)  -0.02  0.00
t=5  A1=RESCUE  A2=ASSIST  A3=WAIT       event: rescue, heavy=True, rescuers=[0], assisters=[1]
     rewards +1.44  +1.46  +1.00
```

What to notice:
- At t = 4, agent 2 was not yet on the cell, so ASSIST was not even in its mask; it needs a teammate on the cell. Agent 1's RESCUE failed and its 3 units were wasted. **This is exactly the coordination failure that scarcity punishes**: at Critical, losing 3 of 13 units is very costly.
- At t = 5, both act in the same step and the rescue succeeds.
- Agent 3 received the team reward of +1.0 without contributing.

A real learned episode at Abundant is in `results/replays/phase6_heavy_assist.txt` (seed 4, test instance 4000000: 5 of 6 rescued, ending at the horizon).

## B.9 How agents interact

Agents interact only through the world:
- **Sharing cells.** This is required for heavy rescues.
- **Changing what others will find.** If I rescue a victim, it is gone for you, and your memory of it becomes stale.
- **Seeing each other.** Feature f3, within 3 cells.
- **Splitting credit.** Simultaneous co-actions split the individual reward.

There is no messaging. In the main setting each agent's budget is private.

**Pooled ablation** (`budget_mode = "pooled"`):
- The team shares one pool of 3 × B₀.
- Payments are made in rotating priority order (agent t mod 3 pays first), so no agent is always favoured. An agent whose action can no longer be paid is "preempted" and WAITs.
- Feature f4 shows the *per-capita* share floor(pool/3), so the observation space is identical. The mask uses the real pool (clarification P4).

## B.10 How cooperation is measured

All metrics are computed from the per-step **action log** (`EpisodeLog`), never from rewards (`cooperation_metrics.py`). A **"minimal requirement" rule** (deviation P6) applies throughout: each rescue has exactly one *effective* RESCUE and, for a heavy victim, one effective ASSIST. Extras are wasted co-actions. When several agents share a role, the lowest index counts as the canonical one.

| ID | Name | Formula | Cooperative direction |
|---|---|---|---|
| C1 | Effective assist rate **EAR** | heavy rescues ÷ ASSIST actions taken | higher |
| C2 | Redundant search **RSR** | SEARCHes whose radius-2 footprint was already ≥ 50% covered by earlier searches ÷ all SEARCHes. **RSR_other** counts only coverage by *other* agents (including same-step searches of lower-index agents). | lower |
| C3 | Territory division **TDI** | 1 − average pairwise Jaccard overlap of the sets of cells each agent visited (base excluded) | higher |
| C4a | Productive spend share **PSS** | (3 per rescue + 2 per heavy rescue) ÷ total units spent | higher, but it **tracks reward** |
| C4b | Consumption **Gini** | Gini of units spent by each agent: G = ΣΣ\|x_i − x_j\| / (2n² mean x) | lower = more balanced |
| C5 | Cooperation rate **CR** | cooperative non-WAIT actions ÷ all non-WAIT actions | higher |

**What counts as "cooperative" in CR** (`cooperation_rate`). For each heavy rescue at time t* on cell c:
- the canonical RESCUE and the canonical ASSIST; plus
- every *move* by those two agents in the 2L = 20 steps before t* that reduced their cheapest-path cost to c.

Light rescues never count. So CR is **0 by construction** in a world with no heavy victims.

**Exp4 event counts:**
- **E1 abandonment:** a failed RESCUE or ASSIST while another agent stood on the same cell.
- **E2 duplicate light rescues.**
- **E3 conflict episodes:** episodes where the best individual return is above its median while the collective return is below its median.

**Pooling over episodes.** For ratio metrics, each seed's value is Σ numerators ÷ Σ denominators over its 100 test episodes (`train.summarize_eval`), not an average of per-episode ratios. Pooling avoids giving huge weight to episodes with tiny denominators.

**Validity check (before any learning).** The metrics were validated on scripted episodes with known answers and on the baselines: 42 of 45 checks passed (`results/phase2/metric_validation_summary.md`). The three failures all concern PSS, which turned out to be almost a monotone function of collective return (Spearman 0.95–1.00). The group therefore decided (D22) to keep PSS in H2 because it was preregistered, but **never to use it as independent evidence of cooperation**.

---

# PART C — AI and reinforcement-learning concepts used in the project

Only concepts that the project actually uses are covered. Each follows the same pattern:
1. simple idea;
2. example;
3. maths;
4. why we need it;
5. where it is in the code;
6. how it shows up in our results.

## C.1 Reinforcement learning (RL)

1. **Simple idea.** An agent learns by trial and error. It acts, the world responds with a new situation and a number called the **reward**, and over many tries the agent learns which actions lead to more total reward.
2. **Example.** At first our agents wander randomly. Occasionally a random sequence of moves ends with a RESCUE on a victim, which pays +1 or more. Over thousands of episodes, the actions that led there become preferred.
3. **Maths.** At each step t the agent sees an observation o_t, chooses an action a_t, and receives reward r_t. Its goal is to maximise the **discounted return**

   > G_t = r_t + γ r_{t+1} + γ² r_{t+2} + … , with 0 ≤ γ < 1.
4. **Why we need it.** Hand-coding team behaviour for every map and budget is hard; that is what the cooperative baseline does. RL lets the agents *discover* behaviour, which is what our research question asks about: can independent learners *learn* cooperation under scarcity?
5. **Code.** The learning loop is `train.train_episode`; the agent is `iql.IQLTeam`.
6. **Effect on results.** Learning is noisy and slow. After 8,000 episodes, policies are still changing (Part F.10).

## C.2 Markov decision process (MDP) and its multi-agent, partially observed version

1. **Simple idea.** An MDP is the formal description of an RL problem: states, actions, how actions change states (transitions), and rewards. "Markov" means the next state depends only on the current state and action, not on the whole history.
2. **Our case.** We have **three** agents acting at once: a *Markov game* (also called a stochastic game). Each agent sees only part of the state: *partially observable*.
3. **Maths.** From the report §3.1: G = ⟨N, S, {Aⁱ}, {Oⁱ}, T, {Rⁱ}, H, B₀⟩ with
   - N = 3 agents;
   - S = states;
   - Aⁱ = the 8 actions;
   - Oⁱ = observations;
   - T = transition rule (deterministic given the joint action);
   - Rⁱ = each agent's reward;
   - H = horizon;
   - B₀ = initial budget.
4. **Why we need it.** It tells us exactly what the agent can and cannot know, and what "the environment" includes.
5. **Code.** `env.py` *is* T and Rⁱ; `observation.py` is Oⁱ; `costs.py` is Aⁱ and the costs.
6. **Effect.** Because each agent sees only a 5-number summary, two different true situations can look identical to it. **[Interpretation]** This limits how well any tabular learner can do and is one reason IQL stays below the cooperative baseline.

## C.3 Policy

1. **Simple idea.** A policy is the agent's rule for choosing an action in each situation.
2. **Example.** The greedy baseline's policy is: "if a light victim is here, RESCUE; else walk to the nearest affordable victim; else explore".
3. **Maths.** A deterministic policy π maps observations to actions: a = π(o). An IQL agent's **greedy policy** is π(o) = argmax over valid a of Q(o, a).
4. **Why.** What we evaluate on the test maps is a policy.
5. **Code.** Learned: `IQLTeam.act` with ε = 0. Baselines: `GreedyController.act`, `CooperativeController.act`, `RandomController.act`.
6. **Effect.** All test results use the **greedy** (ε = 0) learned policy, never the exploring one.

## C.4 State-action values (Q-values) and Q-learning

1. **Simple idea.** Q(o, a) is the agent's estimate of "how much total future reward I will get if I take action a now, in situation o, and act well afterwards". If Q is right, acting well is easy: pick the action with the largest Q.
2. **Example.** Suppose f1 says "heavy victim here" and f3 says "teammate on my cell". If the agent has often been rewarded for playing RESCUE in exactly this observation, then Q(o, RESCUE) grows larger than Q(o, WAIT).
3. **Maths: the Q-learning update.** After each step, with α the learning rate and γ the discount:

   > Q(o,a) ← Q(o,a) + α · [ r + γ · max_{a′ valid in o′} Q(o′,a′) − Q(o,a) ]

   The bracket is the **temporal-difference (TD) error**: the difference between what happened (the reward, plus the estimated value of where we landed) and what we expected. If the episode has ended (`done`), the target is just r.

   **Our values:** α = 0.1, γ = 0.98, and every Q starts at 0.
4. **Why.** It is the simplest learning method that needs no model of the environment, and it is tabular, so it needs no neural network. The master prompt forbade deep-learning frameworks.
5. **Code** (`iql.IQLTeam.update`):
   ```python
   target = r if done else r + self.p.gamma * masked_max(self.Q[i, o2], mask2)
   td = target - self.Q[i, o, a]
   self.Q[i, o, a] += self.p.alpha * td
   ```
   - **The max is taken only over valid next actions** (`mask2`). The agent knows its own next mask, so this uses no hidden information.
   - **Every termination counts as done.** That includes all rescued, exhausted, and **horizon**. Treating the horizon as terminal is a design simplification; it is consistent with the time feature f5.
6. **Effect.** With 3 agents × 3,960 observations × 8 actions = 95,040 table entries per run, and around 0.25 to 0.7 million environment steps per run, many entries are visited rarely. **[Interpretation]** This is part of why learning has not converged.

## C.5 Discount factor γ

1. **Simple idea.** γ says how much the agent cares about future rewards compared with immediate ones.
2. **Example.** With γ = 0.98, a reward 10 steps away counts 0.98¹⁰ ≈ 0.82 as much as one now. A reward 50 steps away counts ≈ 0.36.
3. **Maths.** It appears in G_t and in the Q-update target.
4. **Why.** Without discounting, an agent might not care whether it rescues someone now or at step 100. γ close to 1 makes long walks to victims worthwhile.
5. **Code.** `IQLParams.gamma = 0.98`.
6. **Effect.** It was frozen before the experiments and never tuned.

## C.6 Multi-agent RL and *independent* Q-learning (IQL); non-stationarity

1. **Simple idea.** In **independent** Q-learning, each agent runs its own Q-learning. It treats the other agents as just "part of the environment" and learns only from its own reward.
2. **Example.** Agent 0 learns "RESCUE when on a heavy victim with a teammate present". Whether that works depends on whether the teammate plays ASSIST, and the teammate is *also still learning*. Last week the teammate always assisted; this week it has started walking away. Agent 0's old lesson becomes wrong.
3. **Maths.** For a single agent in a **stationary** environment (the rules never change), tabular Q-learning converges to the optimal values under standard conditions (Watkins & Dayan, report ref [8]). In IQL, agent i's transition probabilities depend on the others' policies π_{−i}, which change during training. The environment is **non-stationary** from agent i's view, and the convergence guarantee no longer applies (report §2.3).
4. **Why we chose it.** The research question is explicitly about *independently learning* agents. IQL is the simplest such method, named in the proposal.
5. **Code.** `IQLTeam` holds one Q-table per agent (`self.Q[i]`) and one exploration random-number stream per agent slot. Nothing corrects for non-stationarity; the docstring says *"measuring its consequences is the point"*.
6. **Effect.** We **measured** non-stationarity rather than assuming convergence (A5, Part F.10):
   - **Policy churn:** the share of observations whose greedy action changed in the last 500 episodes.
   - **TD error:** whether it is shrinking.
   - **A stability criterion:** churn < 5% *and* validation rescue-fraction range < 0.02 over the last three checkpoints.

   Only 5 of 350 runs are stable, and none of the 40 main runs.

## C.7 Exploration versus exploitation; ε-greedy

1. **Simple idea.** **Exploitation** means doing what currently looks best. **Exploration** means trying something else in case it is better. Too little exploration and the agent never discovers rescues; too much and it never uses what it learned.
2. **Example.** Early on, every Q is 0, so "best" is meaningless. The agent must try random actions to discover that RESCUE on a victim pays.
3. **Maths: ε-greedy.** With probability ε, pick a uniformly random *valid* action; otherwise pick argmax Q (ties broken randomly). ε decreases **linearly** from 1.0 to 0.05 over the first 70% of the episodes (5,600 of 8,000), then stays at 0.05:

   > ε(e) = 1.0 + (0.05 − 1.0) · e / 5,600 for e < 5,600; afterwards 0.05.
4. **Why.** It is standard, simple and preregistered.
5. **Code.** `IQLParams.epsilon`, `IQLTeam.act`, `masked_argmax`. In A6, the decay is measured in *environment steps* instead (`epsilon_by_steps`).
6. **Effect.**
   - Learning curves (report Fig. 1) rise mostly while ε falls.
   - During training, the 5% residual exploration keeps adding randomness.
   - **The quick run at 1,500 episodes** gave greedy RF ≈ 0.04. The full runs' own checkpoint at 1,500 episodes is similar, because ε is still high there (decision D29).

## C.8 Action masking

1. **Simple idea.** Do not let an agent pick illegal actions, such as RESCUE where there is no victim or a move into a wall.
2. **Example.** At t = 4 of the replay in B.8, agent 2 had no ASSIST in its mask because no teammate was on its cell.
3. **Maths.** M(o) is the set of valid actions. The argmax, the random choice and the max in the TD target are all taken over M.
4. **Why not penalise illegal actions instead?** Penalties would make learners waste thousands of episodes learning the rules, and every baseline would need the same penalties. Masks define feasibility once, identically for every policy (D3).
5. **Code.** `observation.compute_mask`; validated in `env.step`.
6. **Effect.** No policy, learned or hand-written, ever plays an illegal action. Comparisons between policies are fair at this level.

## C.9 Training versus evaluation

1. **Simple idea.** **Training** is where the agent learns: it explores, and Q-values change. **Evaluation** is where we freeze the Q-tables, set ε = 0 and measure performance on maps never used for training.
2. **Example.** A student practises on homework (training), checks progress on a mock test (validation), and is graded on the final exam (test).
3. **Our three data sets.** These are disjoint lists of map seeds, frozen with hashes in `results/calibration/instance_sets.json`:

   | Set | Size | Used for |
   |---|---|---|
   | training pool | 1,000 maps | learning; each run visits them in a seed-specific shuffled order, 8 passes |
   | validation | 50 maps | checkpoints every 500 episodes (learning curves, churn, best-validation checkpoint); the pilot |
   | test | 100 maps | the final numbers in the report, used only once training is finished |
   | shifted test | 100 maps (walls 0.25, victim density 0.09) | generalisation (Exp5) |
   | calibration | 200 maps | Phase 3 calibration only |

4. **Why.** Measuring on training maps would reward memorising those maps.
5. **Code.** `train.train_run` uses only the training and validation pools; `train.py` states that test instances are never touched. Test evaluation happens in `scripts/run_experiments.py eval`, through `experiments.evaluate_actors`.
6. **Effect.** All reported numbers come from the 100 test maps. The "best-validation checkpoint" is selected on validation, never on test.

## C.10 Random seeds and common random numbers (CRN)

1. **Simple idea.** A **seed** is the starting number of a pseudo-random generator. The same seed gives exactly the same "random" sequence, so the run can be reproduced.
2. **Two different kinds of seed in our project:**
   - **Instance seeds** generate maps (`utils.instance_seed`).
   - **Training seeds 0–9** decide everything random in learning: the order of training maps and each agent's exploration stream.

   A training seed is one independent repetition of the whole learning process.
3. **Common random numbers.**
   - Seed s uses the **same** map order and the **same** exploration stream in *every* condition (Abundant, Critical, pooled, and so on).
   - At evaluation, tie-breaks among equal Q-values come from a generator seeded by (map seed, agent), identical for every method (`iql.eval_rngs`).

   Differences between conditions therefore come from the manipulation, not from luck in random streams.
4. **Why.** Pairing by seed removes noise, so the paired tests (Part C.13) are much more powerful.
5. **Code.** `IQLTeam.__init__` (`SeedSequence([seed, k, 0xE7])`), `train.EpisodeOrder` (`SeedSequence([seed, 0x0D])`), `iql.eval_rngs` (`SeedSequence([instance_seed, i, 0xC2])`).
6. **Effect.** It makes "the same seed ranks the four levels the same way in all 10 cases" (Kendall's W = 1) a meaningful statement.

## C.11 Baselines and the oracle reference

1. **Simple idea.** A baseline is a comparison point. Without one, "RF = 0.573" means nothing.
2. **Our baselines** (`baselines.py`, all decentralised, all bound by the same masks):
   - **Random:** a uniformly random valid action. It is the lower anchor.
   - **Greedy:**
     - chases the nearest affordable victim it believes is waiting, preferring light victims at equal cost;
     - RESCUEs it; tries each heavy victim at most once; **never ASSISTs**;
     - otherwise explores: SEARCH if ≥ 50% of the search footprint is unseen, else walk to the nearest unseen cell.

     Its three agents run identical deterministic rules from the same base, so they tend to **move in lockstep**.
   - **Cooperative:** a hand-designed policy with seven priority rules (the `CooperativeController` docstring):
     - **(1)** on a heavy victim with a teammate present, the lowest index RESCUEs and the others ASSIST;
     - **(2)** RESCUE a light victim;
     - **(3)** wait up to 2L = 20 steps at a heavy victim for help;
     - **(4)** walk to a teammate seen standing still for 3 views (a "help signal");
     - **(5)–(6)** go to the nearest affordable light, then heavy, victim;
     - **(7)** explore your own map sector (sectors from a deterministic k-means), and don't SEARCH if a lower-index teammate is on your cell.
3. **Oracle reference** (`oracle.py`):
   - It sees **everything** and plans centrally: it repeatedly appends the cheapest feasible next rescue (pairing two agents for heavy victims), then executes the plan in the real environment.
   - It is **not a learner and not proven optimal.** On tiny maps it matched the exhaustive optimum in 297 of 300 cases.
   - It is always labelled "oracle reference (full information, not a learner)" and never tested statistically.
4. **Why.**
   - Random and greedy show whether IQL learned anything beyond trivial behaviour.
   - Cooperative shows what coordination can achieve with the same information.
   - The oracle shows how much of a level's difficulty is the budget itself rather than imperfect information.
5. **Code.** `make_team(name)`, `OraclePolicy`, `evaluate.run_episode`.
6. **Effect.** See Part F.3. **Important nuance (§0 item 0.3):** the baselines see the full `AgentView`, while IQL sees only its 5-feature summary.

## C.12 Distribution shift

1. **Simple idea.** A model trained on one kind of situation is tested on a different kind. Performance can drop because the situations differ, not because the model is "worse".
2. **Three places in our project:**
   - **Shifted test maps:** more walls (0.25) and more victims (density 0.09).
   - **Transfer:** a policy trained at one budget level is tested at another.
   - **A4 solo agents:** during training they **never saw a teammate**, so feature f3 was always "none". At test time they meet teammates, and observations with f3 ≠ none are rows of the Q-table that were never updated (still 0).
3. **Maths.** The training distribution of observations differs from the test distribution. Unvisited Q-rows default to 0, and argmax ties among zeros are broken randomly.
4. **Why it matters.** It is a **confound** for A4: the joint-vs-solo gap mixes "learned to coordinate" with "never saw these observations".
5. **Code.** Shifted maps: `instance_sets.json` "shifted_test" with config overrides. Solo training: `RunSpec(n_agents=1, agent_ids=[k])`.
6. **Effect.** Shifted maps lower RF but keep the scarcity ordering. Transfer shows strong specialisation (Part F.9).

## C.13 Statistics: comparisons and uncertainty

**Unit of analysis = training seed.** Each seed gives *one* number per condition: its mean over the 100 test maps. The 100 test episodes are repeated measurements of the *same* trained team. Counting them as 100 independent data points would be **pseudo-replication**: it inflates certainty falsely. So n = 10 per condition.

**Paired versus unpaired.** Because of CRN, seed s at Abundant and seed s at Critical are a *pair*. A paired test looks at within-seed differences, which removes between-seed noise.

**The tests** (`stats.py`), with the reason for each:

| Test | Question it answers | Used for |
|---|---|---|
| **Friedman** test [11] | Do ≥ 3 paired conditions differ? (rank-based; no normality assumption) | H1, H2 across the 4 levels |
| **Kendall's W** | How consistently do seeds rank the conditions? (0 = no agreement, 1 = every seed ranks them identically) | effect size for Friedman: W = χ² / (n(k−1)) |
| **Page's L** [12] | Is there an *ordered* trend (monotone up or down)? Tested both ways; two-sided p = min(1, 2·min(p_dec, p_inc)) | H1, H2, robustness |
| **Wilcoxon signed-rank** [13] | Do two paired conditions differ? Or does a set of values differ from a constant? | pairwise levels; H3–H6 |
| **Rank-biserial r** | Effect size for Wilcoxon (−1 to 1) | all Wilcoxon tests |
| **δ₁** = (seeds above − seeds below)/n | Simple effect size vs a constant | H0, H3 |
| **Holm correction** [10] | Controls the chance of *any* false positive within a family of tests | each preregistered family |
| **Percentile bootstrap CI** [14] | Uncertainty of a mean without distributional assumptions: resample the 10 seeds with replacement 10,000 times | all CIs |

**How the Wilcoxon test works, in one paragraph.**
1. Take the 10 differences and drop exact zeros (`zero_method="wilcox"`). Differences below 10⁻⁹ are snapped to zero first (deviation C6).
2. Rank their absolute sizes.
3. Add up the ranks of the positive differences (W⁺) and of the negative ones (W⁻).
4. If all 10 differences are positive, W⁺ is as large as possible. The chance of that under "no difference" is (1/2)¹⁰ = 1/1024 ≈ 0.00098 one-sided, or 2/1024 ≈ 0.00195 two-sided.

**Holm, step by step.**
1. Sort the m p-values from smallest to largest.
2. Multiply the smallest by m, the next by m−1, and so on.
3. Keep each result at least as large as the previous one.

This is why so many of our adjusted p-values are 0.00195 × 6 = **0.0117** (6 pairwise level contrasts), 0.00195 × 12 = **0.0234** (12 baseline tests) or 0.00195 × 4 = **0.0078** (4 levels).

**Why these tests and not t-tests or ANOVA.**
- With only 10 seeds, normality cannot be checked.
- Rescue fractions are bounded between 0 and 1 and near the floor at Critical.
- Rank tests are robust to all of this.

**The cost:** with n = 10, small effects are hard to detect. A non-significant result is **inconclusive**, not proof of no effect.

**One-sample tests against baselines (H3, H0).** Greedy, cooperative and the oracle are **deterministic**: they produce one number per level, with no seed variation. So IQL's 10 seed values are compared with that single constant.

**Code.** `stats.friedman`, `stats.page_two_sided`, `stats.wilcoxon_test`, `stats.one_sample_vs_constant`, `stats.holm`, `stats.bootstrap_ci`, `stats.paired_bootstrap_ci`. Each bootstrap is seeded from the CRC32 hash of a text label, so every interval is reproducible.

## C.14 Calibration

1. **Simple idea.** Choose the reference budget and horizon by *measuring* the task, so that "ρ = 0.5" means "half of what this task needs" rather than an arbitrary number.
2. **Example.** 30 units is generous on a 6 × 6 map and hopeless on a 20 × 20 map.
3. **Maths.**
   - **H = ⌈T₉₀/0.7⌉.** T₉₀ is the 90th percentile of the step at which the cooperative baseline has rescued 90% of victims, with unlimited budget. The main configuration gives T₉₀ = 73, so H = 105.
   - **B_ref = the 90th percentile** of per-agent consumption by the cooperative baseline, with unlimited budget and the H just fixed. Main configuration: 64.
   - **The ρ levels** are chosen so that the cooperative baseline reaches about 1.0 / 0.70 / 0.40 / 0.10–0.15 RF, under a feasibility rule: at Critical, at least one victim must be rescuable in ≥ 95% of instances.
4. **Why.** It answers review point R3. It also makes it possible to check whether ρ means the same on other map sizes.
5. **Code.** `calibration.py`, `scripts/run_calibration.py`; rules hashed in advance in `config/calibration.yaml`.
6. **Effect.** See Part E.3 and F.11. Critical had to be 0.2 rather than 0.1, and ρ is comparable on maps with L ≥ 10 but not on 8 × 8 maps.

---

# PART D — The codebase, module by module

## D.1 Architecture at a glance

```
config/default.yaml ──► utils.load_config ─────────────────────────────────────────────────────────┐
config/calibrated.yaml (H, B_ref, b0 per level)                                                    │
                                                                                                    ▼
mapgen.generate_instance(seed) ─► Instance ─► mapgen.compute_statics ─► MapStatics (paths, views)
                                                     │
costs.CostModel ─────────────────────────────────────┤
rewards.RewardModel ─────────────────────────────────┤
observation (AgentView, features, encode, mask) ─────┤
                                                     ▼
                                          env.RescueEnv  (reset / step / EpisodeLog)
                     ┌───────────────────────────────┼─────────────────────────────┐
                     ▼                               ▼                             ▼
          iql.IQLTeam (learner)          baselines (random/greedy/coop)     oracle.OraclePolicy
                     │                               │                             │
          train.train_run (train + validation checkpoints)                         │
                     │                               │                             │
          experiments.py (blocks, settings, evaluate_actors) ◄──────────────────────┘
                     │
   scripts/run_experiments.py train|eval  ─► results/runs/, results/eval/
                     │
   metrics.episode_record + cooperation_metrics  (per-episode rows)
                     │
   scripts/run_stats.py (stats.py) ─► results/stats/ ─► make_tables / make_figures
                     │
   build_report_content.py + render_report.js ─► report/ ;  verify_results.py checks everything
```

## D.2 `utils.py`: shared helpers
- `load_config` reads `config/default.yaml` (and applies overrides).
- `instance_seed(split, index, attempt)` = SEED_BASE[split] + 100·index + attempt. Each data split has its own disjoint seed range. If a map is rejected (e.g. infeasible at Critical), the next attempt number is used.
- `initial_budget(ρ, B_ref)` uses **round-half-up**. Python's `round()` rounds 2.5 to 2 ("banker's rounding"), which would make budgets depend on an obscure rounding rule.
- `make_rng`, `chebyshev`, `sha256_bytes`.

## D.3 `costs.py`: actions and costs
- `Action` enum (UP = 0 … WAIT = 7) and `CostModel` (move 1, hazard 2, SEARCH 2, RESCUE 3, ASSIST 2, WAIT 0).
- `validate()` enforces three assumptions: WAIT is free, every other action costs ≥ 1, and hazards cost at least as much as normal moves.
- `c_min` (= 1) defines dormancy.
- `action_cost(a, entry_cost)` charges a move according to the cell being *entered*.

## D.4 `mapgen.py`: maps, paths, feasibility
- `generate_instance(cfg, seed)` is described in B.2. It returns an `Instance` (grid, base, victim cells, heavy flags, seed, metadata).
- `instance_from_ascii` builds hand-drawn maps for tests and scripted replays.
- `compute_statics(inst, costs, radii)` precomputes, once per map:
  - `dist[a, b]`: cheapest path cost from every cell to every cell (all-pairs);
  - `steps[a, b]`: number of steps on that path;
  - `first_move[a, b]`: the first action on that path, with deterministic tie-breaking;
  - `move_target` and `entry_cost` tables;
  - `views[r][cell]`: the cells visible within radius r.

  Everything later (features, masks, baselines, oracle, metrics) reads these tables instead of searching paths again. This is a big speed-up.
- `feasible_victims` / `is_feasible`: an exact check that at least one victim can be rescued from the base within budget and horizon. A heavy victim needs two agents who can both reach it and pay.

## D.5 `observation.py`: what agents may use
- `AgentView`: the *only* bridge from the true state to any policy. It has two separate budget fields (P4): `spendable` (used by the mask) and `budget_feature_value` (used by f4).
- `budget_thresholds`, `budget_bucket`, `time_bucket` are written in integer arithmetic so boundaries are exact.
- `features` computes f1–f5 (B.4); `encode` / `decode` convert to and from a row index.
- `compute_mask` gives the valid actions (B.3).

## D.6 `env.py`: the game engine
- `RescueEnv(cfg, horizon, b_ref, budget_mode, n_agents)`.
- `reset(instance, b0)` puts agents on the base, sets budgets, makes the first observations and returns (obs, masks).
- `step(actions)` runs the seven sub-steps of B.7 and returns (obs, masks, rewards, done, info). The `info` dict includes events such as rescue, failed_rescue, first_sighting and stale_correction.
- Internals:
  - `_observe` overwrites memory with the truth for visible cells and logs a `stale_correction` when a remembered victim turns out to be gone;
  - `_update_dormancy`;
  - `_check_termination`;
  - `view(i)` builds the `AgentView`, giving copies so a policy bug cannot corrupt the true state.
- **`EpisodeLog`** records positions, budgets, requested and effective actions, costs, rewards and events at every step. All cooperation metrics are computed from it afterwards.
- The environment owns **no random generator**: given the actions, it is deterministic.

## D.7 `rewards.py`
`RewardModel.from_config` holds every coefficient in one place. `combine` turns the raw components (discovery shares, rescue shares, number rescued, cost paid) into R, r_ind and r_team (B.5).

## D.8 `iql.py`: the learner
- **`IQLParams`:** α 0.1, γ 0.98, ε 1.0 → 0.05 over 70% of 8,000 episodes.
- **`IQLTeam`:**
  - `Q` has shape (n, 3960, 8), initialised to 0, with one random stream per agent slot;
  - `act(obs, masks, ε)` is ε-greedy over valid actions;
  - `update(i, o, a, r, o2, mask2, done)` is the TD(0) update shown in C.4;
  - `greedy_actions` is used only for the churn diagnostic.
- **`masked_argmax`:** the best valid action, with ties broken uniformly at random.
- **`eval_rngs`:** the CRN tie-break streams for evaluation.

## D.9 `train.py`: one training run
- **`InstancePool`:** a list of (instance, statics) pairs for a frozen list of seeds.
- **`RunSpec`:** everything that defines a run (seed, b0, H, B_ref, budget mode, parameters, n_agents for solo runs, step budget for A6).
- **`train_episode`:** play one episode with exploration and update every non-dormant agent after every step:
  ```text
  obs, masks = env.reset(map, b0)
  while not done:
      dormant = env.dormant (before the step)
      acts = team.act(obs, masks, eps)
      obs2, masks2, R, done = env.step(acts)
      for each agent i not dormant: team.update(i, obs[i], acts[i], R[i], obs2[i], masks2[i], done)
      obs, masks = obs2, masks2
  ```
- **`evaluate_team`:** greedy play on a pool with CRN tie-breaks; returns per-episode metric rows and the set of observations visited (for churn).
- **`summarize_eval`:** turns per-episode rows into one **seed-level** value per metric. Means are used for per-episode metrics such as RF; pooled ratios for C1, C2, C4a and C5 and the heavy and light shares.
- **`churn(prev, cur, visited)`:** the share of validation-visited observations whose greedy action changed.
- **`stability`:** stable means last churn < 0.05 **and** validation RF range over the last 3 checkpoints < 0.02.
- **`train_run`:**
  1. Evaluate at episode 0.
  2. Train for 8,000 episodes in the seed's map order, evaluating on validation every 500 episodes (17 checkpoints in total).
  3. Keep the **final** Q-tables (primary analysis) and the **best-on-validation** Q-tables (sensitivity).
  4. Write `train_log.csv`, `checkpoints.csv`, `q_final.npz`, `q_bestval.npz` and `run.json`.

## D.10 `baselines.py`, `oracle.py`, `evaluate.py`
- **`DecentralizedTeam`** gives each agent its own controller, which sees only its own view and mask.
- **`explore`** is shared by greedy and cooperative, so the *only* difference between them is the cooperation rules (D19).
- **`sector_partition`:** a deterministic k-means split of free cells into 3 sectors.
- **Oracle:**
  - `greedy_insertion_plan` → `compile_plan` (turns the plan into per-step actions) → `OraclePolicy.act`;
  - `exhaustive_plan_count` gives the exact optimum on tiny maps;
  - `upper_bound` gives a loose bound (here always 6, so it was not informative).
- **`evaluate.run_episode`** plays one episode for any team policy.

## D.11 `metrics.py` and `cooperation_metrics.py`
- **`episode_record(inst, st, log, costs, r_v, **labels)`** builds one row per episode:
  - RF = rescued/V; ms = 1 if all rescued;
  - heavy and light rescue counts, collective return, termination reason, steps, coverage;
  - all of C1–C5 and E1–E2 with numerators and denominators.
- **`stale_diagnostics`**, **`e3_conflict_flags`** (E3 across a seed's episodes).
- The C1–C5 functions are explained in B.10.

## D.12 `calibration.py` and `experiments.py`
- **`calibration.py`:** config variants for other map sizes and densities, consumption measurement, horizon and B_ref rules, and the ρ sweep.
- **`experiments.py`:**
  - `BLOCKS` (main, p0, p0sec, pooled, alt, solo, eqsteps) and `setting(block, level)`, which returns (H, B_ref, b0);
  - `PoolCache`;
  - actor wrappers: `QActor` (greedy learned agent), `RandomActor`, `WaitActor`, `ControllerActor`;
  - `q_team_factory`, `ablated_factory` (A2), `cooperative_factory`, `evaluate_actors`;
  - `mismatch_permutations` (A1): two rounds of permutations σ2, σ3 such that s, σ2(s) and σ3(s) are all different, from a fixed generator;
  - `run_dir`, `load_q`.

## D.13 `stats.py`
Described in C.13. It also contains:
- `kruskal` and `cliffs_delta` (secondary, unpaired comparisons);
- `ols` and `vif` (A8 regression and collinearity).

## D.14 The scripts and the execution flow

The pipeline runs in this order. It is also listed in `scripts/run_all.py --full --dry-run`.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `pytest` | src, tests | `results/logs/pytest.txt` |
| 2 | `run_calibration.py`, `plot_calibration.py` | config, 200 calibration maps | `config/calibrated.yaml`, `results/calibration/` |
| 3 | `make_instance_sets.py`, `make_freeze_manifest.py` | config | frozen seed lists and hashes |
| 4 | `run_pilot.py`, `analyze_pilot.py` | training + validation maps | `results/pilot/` (gate passed; nothing changed) |
| 5 | `run_experiments.py train --block X` | training + validation | `results/runs/<block>/<level>/seed_s/` (350 runs) |
| 6 | `run_experiments.py eval --kind K` | Q-tables + **test** maps | `results/eval/` (raw per-episode CSVs) |
| 7 | `check_phase5_integrity.py`, `phase5_summary.py`, `make_phase5_manifest.py` | runs, eval | integrity report, hashes |
| 8 | `run_stats.py` | eval CSVs | `results/stats/` (seed-level tables, every test, results.json) |
| 9 | `make_tables.py`, `make_figures.py`, `make_replays.py` | stats | `results/tables/`, `results/figures/`, `results/replays/` |
| 10 | `build_report.sh` | stats, figures | `report/report.docx`, `report.pdf`, `docs/report_numbers.yaml` |
| 11 | `verify_results.py`, `make_manifest.py` | everything | `results/logs/verify_results.txt`, `results/manifest.json` |

**From one command to one number.** Example: the Abundant RF of 0.573.
1. **Train.** `run_experiments.py train --block main` trains 4 levels × 10 seeds. For seed 3 at Abundant, `train_run` writes `results/runs/main/Abundant/seed_3/q_final.npz`.
2. **Evaluate.** `run_experiments.py eval --kind learned` loads each `q_final.npz` and calls `evaluate_actors` on the 100 test maps with ε = 0 and CRN tie-breaks. Each episode becomes a row from `episode_record`; the rows are saved in `results/eval/learned/main__Abundant.csv`.
3. **Summarise.**
   - `run_stats.py` groups the rows by seed → `summarize_eval` → 10 seed values in `results/stats/seed_level_learned.csv`.
   - The mean of those 10 values and its bootstrap CI go to `condition_means.csv`: **0.573 [0.517, 0.627]**.
   - The Friedman test uses the 10 × 4 matrix of seed values → `h1_h2_omnibus.csv`.
4. **Report.** `build_report_content.py` reads 0.573 through `report_lib.Registry.csv(...)` and records its source in `docs/report_numbers.yaml`.
5. **Verify.** `verify_results.py` (check V7) re-reads it, re-formats it and confirms it appears in the Word file.

**The verifier** (`verify_results.py`) has seven groups of checks, 278 checks in total:
- **V1:** seed-level and baseline values recomputed from the raw evaluation CSVs.
- **V2:** every condition mean recomputed.
- **V3:** confirmatory statistics (H0–H6, Friedman, Page, Holm) recomputed independently from the seed-level data.
- **V4:** re-runs `run_stats.py` and requires byte-identical outputs.
- **V5:** 72 claims in `docs/claims.yaml`.
- **V6:** raw evaluation file hashes and training-run completeness.
- **V7:** the 579 report numbers.

**The quick run.** `scripts/run_all.py --quick` runs every stage at reduced scale (3 seeds × 3,000 episodes, 200 / 20 / 30 maps) into `results_quick/` in about 3 minutes. It is a pipeline check; 3 seeds cannot pass the preregistered gate (the smallest possible one-sided p is 1/8 = 0.125).

## D.15 The tests (264)
Each test file targets one guarantee:
- `test_env_rules.py`: rescue rules, simultaneity, credit split, termination order.
- `test_costs_masking.py`: masks, costs, InvalidActionError.
- `test_observation.py`: features, thresholds, encoding.
- `test_stale_information.py`: memory correction.
- `test_feasibility.py`.
- `test_pooled_budget.py`: rotating priority, preemption, the P4 feature.
- `test_invariants_determinism.py`: budget conservation, same seed gives the same episode.
- `test_mapgen.py`.
- `test_metrics.py`: hand-computed metric values on scripted episodes.
- `test_baselines.py`.
- `test_oracle.py`: oracle vs exhaustive optimum.
- `test_calibration.py`, `test_frozen_calibration.py`.
- `test_iql.py`: update formula, masked argmax, ε schedule.
- `test_experiments.py`: blocks, A1 permutations.
- `test_stats.py`: test statistics vs known values.
- `test_run_all_quick.py`.

Mutation checks were also run during development: a rule was deliberately broken to confirm that a test catches it.

---

# PART E — Experimental design

## E.1 The logic in one picture

```
              manipulate ρ (everything else fixed, same seeds)
Abundant ─────────────► Moderate ─────────────► Scarce ─────────────► Critical
   │  Exp1: does rescue performance fall?      (H1)
   │  Exp2: does cooperative behaviour change? (H2)
   │  Exp3: how does IQL compare with baselines? (H3)
   │  Exp4: do individual and collective interests conflict? (E1–E3)
   │  Exp5: does a policy transfer to other levels / shifted maps?
   │
   └─ Attribution: is the fall *because of* cooperation?
        A1 mismatch teammates (H4)     A2 remove a teammate
        A3 world without heavy victims (H5)   A4 train agents alone (H6)
        A5 non-stationarity diagnostics       A6 equal training steps
        A7 the full statistical battery       A8 association regression
```

## E.2 The conditions: training blocks

Every block uses training seeds **0–9**. All blocks except eqsteps use all four ρ levels. Total: **350 runs** (`experiments.BLOCKS`; report Table 7).

| Block | What changes | Runs | Answers |
|---|---|---|---|
| main | nothing (reference) | 40 | Exp1–4, H0–H4, H6, A1, A2, A5, A8 |
| p0 | no heavy victims; same maps, H = 105, B_ref = 64 | 40 | H5 (A3 primary) |
| p0sec | no heavy victims at their own calibration (H = 48, B_ref = 41) | 40 | A3 secondary |
| solo | each agent slot trained alone (n = 1), then deployed as a team | 120 (40 teams × 3 slots) | H6 (A4) |
| eqsteps | Moderate–Critical trained until they used as many steps as Abundant | 30 | A6 |
| pooled | one shared team budget 3·b₀ | 40 | budget-scope robustness |
| alt | 12 × 12 maps, density 0.04, own calibration (H = 150, B_ref = 87) | 40 | configuration robustness |

**Test-time-only conditions** reuse the main agents and need no new training:
- A1 mismatch;
- A2 ablation;
- transfer (train at one level, test at another);
- the shifted test maps.

## E.3 Calibration (review point R3)

Calibration happened **before** freezing the preregistration. It used only the 200 calibration maps, the cooperative baseline and the oracle; no learner was involved (`config/calibration.yaml`, rules hashed in advance).

1. **Horizon.**
   - T₉₀ = 73, the 90th percentile step at which the cooperative baseline reaches 90% rescued.
   - H = ⌈73/0.7⌉ = **105**.
   - The 0.7 factor leaves slack so time is not the binding limit for a good team.
2. **B_ref.** The 90th percentile of per-agent consumption = **64** (mean consumption 44.9).
   - The analytic formula estimates 21.9.
   - It tracks the empirical values across configurations almost perfectly (r = 0.998) but predicts only about half of the mean (ratio 0.49).
   - Reason documented in the report: it ignores detours, waiting for a partner and revisits. The empirical value is used.
3. **ρ sweep.** ρ = 1.0, 0.9, …, 0.1 was swept with the cooperative baseline and the oracle (report Table 5).
   - Targets for the cooperative RF: ≈ 1.0 / 0.70 / 0.40 / 0.10–0.15.
   - Selected levels: **1.0 / 0.5 / 0.3 / 0.2**, giving cooperative RF 0.971 / 0.696 / 0.392 / 0.220.
   - Critical misses its band. ρ = 0.1 is solvable in only 33% of instances, below the pre-stated 95% rule, while ρ = 0.2 is solvable in 99%. The grid was not refined afterwards (note N1).
4. **Sensitivity.** The procedure was repeated for L ∈ {8, 12} × density ∈ {0.04, 0.08}.
   - For L ≥ 10, the cooperative RF curves nearly coincide (spread ≤ 0.079).
   - On 8 × 8 maps they fall faster.
5. **What cooperation costs.** In the all-light world, B_ref = 41 and H = 48 (instead of 64 and 105). Needing two agents for half the victims raises the just-enough budget by about 56%.

## E.4 Training, validation and evaluation episodes

| | Value |
|---|---|
| Training episodes per run | 8,000 (on the 1,000-map training pool, 8 shuffled passes) |
| Validation checkpoints | every 500 episodes on 50 validation maps (17 checkpoints) |
| Policy used for test | **final** Q-tables (primary); best-validation checkpoint (sensitivity) |
| Test evaluation | 100 test maps, greedy (ε = 0), CRN tie-breaks; one episode per map per team |
| Baselines on test | greedy, cooperative and oracle: 100 episodes per level; random: 10 evaluation seeds × 100 maps = 1,000 episodes |
| Pilot (Phase 4) | seeds 1000–1004 (disjoint from 0–9), validation maps only |

**The pilot.** The pilot protocol (hashed before the pilot) allowed only a fixed list of variants, in this order:
- α = 0.2;
- α = 0.05;
- ε decay over 90%;
- 16,000 episodes;
- an observation-bucket change.

The first variant to pass the gate would be adopted. **The frozen defaults (P0) passed immediately:**
- validation RF 0.622 vs random 0.066;
- 5/5 seeds above random, p = 0.031.

So nothing was changed. The episode-count rule (double the episodes if RF still rose by more than 0.02 in the last quarter) did not trigger: the rise was 0.018.

## E.5 Comparisons and statistical families

| Family | Comparison | Test | Correction |
|---|---|---|---|
| H0-gate | IQL vs random at Abundant | one-sided one-sample Wilcoxon; p < 0.05 and δ₁ ≥ 0.33 | none (gate) |
| H1 | RF across 4 levels | Friedman + W; Page two-sided; 6 pairwise Wilcoxon | Holm over 6 pairs |
| H2 | 7 metrics across levels | Friedman per metric (+ Page) | Holm over 7 metrics |
| H3 | IQL vs random/greedy/cooperative × 4 levels | one-sample Wilcoxon | Holm over 12 |
| H4 | original vs mismatched teams per level | paired Wilcoxon | Holm over 4 |
| H5 | DiD = drop(heavy world) − drop(all-light world), Abundant → Critical | Wilcoxon on 10 DiDs + bootstrap CI | single test |
| H6 | joint vs solo teams per level | paired Wilcoxon | Holm over 4 |
| Exploratory | A2, A5, A6, A8, Exp4, Exp5, pooled, alt | as appropriate | **unadjusted**; read descriptively |

**Evidence labels** (report §1.5):
- **CONFIRMATORY:** H0–H6, Holm-corrected; these carry the conclusions.
- **SECONDARY:** preregistered estimates and robustness, e.g. oracle-normalised A3 or the best-validation checkpoint.
- **EXPLORATORY:** preregistered as exploratory.
- **POST HOC:** added after seeing results. This is only the log-scale A3 analysis (C4, C5).

## E.6 Why each experiment exists

- **Exp1 (H1).** The basic scarcity effect on rescues.
- **Exp2 (H2).** Does *behaviour* change, not just outcomes? Seven behavioural metrics.
- **Exp3 (H3).** Is IQL any good? It is placed between random (floor), greedy (uncoordinated) and the cooperative baseline (a hand-designed ceiling with the same information); the oracle is shown for scale.
- **Exp4.** Do selfish incentives fight team incentives? Measured by abandonment (E1), duplicates (E2), conflict episodes (E3), and the correlation between the best agent's return and the team return.
- **Exp5 (generalisation).**
  - *Transfer matrix:* train at level X, test at level Y. Does a policy learn something general about budgets?
  - *Shifted maps:* does it survive denser, more cluttered maps?
- **A1 mismatch (H4).**
  - **Construction:** for seed s, the team is agent slot 0 from seed s, slot 1 from seed σ2(s) and slot 2 from seed σ3(s), with all three seeds different. There are two rounds of fixed permutations.
  - **Logic:** if each seed's agents co-adapted their behaviour to *each other*, strangers should do worse even though every agent individually is equally well trained.
- **A2 ablation.** Replace one slot (each of the 3 slots, averaged) at test time by a random agent or by a WAIT-only agent. How much does the team depend on each member?
- **A3 (H5).**
  - **Construction:** an identical world (same maps, positions, seeds and absolute budgets) in which every victim is light, so cooperation is never necessary.
  - **Logic:** if scarcity hurts *by blocking necessary cooperation*, the heavy world should lose more from Abundant to Critical than the all-light world.
  - **Contrast:** the **difference-in-differences (DiD)**

    > DiD_s = [RF_s(Abundant) − RF_s(Critical)]_heavy world − [RF_s(Abundant) − RF_s(Critical)]_all-light world
- **A4 (H6).** Train each agent slot alone (n = 1 environment), then put three solo-trained agents together. If joint training teaches coordination, solo teams should do worse. The solo agent for slot k uses exactly the same exploration stream as joint agent k (`agent_ids=[k]`), so the comparison is paired.
- **A5.** Is the learning still moving? Churn, TD error, the stability criterion, and the best-validation checkpoint as a sensitivity analysis.
- **A6 (equal steps).**
  - **Problem:** with equal *episodes*, scarce runs get far fewer *environment steps*, because exploring agents run out of budget early. Mean per run: about 709k steps at Abundant against about 254k at Critical.
  - **Fix:** train Moderate, Scarce and Critical until they have used as many steps as the Abundant run of the same seed.
  - **Question:** is "scarcity hurts" just "less practice"?
- **A7.** The full statistical battery above.
- **A8.** Regress each seed's RF on the six standardised metrics (C1, C2-other, C3, C4a, C4b, C5) plus level dummies.
  - Confidence intervals come from a **cluster bootstrap by seed**: whole seeds are resampled.
  - Two seed-level observations were excluded because EAR was undefined (no ASSISTs), leaving n = 38.
  - Purpose: an *observational* check of whether cooperation and performance go together within a level.

## E.7 Metrics recap: primary versus secondary

- **Primary outcome:** RF, the rescue fraction (rescued / 6), averaged over a seed's 100 test episodes.
- **Secondary outcomes:**
  - heavy share and light share;
  - collective return;
  - the 7 cooperation metrics;
  - E1–E3;
  - termination shares and steps.

---

# PART F — The results, and how to interpret them

All numbers are from the 100 test maps at the final checkpoint after 8,000 episodes. They are given as mean [95% bootstrap CI] over 10 seeds unless stated. Sources: `results/stats/*.csv`, `results/stats/results.json`, and report tables 8–19 and figures 1–9.

## F.1 H0: does learning work at all? (CONFIRMATORY)

1. **Measured.** IQL RF at Abundant vs the random baseline's RF.
2. **Numbers.**
   - IQL 0.573 [0.517, 0.627] vs random 0.063.
   - All 10 seeds are above random: W⁺ = 55 (the maximum possible), one-sided exact p = 1/1024 ≈ 9.8 × 10⁻⁴, δ₁ = 1.00.
3. **Graph.** Report Fig. 1 shows the learning curves: validation RF against episodes, one line per level, with a 95% CI band. They rise while ε falls, then flatten with fluctuations.
4. **Supports.** The agents learned something real; the main experiment was allowed to proceed.
5. **Does not support.** "IQL learned well" or "learned to cooperate". 0.573 is far below the cooperative baseline (0.985).
6. **Caveats.** The policy is not converged. The best-validation checkpoint gives 0.647 at Abundant.

## F.2 H1: scarcity reduces rescue performance (CONFIRMATORY)

| Level | RF | Heavy share | Light share | Exhausted | Horizon | Steps |
|---|---|---|---|---|---|---|
| Abundant | 0.573 [0.517, 0.627] | 0.422 | 0.723 | 0.03 | 0.90 | 99.6 |
| Moderate | 0.344 [0.319, 0.368] | 0.221 | 0.467 | 0.34 | 0.66 | 80.0 |
| Scarce | 0.180 [0.166, 0.194] | 0.083 | 0.277 | 0.56 | 0.44 | 59.3 |
| Critical | 0.087 [0.076, 0.098] | 0.016 | 0.159 | 0.51 | 0.49 | 64.2 |

1. **Measured.** The mean rescue fraction per level, the split by victim type, and how episodes ended.
2. **Numbers.**
   - Friedman χ²(3) = 30.0, p = 1.4 × 10⁻⁶, **Kendall's W = 1.00**: every seed ranks the levels Abundant > Moderate > Scarce > Critical.
   - Page two-sided p = 3.2 × 10⁻¹⁴.
   - All 6 pairwise differences: Holm p = 0.0117. Even Scarce → Critical costs 0.092 [0.071, 0.114].
3. **Graph.** Report Fig. 2 has per-seed lines connecting the same seed across levels; every line goes down.
4. **Supports.** Scarcity *causes* a large, monotone fall in rescues **in this environment with this training procedure**. It is causal because ρ was manipulated with everything else held fixed.
5. **Heavy rescues vanish first.** The heavy share falls 0.422 → 0.016, which is 26 times lower; the light share falls 0.723 → 0.159, which is 4.5 times lower.
6. **Does not support.**
   - That the fall happens *because of* cooperation (Part F.7).
   - That it would look the same after convergence.
7. **Termination.** See §0 item 0.1.
   - At Abundant, 90% of test episodes end at the horizon. **[Interpretation, also in the report]** The teams are slow rather than broke.
   - At Scarce and Critical, about half end by exhaustion and half at the horizon: some agents end the mission with budget unspent.
   - The *data* say only that at least one agent still had ≥ 3 units at t = 105. Why the greedy policy stopped spending (for example, by WAITing) would need a behavioural analysis we did not run.

## F.3 H3: IQL versus the baselines (CONFIRMATORY, Holm over 12)

| Level | IQL | Random | Greedy | Cooperative | Oracle reference |
|---|---|---|---|---|---|
| Abundant | 0.573 | 0.063 | 0.465 | 0.985 | 1.000 |
| Moderate | 0.344 | 0.024 | 0.227 | 0.707 | 0.960 |
| Scarce | 0.180 | 0.010 | 0.123 | 0.413 | 0.617 |
| Critical | 0.087 | 0.005 | 0.075 | 0.233 | 0.403 |

**Statistical results.**
- **vs random:** IQL is above it at every level (10/10 seeds).
- **vs greedy:**
  - above it at Abundant (Holm p = 0.027; 9/10 seeds);
  - above it at Moderate and Scarce (Holm p = 0.023; 10/10);
  - **not significantly different at Critical:** 0.012 [0.001, 0.023]; 7 seeds above, 2 below, 1 exact tie; Holm p = 0.0742. The bootstrap CI of the mean just excludes 0, but the preregistered test (rank-based, Holm over 12) is not significant. The test decides.
- **vs cooperative:** IQL is **below** it everywhere (0/10 seeds above). The gap is −0.412 at Abundant and −0.146 at Critical.

**Interpretation.**
- **Greedy** is a weak opponent: its three agents run the same deterministic rule from the same base, so they move in lockstep and never ASSIST. Beating it shows IQL beats *uncoordinated identical agents*, not "selfishness" in general.
- **The cooperative baseline** shows what simple, explicit conventions achieve. **[Interpretation]** Two reasons for IQL's gap are well supported by the repository:
  - The cooperative policy reads the full `AgentView`: memory, teammate identities and positions, and its own history (§0 item 0.3). IQL reads a 5-number summary that drops teammate identity.
  - IQL had not converged.

  Neither reason was separately tested.
- **The oracle reference** shows how much is lost to imperfect information and coordination. At Critical, even full information rescues only 40%: the budget itself limits what is possible.

## F.4 H2: cooperative behaviour under scarcity (CONFIRMATORY, Holm over 7)

| Metric | Abundant | Critical | n | Friedman p (Holm) | W |
|---|---|---|---|---|---|
| CR cooperation rate | 0.180 | 0.023 | 10 | 1.7 × 10⁻⁴ | 0.80 |
| PSS productive spend share | 0.087 | 0.055 | 10 | 5.6 × 10⁻⁴ | 0.71 |
| RSR redundant search | 0.700 | 0.442 | 10 | 0.0041 | 0.56 |
| RSR_other | 0.216 | 0.198 | 10 | 0.025 (non-monotone; Page Holm p = 1.00) | 0.41 |
| EAR effective assist rate | 0.447 | 0.319 | **8** | 0.41 (n.s.) | 0.23 |
| TDI territory division | 0.607 | 0.461 | 10 | 0.59 (n.s.) | 0.12 |
| Consumption Gini | 0.073 | 0.085 | 10 | 0.90 (n.s.) | 0.02 |

**How to read it.**
- **CR collapses**, from 0.180 to 0.023. Abundant and Moderate do not differ significantly; the drop happens from Moderate to Critical.
- **PSS falls**, but PSS largely restates "fewer rescues per unit spent" (it tracks reward), so it is **not independent evidence** of cooperation.
- **RSR_other peaks at Scarce** (0.476). At Critical agents hardly SEARCH, so there is little left to be redundant.
- **EAR, TDI and Gini show no significant change.** With 10 seeds (8 for EAR, because two seeds never ASSISTed at some level), this is **inconclusive**, not proof of no change.

**Supports.** Under scarcity the learned teams stop performing *joint* actions (convergence on heavy victims). We found no significant change in the more generic teamwork aspects.

**Does not support.**
- "Cooperation in general declines."
- "Scarcity causes the loss of cooperation, which causes the loss of rescues." That second link is H5's job.

**Graph.** Report Fig. 3 shows the seven metrics by level with per-seed lines.

## F.5 Exp4: individual versus collective interest (EXPLORATORY)

| Level | E1 abandonment / episode | E2 duplicates / episode | E3 conflict share | Spearman(best agent, team) |
|---|---|---|---|---|
| Abundant | 3.337 | 0.362 | 0.161 | 0.95 |
| Moderate | 1.693 | 0.120 | 0.148 | 0.96 |
| Scarce | 0.372 | 0.067 | 0.209 | 0.95 |
| Critical | 0.152 | 0.024 | 0.052 | 0.95 |

- **E1 falls** under scarcity. This is most likely not better coordination: agents rarely meet at heavy victims at all, so there is little to abandon.
- **The high E1 at Abundant (3.3 per episode)** is itself evidence of imperfect coordination. Agents often stand together on a heavy victim and still fail to play the complementary actions in the same step.
- **The best agent and the team move together** (Spearman ≈ 0.95). Within this reward design, individual and collective interests rarely conflict.
- **[Interpretation, as in the report]** The obstacle is the *difficulty of joint action*, not a social dilemma. A plausible reason is the team reward term, which makes every rescue valuable to everyone.

## F.6 H4 (A1): teammate mismatch (CONFIRMATORY)

| Level | Original | Mismatched | Difference [CI] | Relative drop | Seeds original better | p (Holm) |
|---|---|---|---|---|---|---|
| Abundant | 0.573 | 0.439 | 0.1335 [0.057, 0.211] | 23% | 8 | 0.027 |
| Moderate | 0.344 | 0.255 | 0.090 [0.067, 0.114] | 26% | 10 | 0.0078 |
| Scarce | 0.180 | 0.137 | 0.043 [0.025, 0.063] | 24% | 10 | 0.0078 |
| Critical | 0.087 | 0.070 | 0.017 [0.004, 0.030] | 20% | 8 | 0.084 (n.s.) |

**Supports.** Each seed's agents learned conventions that work with *their own* partners. This is co-adaptation, a fingerprint of learned coordination.

**Caveats.**
- **Critical** is not significant: little joint behaviour is left to disrupt.
- **Dependence.** Each agent appears in several mismatched teams, so the 10 differences are not fully independent (preregistered caveat).

**Does not support.** That co-adaptation is *why* scarcity lowers RF.

## F.7 H5 (A3): does scarcity hurt *more* when cooperation is needed? (CONFIRMATORY, negative)

**Inputs** (learned RF / oracle reference):

| Level | IQL heavy world | IQL all-light world | Oracle heavy | Oracle all-light |
|---|---|---|---|---|
| Abundant | 0.573 | 0.931 | 1.000 | 1.000 |
| Critical | 0.087 | 0.198 | 0.403 | 0.497 |

**Results under every analysis** (report Table 15; positive = scarcity removes more in the heavy world):

| Analysis | Family | DiD [95% CI] | Seeds > 0 | Retained at Critical: heavy vs all-light |
|---|---|---|---|---|
| Raw RF | **CONFIRMATORY** | **−0.248 [−0.322, −0.171]**, p = 0.002 | 0 | 0.153 vs 0.213 |
| Oracle-normalised | SECONDARY | −0.176 [−0.266, −0.081] | 2 | 0.378 vs 0.428 |
| Raw, own calibration | SECONDARY | −0.207 [−0.273, −0.138] | 1 | 0.153 vs 0.109 |
| Oracle-normalised, own calibration | SECONDARY | +0.052 [−0.029, 0.147] | 6 | 0.378 vs 0.609 |
| Log drop | POST HOC | +0.331 [0.113, 0.575] | 8 | 0.151 vs 0.210 |
| Log drop, own calibration | POST HOC | −0.339 [−0.550, −0.083] | 2 | 0.151 vs 0.108 |

**What the confirmatory result says.** In absolute points, the all-light world *loses more* (0.931 → 0.198 is −0.733) than the heavy world (0.573 → 0.087 is −0.486). The preregistered test is significant **in the opposite direction** to the "cooperation bottleneck" idea.

**Why it is not evidence that cooperation *protects* against scarcity:**
1. **Floor effect.** The heavy world starts much lower and is near the floor at Critical; it *cannot* lose many more points.
2. **Scale.** As a *fraction*, the heavy world keeps 15% of its Abundant RF while the all-light world keeps 21%. The post hoc log version is therefore positive.
3. **Calibration.** If the all-light world gets its own (smaller) calibration, the normalised DiD is null and the log DiD turns negative.

**Conclusion.** There is no consistent sign across reasonable scales and calibrations, so **we make no claim** that scarcity specifically destroys cooperation-dependent rescues.

**What A3 does show robustly.** The all-light world shows the same steep decline (Page p = 3.2 × 10⁻¹⁴). A large scarcity effect therefore arises *even when cooperation is never required*.

**Why this matters scientifically.**
- A preregistered test that fails or reverses is still knowledge. It tells us that the obvious story ("scarcity kills cooperation, which kills rescues") is not what our data show.
- It also shows how fragile a difference-in-differences becomes near floors and ceilings. An additive scale silently assumes that a point lost at RF = 0.9 means the same as a point lost at RF = 0.1.
- **The post hoc log analysis** was added after we saw H5 (deviation C4). Its first version had a sign error, which we found and corrected (C5). It is labelled post hoc everywhere and never replaces the preregistered result.

**Graph.** Report Fig. 5 shows both worlds' curves with oracle references, plus the DiD under the main-budget analyses.

## F.8 H6 (A4): joint versus solo training (CONFIRMATORY, with a confound)

| Level | Joint | Solo team | Difference [CI] | p (Holm) |
|---|---|---|---|---|
| Abundant | 0.573 | 0.101 | 0.471 [0.415, 0.527] | 0.0078 |
| Moderate | 0.344 | 0.039 | 0.305 [0.280, 0.329] | 0.0078 |
| Scarce | 0.180 | 0.015 | 0.165 [0.150, 0.179] | 0.0078 |
| Critical | 0.087 | 0.006 | 0.081 [0.070, 0.091] | 0.0078 |

**Supports.** Training with teammates matters enormously; 10/10 seeds favour joint training at every level.

**Confound.** Solo agents never observed a teammate, so f3 was always "none" in training. At deployment they meet observations with f3 ≠ none, whose Q-rows are still at their initial zero. This distribution shift alone could produce a large drop. The gap therefore **overstates** how much of the effect is learned coordination.

**A cleaner design** (not run): solo training with scripted or random "dummy" teammates, so that f3 is populated during training.

## F.9 Exp5: generalisation (EXPLORATORY)

**Transfer matrix** (rows = trained at, columns = tested at):

| Trained \ Tested | Abundant | Moderate | Scarce | Critical |
|---|---|---|---|---|
| Abundant | **0.573** | 0.192 | 0.072 | 0.010 |
| Moderate | 0.161 | **0.344** | 0.207 | 0.116 |
| Scarce | 0.059 | 0.169 | **0.180** | 0.121 |
| Critical | 0.049 | 0.106 | 0.100 | **0.087** |

**What it shows.**
- **Policies specialise.** An Abundant-trained policy collapses at Critical (0.010). Most likely it spends as if budget were plentiful.
- **Moderate- and Scarce-trained policies do *better* at Critical** (0.116, 0.121) than the Critical-trained one (0.087). A plausible reason: training at Critical gives few successful episodes to learn from.
- **This happens even though** the budget feature f4 means the same absolute amount at every level.

**Shifted test maps** (walls 0.25, density 0.09):
- RF is 0.429 / 0.256 / 0.139 / 0.079, lower at every level.
- The ordering is preserved (Page p = 3.2 × 10⁻¹⁴).

**Graph.** Report Fig. 6.

## F.10 A5: non-stationarity (EXPLORATORY)

**What the data show.**
- Policy churn at the last checkpoint is about 5–13% on average across levels (main block: 12.6% at Abundant, 9.2% at Critical).
- The mean |TD error| is **still rising** at 8,000 episodes.
- Validation RF still fluctuates.
- **5 of 350 runs** meet the stability criterion, and **0 of the 40 main runs**.
- The preregistered "stable runs only" sensitivity analysis could therefore not be computed. We report that rather than redefine "stable".

**The best-validation checkpoint:**
- gives the same H1 conclusion (W = 1.00);
- gives a higher Abundant RF (0.647).

**Interpretation.** The policies are still moving, but the scarcity *ordering* is the same wherever we sample them.

**Graph.** Report Fig. 7 shows churn, TD error, and the number of stable runs per block.

## F.11 A6, pooled budgets, the alternate map, and robustness (EXPLORATORY)

- **A6 (equal steps).** Change in RF:
  - Moderate +0.078 [0.036, 0.116] (unadjusted p = 0.0098);
  - Scarce −0.034;
  - Critical +0.016 [−0.009, 0.043].

  The trend is unchanged (Page p = 8.0 × 10⁻¹⁰). **Less practice explains a small part of the Moderate result and none of the overall trend.**
- **Pooled budget.**
  - RF is 0.667 / 0.405 / 0.195 / 0.129.
  - It is higher than per-agent at Moderate (+0.061, p = 0.0059) and Critical (+0.042, p = 0.002).
  - Plausibly, sharing removes the risk that the agent who must pay is the one that has run out.
  - The trend is just as strong (W = 0.96).
- **Alternate configuration** (12 × 12 maps).
  - RF is 0.455 / 0.372 / 0.198 / 0.068.
  - At Abundant, 98.5% of episodes end at the horizon: time-limited on the bigger map.
  - It is compared descriptively only, because the maps differ.
- **Trend robustness** (report Table 18). The Page trend p is < 10⁻⁹ in every variant (pooled, alternate, both all-light worlds, shifted, equal steps).

**Graph.** Report Fig. 9.

## F.12 A2: removing a teammate (EXPLORATORY)

**At Abundant:**
- replacing one learned agent by a random agent lowers RF by 0.184 (to 0.389);
- replacing it by a WAIT-only agent lowers RF by 0.281 (to 0.292).

The drops shrink with scarcity (WAIT replacement at Critical: 0.038).

**The cooperative baseline under the same ablation:** 0.985 → 0.768 (random) or 0.810 (WAIT).

**Caveat.** Part of any drop is simply losing a third of the team's search capacity and budget, so A2 alone does not isolate cooperation.

## F.13 A8: association between cooperation and performance (EXPLORATORY, observational)

**Variance explained.**
- R² = 0.927 with level dummies only.
- R² = 0.978 with the six metrics added.

**Single-metric models** (level fixed): CR has a coefficient of 0.082 [0.054, 0.120] RF per standard deviation. Seeds that cooperate more rescue more.

**Joint model.**
- Only **PSS** keeps a CI that excludes 0: 0.046 [0.014, 0.074].
- CR's interval includes 0: 0.026 [−0.016, 0.091].
- PSS and CR are collinear (VIF 7.8 and 8.3), and PSS largely restates reward.

**This is association, not causation.**
- Seeds differ in many ways.
- The metrics and RF are both outcomes of the same policy.
- 38 observations from 10 seeds cannot separate them.

**Graph.** Report Fig. 8.

## F.14 The claims ledger and final audit

- **`docs/claims_ledger.md`** lists 72 claims used in the phase summaries, each with its file and locator. All 72 are verified (V5).
- **`docs/report_numbers.yaml`** lists all 579 numbers shown in the report. The verifier re-reads each from source and checks it appears in the Word file (V7).
- **`docs/final_audit.md`** checks every master-prompt requirement:
  - all pass, a few "with note" (run time 2.4 h vs the "about 2 h" target; four compact tables show means only; reference [6]'s volume and pages unconfirmed);
  - none failed or incomplete.

**What the audit does *not* certify.** Interpretive sentences such as §9.2's termination sentence (§0 item 0.1). The verifier checks numbers, not prose.

## F.15 Summary: what we can and cannot claim

**We can claim** (within this environment, IQL, 8,000 episodes, 10 seeds):
1. Scarcity causes a large, monotone fall in rescues. It holds in every seed and every robustness variant.
2. Joint (heavy) rescues and the cooperation rate collapse under scarcity. We found no significant change in territory division, load balance or assist efficiency.
3. Learned teams rely on co-adapted conventions (H4 at 3 of 4 levels). Joint training matters greatly (H6), though partly through distribution shift.
4. A large scarcity effect arises even when cooperation is never necessary (A3, all-light world).

**We cannot claim:**
1. That scarcity hurts *more* when cooperation is necessary (H5 reversed and fragile).
2. That cooperation *causes* better performance (A8 is observational).
3. Anything about converged or optimal policies.
4. That IQL beats selfish strategies in general (the greedy baseline is weak; no significant difference at Critical).
5. Generalisation to other algorithms, team sizes, small maps, ρ = 0.1, or communication-enabled agents.

---

# PART G — The important design decisions

Documented decisions are D1–D29 in `docs/design_decisions.md`. For each major decision below, **"Documented"** gives the recorded alternatives and reasons. **"Interpretation"** marks my own technical comments.

| Decision | Alternatives | Documented reason | Interpretation |
|---|---|---|---|
| **D1 Per-agent budgets**, pooled as an ablation | one global pool; transferable budgets | Per-agent budgets create a team allocation problem; the ablation shows whether conclusions depend on it | Pooled helped a little (+0.04 to +0.06) but did not change the trend, so the conclusion is robust to this choice. |
| **D2 Exhaustion** = max budget < c_R | end only when all budgets are 0; never before H | After that point no action can change RF | Agents with 1–2 units could still SEARCH; this affects coverage only. |
| **D3 Action masking**, identical for all policies | invalid actions with penalties | Penalties waste samples learning rules; masks keep baselines comparable | D3 records that requiring a co-located teammate for ASSIST "slightly helps learners". It applies equally to all methods. |
| **D4 Heavy victims need simultaneous RESCUE + ASSIST** | "two agents on the cell" without roles; a time-extended lift | Makes cooperation *causally necessary* for part of the outcome; p_heavy = 0 gives a control world (A3) | Same-step simultaneity is a very strict test of coordination. The high E1 at Abundant shows IQL often gets the timing wrong. |
| **D5 Map known in advance**; victims and teammates hidden | hide the terrain too | Keeps the observation tabular (3,960 states) and focuses partial observability on the research question | Partial observability is weaker than in a real disaster. |
| **D6 5-feature observation** with path-based directions | raw local window (too many states) | Small table; path directions avoid getting stuck at walls | Aliasing is the price: different situations look identical. |
| **D7 Budget buckets relative to B_ref** | buckets relative to the agent's own start budget | A bucket means the same amount at every ρ, so transfer is interpretable | It makes the transfer matrix meaningful. |
| **D8 Reward split** (heavy 0.5/0.5, light 1.0; team 1.0 per rescue) | heavy victims worth more | Equal value per life; built-in individual-vs-team tension | Exp4 found little actual conflict: the team term dominates. |
| **D9 Behavioural cooperation metrics** | team reward as a proxy | Requested by the review; avoids tautology | PSS still turned out to track reward (D22). |
| **D10 Oracle reference** (greedy-insertion planner) | exact optimum (intractable), mixed-integer program | Honesty about what is and is not optimal | 297/300 equal to the exhaustive optimum on tiny maps. |
| **D11 Calibrate from the cooperative baseline** | guess values; calibrate from RL agents | Reproducible definition; avoids circularity (calibrating on learners would tie ρ to what is being measured) | B_ref inherits the baseline's efficiency. With a better planner, B_ref would be lower. |
| **D12 n = 3 agents** | 2 or 4 | With 2, the agent ablation is trivial; 4 increases non-stationarity and compute | Results may not extend to larger teams. |
| **D13 Fixed pool of 1,000 training maps**; disjoint test/validation | fresh maps per episode | No test leakage; CRN across conditions | — |
| **D14 Final checkpoint is primary**; best-validation is a sensitivity analysis | best checkpoint as primary | Avoids selection bias | Best-validation gives higher RF but the same conclusions. |
| **D15 Unit = seed; paired non-parametric tests**; Holm; bootstrap | per-episode tests (pseudo-replication); unpaired tests | Seeds are the independent replicates; CRN makes conditions paired | The minimum p of 0.002 limits power for small effects. |
| **D16 No communication** | a cost-bearing BEACON action | Keeps the scarcity effect uncontaminated | It is an obvious next experiment. |
| **D17 Policies use only observed information** | ground-truth masking | No hidden-information leaks; stale memory only wastes travel | — |
| **D19 Greedy and cooperative share helper code** | separate implementations | Their only difference is the cooperation rules | — |
| **D22 Keep greedy as implemented** (lockstep); keep PSS with a caveat | add agent-specific tie-breaks; drop PSS | Group decisions at the Phase 2 gate, before freezing | Changing the greedy baseline after seeing it was weak would have been tuning a comparator. |
| **D26 Analysis mechanics fixed before any test statistic** | decide while analysing | Prevents garden-of-forking-paths choices | — |
| **D28 Report generated from result files** | hand-typed numbers | Every number traceable and machine-checked | It does not check prose (see §0.1). |
| **D29 Quick mode at 3 seeds × 3,000 episodes** | 1,500 episodes | Shows a learning signal in under 10 minutes | — |

**Choices that came from the preregistration and were never tuned:**
- α = 0.1, γ = 0.98;
- the ε schedule;
- 8,000 episodes;
- λ values;
- costs;
- the ρ levels (from calibration);
- the tests.

The pilot was allowed to change a short list of these only if the defaults failed; they passed.

---

# PART H — Limitations and critical analysis

## H.1 What did not work, or was not supported
1. **H5 (A3).** The cooperation-specific bottleneck was not supported. The test reversed on the absolute scale and was unstable across scale and calibration.
2. **H3 vs greedy at Critical.** Not significant (Holm p = 0.074).
3. **H4 at Critical.** Not significant (Holm p = 0.084).
4. **H2 for EAR, TDI and Gini.** No significant change; inconclusive.
5. **Stability.** 0 of 40 main runs were stable, so the stable-only sensitivity analysis could not be done.
6. **IQL vs the cooperative baseline.** IQL is below it everywhere, by up to 0.41 RF.
7. **Calibration.** Critical missed its target band (cooperative RF 0.220 vs 0.10–0.15), because ρ = 0.1 is mostly infeasible.

## H.2 Limitations of the experiments
- **No convergence.** The most important limitation. Absolute levels, and possibly some effect sizes, could change with more training.
- **10 seeds.** Good for large, consistent effects; weak for small ones.
- **One environment family, three agents, tabular IQL with a hand-designed observation, no communication.**
- **The time-limited Abundant regime.** Most Abundant test episodes end at the horizon, so Abundant partly measures speed. This is stronger on 12 × 12 maps (98.5%).
- **A1 dependence.** Mismatched teams share agents across seeds, so their differences are not fully independent.
- **A4 confound.** Distribution shift in the teammate feature.
- **A8 is observational, with collinear metrics.**
- **Metric construct issues.**
  - PSS tracks reward.
  - EAR is undefined for seeds that never ASSIST, which drops n to 8.
  - CR depends on the 2L look-back window, a design constant.
- **The interpretation text error** in report §9.2 (§0.1). Only the prose is wrong; the data are correct.

## H.3 Assumptions we made
- **Simultaneity:** a heavy rescue needs the same step, with no tolerance window.
- **Free waiting:** WAIT costs 0, so waiting for a partner is free in budget terms (but not in time).
- **No communication.**
- **Known map.**
- **Deterministic transitions.**
- **Additive reward with fixed λ** across all conditions.
- **Treating the horizon as terminal** in the Q-target.
- **Equal value for every victim.**

## H.4 Weaknesses of the baselines
- **Greedy:** lockstep agents; never ASSISTs; tries each heavy victim at most once. It is a weak representative of selfish behaviour. The Phase 2 validation shows the lockstep directly: greedy's territory-division index is 0.000, meaning all three agents visit exactly the same cells (`results/phase2/metric_validation_summary.md`).
- **Cooperative:**
  - hand-designed;
  - uses teammate identities and a richer view than IQL, so the comparison is not information-matched at the feature level (§0.3);
  - it also defined B_ref, so it is "calibrated to itself" at Abundant (RF 0.985).
- **Random:** a floor only.
- **Oracle:** a heuristic, not an optimum; uses full information; not decentralised.

## H.5 Possible sources of bias, and what protects against them

| Possible bias | Protection |
|---|---|
| Choosing tests after seeing data | preregistration + hash; D26; post hoc analyses labelled |
| Tuning on test data | pilot on validation only; nothing changed; test touched only at the end |
| Selecting a lucky checkpoint | final checkpoint primary; best-validation as sensitivity only |
| Pseudo-replication | unit = seed |
| Multiple testing | Holm within families; exploratory p-values unadjusted and labelled |
| Hidden-information leaks | AgentView-only masks and features; tests; InvalidActionError |
| Reporting errors | generated report; 579 numbers verified; 72 claims verified |
| Calibration circularity | calibrated from baselines and the oracle, never from learners |
| Interpretation bias (prose) | **not machine-checked**; §0.1 is an example that slipped through |

## H.6 What we would improve with more time
1. **Train longer** (e.g. 32,000 episodes, or until the stability criterion holds), and report at matched convergence.
2. **More seeds** (20–30) for power on small effects.
3. **Fix the A4 confound:** solo training with dummy or scripted teammates so that f3 is populated.
4. **Information-matched cooperative baseline:** a hand-written policy that reads only f1–f5, to separate "learning" from "information" in the IQL-vs-cooperative gap.
5. **A stronger selfish baseline:** greedy agents with independent tie-breaking, or individually trained selfish learners (λ_T = 0).
6. **A3 on a proportional scale, preregistered:** compare log-retention, or use oracle-normalised RF as primary. Or choose comparison worlds matched on their Abundant RF to avoid floors and ceilings.
7. **Centralised training with decentralised execution** (e.g. value decomposition) as a second learner, to see whether the conclusions are specific to IQL.
8. **Communication** (the planned BEACON action) to test whether signalling rescues cooperation under scarcity.
9. **Behavioural analysis of horizon terminations at Critical** (§0.1): why do greedy learned policies stop spending?
10. **A ρ grid between 0.1 and 0.2**, with feasibility-conditioned analysis, to reach the intended Critical band.

## H.7 Additional experiments that would strengthen the conclusions
- **Varying p_heavy** (0, 0.25, 0.5, 0.75) at fixed ρ: a dose-response test of how much cooperation demand changes the scarcity slope.
- **Cooperation interventions at test time:** force the convergence behaviour (for example, a scripted "stay and assist" rule) and see whether RF under scarcity recovers. This would be causal evidence for the mediation path that A8 can only suggest.
- **Team sizes 2 and 4.**

---

# PART I — Viva preparation: 45 questions at three levels

Format for each question:
- **Q:** the question.
- **Tests:** what the examiner is checking.
- **A:** a technically correct answer.
- **Follow-up:** a likely next question.
- **Reason:** how to think it through.

## Level 1 — Basic understanding (15)

**1. Q: What is your project about, in two sentences?**
*Tests:* whether you can state the problem.
**A:** Three independent Q-learning agents must rescue victims on a grid with private, non-refillable budgets. Half the victims need two agents acting in the same step. We test how shrinking the budget (scarcity) affects rescues and cooperative behaviour, and whether the loss of rescues is due to loss of cooperation.
*Follow-up:* "And what did you find?"
*Reason:* Give the three-part answer:
- scarcity strongly reduces rescues;
- joint rescues collapse;
- but the preregistered test of a cooperation-specific bottleneck reversed, so we make no such claim.

All results are after 8,000 episodes.

**2. Q: What is resource scarcity in your environment?**
*Tests:* the core manipulation.
**A:** Each agent starts with B₀ = round(ρ·B_ref) units, with B_ref = 64. ρ is 1.0, 0.5, 0.3 or 0.2 (budgets 64, 32, 19, 13). Everything else is held fixed.
*Follow-up:* "Why not just pick 64, 32, 16, 8?"
*Reason:* ρ is a fraction of a *measured* just-enough budget, so it has a meaning that transfers across maps. The levels were chosen from the cooperative baseline's RF targets under a feasibility rule.

**3. Q: What does cooperation mean in your project?**
*Tests:* precision.
**A:** It has two layers:
- **necessary cooperation:** a heavy victim needs RESCUE plus ASSIST by different agents on the same cell in the same step;
- **useful cooperation:** spreading out, avoiding redundant searches, balancing load.

We measure it from action logs with seven metrics, never from reward.
*Follow-up:* "Which is your main cooperation metric and how is it computed?"
*Reason:* CR = cooperative non-WAIT actions ÷ non-WAIT actions. Cooperative actions are the effective RESCUE and ASSIST of each heavy rescue plus the participants' moves that converged on the victim in the 2L = 20 steps before.

**4. Q: What are the actions and their costs?**
*Tests:* environment basics.
**A:**
- UP, DOWN, LEFT, RIGHT: 1 each (2 into a hazard cell);
- SEARCH: 2;
- RESCUE: 3;
- ASSIST: 2;
- WAIT: 0.

*Follow-up:* "Why is WAIT free?"
*Reason:* So an agent always has a legal action even with zero budget. The code refuses any configuration where WAIT has a cost.

**5. Q: What does an agent observe?**
*Tests:* partial observability.
**A:** A 5-feature tuple (3,960 values):
- the nearest believed-waiting victim (direction and near/far, or "here light/heavy");
- the direction to unexplored cells;
- the nearest teammate within 3 cells;
- its own budget bucket;
- the time third.

*Follow-up:* "Can the agent see its teammates' budgets?"
*Reason:* No. Only position (within 3 cells, as a direction) and no identity in the learner's features.

**6. Q: When does an episode end?**
*Tests:* termination rules.
**A:** In order:
1. all victims rescued;
2. exhausted: no agent can afford a RESCUE, i.e. max budget < 3;
3. horizon: t = 105.

*Follow-up:* "Why end at exhaustion instead of letting agents keep going?"
*Reason:* After that point no action can change the rescue count, so continuing only wastes compute and dilutes per-step metrics (D2).

**7. Q: What is reinforcement learning?**
*Tests:* fundamentals.
**A:** Learning by trial and error to maximise cumulative (discounted) reward. Act, observe the reward and the next situation, and update your estimates of which actions are good.
*Follow-up:* "What is the agent maximising in your case?"
*Reason:* Its own discounted return of R_i = r_ind + r_team − 0.02·cost, with γ = 0.98.

**8. Q: What is a Q-value?**
*Tests:* core concept.
**A:** Q(o, a) is the estimated total discounted future reward of taking action a in observation o and acting well afterwards.
*Follow-up:* "How do you get the policy from it?"
*Reason:* Greedy: pick argmax over valid actions, with ties broken randomly (evaluation ties use seeded generators).

**9. Q: What does "independent" mean in IQL?**
*Tests:* the MARL framing.
**A:** Each agent has its own Q-table and learns only from its own reward, treating teammates as part of the environment. There is no shared learning and no communication.
*Follow-up:* "What problem does that cause?"
*Reason:* Non-stationarity: teammates change as they learn, so each agent's environment keeps changing.

**10. Q: What is exploration vs exploitation, and how do you handle it?**
*Tests:* fundamentals.
**A:** ε-greedy:
- with probability ε, a random *valid* action;
- otherwise, the best Q.

ε falls linearly from 1.0 to 0.05 over the first 70% of episodes.
*Follow-up:* "What happens at test time?"
*Reason:* ε = 0: purely greedy, with common-random-number tie-breaks.

**11. Q: What are your baselines and why?**
*Tests:* experimental design.
**A:**
- random (floor);
- greedy (uncoordinated, never ASSISTs);
- cooperative (hand-designed conventions, same information source);
- the oracle reference (full information, a planner, not a learner, not tested).

*Follow-up:* "Why is the oracle not a baseline in your tests?"
*Reason:* It has information no agent has and plans centrally. It is a scale reference, not a competitor.

**12. Q: What is a training seed and why 10?**
*Tests:* replication.
**A:** One independent repetition of the whole training process (map order and exploration streams). There are 10 per condition, preregistered; each condition costs 10 runs.
*Follow-up:* "Why not count the 100 test episodes as your sample?"
*Reason:* They are repeated measurements of one trained team. That would be pseudo-replication.

**13. Q: What is the difference between validation and test data?**
*Tests:* methodology.
**A:**
- **Validation (50 maps):** checkpoints during training, the best-validation checkpoint, and the pilot.
- **Test (100 maps):** final evaluation only.

The two sets are disjoint and frozen with hashes.
*Follow-up:* "Did you ever look at test results to change anything?"
*Reason:* No. The pilot used validation only, and nothing was changed. Test data were used only in Phase 5 evaluation.

**14. Q: What does preregistration mean and why do it?**
*Tests:* research integrity.
**A:** Hypotheses, tests and analysis rules were written and hash-frozen before any learning run. This prevents choosing analyses after seeing results.
*Follow-up:* "Did you deviate?"
*Reason:* Yes, logged:
- C1–C6 and N2–N5 after the freeze;
- C4 is the only post hoc analysis, labelled;
- C5 and C6 are bug fixes;
- none changed a hypothesis or parameter.

**15. Q: What is calibration and what did it give you?**
*Tests:* review point R3.
**A:** Measuring the task to set H and B_ref before any learning:
- H = ⌈T₉₀/0.7⌉ = 105;
- B_ref = 90th percentile of the cooperative baseline's per-agent consumption = 64;
- ρ levels from RF targets.

*Follow-up:* "Does ρ mean the same on every map?"
*Reason:* For L ≥ 10, nearly (spread ≤ 0.079). Not on 8 × 8 maps.

## Level 2 — Technical understanding (16)

**16. Q: Write the Q-learning update you implemented.**
*Tests:* exact algorithm knowledge.
**A:** Q(o,a) ← Q(o,a) + α[r + γ·max_{a′∈M(o′)} Q(o′,a′) − Q(o,a)], with:
- α = 0.1, γ = 0.98;
- target = r when the episode ended (any termination);
- the max over the next state's **valid** actions;
- Q initialised to 0.

*Follow-up:* "Why take the max only over valid actions?"
*Reason:* An invalid action can never be taken, so its value is irrelevant. The agent knows its own next mask, so no hidden information is used.

**17. Q: Which agents get updates on a step?**
*Tests:* code detail.
**A:** Every agent that was **not dormant** at the start of the step. A dormant agent (budget < 1) could only WAIT, so there was no choice to learn from (`train_episode`).
*Follow-up:* "Is the horizon terminal in the target?"
*Reason:* Yes, done = 1 for every termination. This is a simplification consistent with the time feature f5.

**18. Q: How is the observation encoded as a table row?**
*Tests:* implementation.
**A:** Mixed radix: o = (((f1·5 + f2)·6 + f3)·4 + f4)·3 + f5, giving 0..3,959.
*Follow-up:* "How big is each run's Q-table?"
*Reason:* 3 × 3,960 × 8 = 95,040 entries.

**19. Q: Give the budget-bucket thresholds and explain bucket 0.**
*Tests:* the f4 design.
**A:**
- τ1 = c_R = 3;
- τ2 = max(4, ⌈B_ref/4⌉) = 16;
- τ3 = max(17, ⌈B_ref/2⌉) = 32.

Half-open buckets. Bucket 0 = "cannot pay for a RESCUE" (per-agent mode).
*Follow-up:* "What about pooled mode?"
*Reason:* f4 uses floor(pool/3), the per-capita share, while the mask uses the whole pool. So bucket 0 does *not* mean the team cannot RESCUE (P4).

**20. Q: Walk through the order of operations in one step.**
*Tests:* the transition function.
**A:**
1. validate actions against the masks;
2. pay;
3. move;
4. resolve RESCUE/ASSIST cell by cell;
5. sense (radius 1, plus radius 2 after SEARCH);
6. reward;
7. t + 1, dormancy, termination.

*Follow-up:* "Can a heavy victim be rescued if the assister arrives in the same step it should assist?"
*Reason:* No. ASSIST requires already standing on the cell with a teammate there when the mask is issued. Moving and assisting are different actions, so you cannot do both in one step.

**21. Q: Give the reward formula and compute a heavy rescue's rewards.**
*Tests:* reward design.
**A:** R_i = r_ind + r_team − 0.02·cost.
- rescuer: 0.5 + 1 − 0.06 = 1.44;
- assister: 0.5 + 1 − 0.04 = 1.46;
- uninvolved teammate: +1.00.

(Replay `phase1_scripted_heavy_assist.txt`, t = 5.)
*Follow-up:* "Why might a selfish agent avoid heavy victims?"
*Reason:* Individually, a light rescue pays 1.0 against 0.5, needs no partner, and costs less team budget.

**22. Q: How do you compute CR exactly?**
*Tests:* metric implementation.
**A:** For each heavy rescue at (t*, c):
- add the canonical RESCUE and the canonical ASSIST (lowest-index agent in each role);
- add every move by those two agents in [t* − 2L, t*) that reduced their cheapest-path cost to c.

Divide the set's size by all non-WAIT effective actions. For a seed, pool numerators and denominators over its 100 test episodes.
*Follow-up:* "What is CR in the all-light world?"
*Reason:* 0 by construction: no rescue requires a partner.

**23. Q: Why pool ratio metrics instead of averaging per-episode ratios?**
*Tests:* statistical care.
**A:** Episodes with tiny denominators (e.g. 1 ASSIST) would otherwise get the same weight as rich episodes, and undefined ratios (0/0) would need ad hoc handling. Pooling weights by activity.
*Follow-up:* "And RF?"
*Reason:* RF is a per-episode mean (each episode has exactly 6 victims), so the mean is natural.

**24. Q: Explain the Friedman test and Kendall's W in your context.**
*Tests:* stats.
**A:**
- **The test:** for each seed, rank the 4 levels by RF. If the levels didn't matter, the ranks would be random across seeds. Friedman's χ² measures how far the rank sums are from equal.
- **W = χ²/(n(k−1)):** 1 means every seed ranks them identically.
- **Ours:** χ²(3) = 30.0 with n = 10, k = 4 gives W = 30/(10·3) = 1.00.

*Follow-up:* "Why is χ² exactly 30?"
*Reason:* That is the maximum possible with 10 seeds and 4 levels, reached when all rankings agree.

**25. Q: Why is the smallest two-sided Wilcoxon p ≈ 0.002, and why do you see 0.0117 so often?**
*Tests:* understanding of exact tests and Holm.
**A:** With 10 non-zero differences, the most extreme outcome (all in one direction) has probability 2/1024 = 0.00195 two-sided. Holm multiplies the smallest p in a family of 6 by 6, giving 0.0117. For 12 it gives 0.0234; for 4, 0.0078.
*Follow-up:* "So could you ever get p < 0.001 with 10 seeds in a pairwise test?"
*Reason:* Not two-sided Wilcoxon. Friedman and Page use more information (4 conditions), so they can go much lower.

**26. Q: How does the H3 test work when greedy has no seeds?**
*Tests:* one-sample logic.
**A:** Greedy, cooperative and the oracle are deterministic: one value per level. We test IQL's 10 seed values against that constant (one-sample Wilcoxon) and report δ₁ = (above − below)/10.
*Follow-up:* "Why was seed 8 a problem?"
*Reason:* It tied greedy exactly (45/600), but floating-point noise made the difference about 10⁻¹⁷. So the test kept it as a non-zero difference by accident. Snapping |d| < 10⁻⁹ to zero (C6) fixed it. p went from 0.084 to 0.0742, still not significant.

**27. Q: How is the A1 mismatched team built?**
*Tests:* experimental mechanics.
**A:** For seed s, slot 0 comes from seed s, slot 1 from seed σ2(s) and slot 2 from seed σ3(s). σ2 and σ3 are permutations with s, σ2(s), σ3(s) all distinct. There are two rounds from a fixed generator, averaged per seed, and the result is compared with the original team, paired by s.
*Follow-up:* "Why keep each agent in its original slot?"
*Reason:* Exploration streams and any slot-specific habits stay where they were learned. Only the *partners* change.

**28. Q: What is the DiD in A3 and why use it?**
*Tests:* the attribution design.
**A:** DiD_s = drop_heavy − drop_all-light, where drop = RF(Abundant) − RF(Critical). It asks whether scarcity removes more in the world where cooperation is necessary. Differencing within seed removes seed-specific effects.
*Follow-up:* "What did you get?"
*Reason:* −0.248, 0/10 seeds positive, p = 0.002. That is the opposite direction, and it is explained by floor effects and scale.

**29. Q: How does the bootstrap CI work here?**
*Tests:* uncertainty.
**A:** Resample the 10 seed values with replacement 10,000 times, compute the mean each time, and take the 2.5th and 97.5th percentiles. For paired contrasts, resample seeds and keep both of a seed's conditions together. For A8, resample whole seeds (a cluster bootstrap).
*Follow-up:* "Why can the CI exclude 0 when the test is not significant (greedy at Critical: CI [0.001, 0.023], Holm p = 0.074)?"
*Reason:*
- They answer different questions: the CI is about the *mean* and is unadjusted; the test uses ranks and Holm across 12 tests.
- The preregistered test decides.

**30. Q: Describe the A6 equal-steps design.**
*Tests:* confound control.
**A:** Scarce runs end episodes early, so with equal episodes they get fewer environment steps (≈ 254k at Critical vs ≈ 709k at Abundant). In A6, Moderate, Scarce and Critical train until they match the same seed's Abundant step count, with ε decaying over steps.
*Follow-up:* "Result?"
*Reason:*
- Moderate +0.078 (p = 0.0098), Scarce −0.034, Critical +0.016;
- the trend is unchanged (Page p = 8 × 10⁻¹⁰);
- less practice explains little.

**31. Q: How do you guarantee an agent never uses hidden information?**
*Tests:* implementation integrity.
**A:**
- Features and masks are computed only from `AgentView`, which the environment builds from the agent's own memory, its current view, nearby teammates, its own budget and t. Memory is a copy; the observed mask is read-only.
- Every action is re-checked, and `InvalidActionError` is raised otherwise.
- Tests check this directly.

*Follow-up:* "Then how is the first-sighting reward computed?"
*Reason:* By the environment, from ground truth. That is environment feedback, not a policy input (D17).

## Level 3 — Critical research questions (14)

**32. Q: Is your claim that "scarcity reduces performance" causal?**
*Tests:* causal reasoning.
**A:** Yes, for this environment and training procedure. ρ was manipulated with maps, seeds, exploration streams and evaluation tie-breaks held fixed, and the effect appears in every seed.
*Follow-up:* "And 'through cooperation'?"
*Reason:* That is a different, mediated claim. It needs interventions on the mediator. Our interventions (A1, A3, A4) do not establish it; A3 reversed.

**33. Q: H5 came out in the opposite direction. Doesn't that mean cooperation protects against scarcity?**
*Tests:* resisting over-interpretation.
**A:** No.
1. The heavy world starts lower (0.573 vs 0.931) and is near the floor at Critical (0.087), so it cannot lose as many points.
2. As a proportion it keeps *less* (15% vs 21%).
3. With the comparison world at its own calibration, the normalised DiD is null.

No consistent sign means no claim.
*Follow-up:* "So why didn't you preregister a proportional scale?"
*Reason:* Honest answer: we did not anticipate floor effects of this size. The proportional analysis is post hoc and labelled; a future study should preregister it or use worlds matched at Abundant.

**34. Q: Your learners never converged. Why should anyone trust the results?**
*Tests:* the main limitation.
**A:** We claim nothing about converged behaviour. What holds:
- the scarcity ordering is identical at the final and best-validation checkpoints (W = 1), in all seeds and all variants;
- A6 shows that more steps do not change the trend.

Absolute levels may change with more training.
*Follow-up:* "Could the ordering flip with more training?"
*Reason:*
- We cannot rule it out formally.
- Against it: the oracle and the cooperative baseline show the same ordering, and the ordering held throughout training (Fig. 1).
- It would require scarce levels to gain much more than abundant ones.

**35. Q: IQL is far below your hand-designed policy. Is the learning result interesting at all?**
*Tests:* perspective.
**A:** Yes, as a study of *independent learners*. The research question is how scarcity affects what such learners learn, not whether IQL is the best method. The gap is itself a finding.
*Follow-up:* "What explains the gap?"
*Reason:* **[Interpretation]** Candidate explanations, none separately tested:
- non-convergence;
- the 5-feature observation (aliasing, no teammate identity) vs the full view the cooperative policy reads;
- the difficulty of same-step coordination for independent learners (high E1 at Abundant).

**36. Q: Isn't the cooperative baseline unfair, since it uses more information than IQL?**
*Tests:* a critical reading of the comparison.
**A:** Partly, yes. It reads the same *source* (AgentView) but in full: teammate identities, exact positions within 3 cells, and its own history. IQL sees a compressed 5-tuple. So the comparison is information-matched at the level of what is observable, not at the level of features.
*Follow-up:* "How would you fix it?"
*Reason:* Add a cooperative policy restricted to f1–f5, or give IQL richer features. Either separates "learning" from "information".

**37. Q: Your greedy baseline moves in lockstep. Isn't that a strawman?**
*Tests:* baseline critique.
**A:** It is a weak representative of selfishness. The group kept it as preregistered (D22) instead of improving it after seeing it, which would have been tuning a comparator. We therefore describe the comparison as "IQL vs uncoordinated identical agents".
*Follow-up:* "What would a fair selfish baseline be?"
*Reason:* Independent tie-breaking, or learners trained with λ_T = 0 (no team reward).

**38. Q: What is the alternative explanation for the H6 (solo vs joint) result?**
*Tests:* identifying confounds.
**A:** Distribution shift. Solo agents never saw a teammate, so every observation with f3 ≠ none is an unvisited Q-row (all zeros). At deployment they meet such observations constantly.
*Follow-up:* "How big could that effect be?"
*Reason:* Unknown, but potentially large, because teammates are often within 3 cells near the base. The design fix is dummy teammates during solo training.

**39. Q: A8 shows seeds with higher CR have higher RF. Why not call it mediation?**
*Tests:* correlation vs causation.
**A:**
- It is observational: seeds differ in many ways, and CR and RF are both outcomes of the same policy.
- In the joint model CR's CI includes 0.
- PSS and CR are collinear (VIF ≈ 8), and PSS tracks reward.
- 38 observations from 10 seeds is little data.

*Follow-up:* "What would causal evidence look like?"
*Reason:* Intervene on cooperation directly, e.g. force convergence behaviour at test time, and see whether RF under scarcity recovers.

**40. Q: Is the termination behaviour consistent with your report's narrative?**
*Tests:* whether you know the data better than the prose (§0.1).
**A:** Not fully.
- Table 8 shows that at Scarce and Critical about half of greedy test episodes end at the **horizon**, not by exhaustion. §9.2's sentence overstates exhaustion.
- During training (with exploration), 92–95% of Scarce and Critical episodes do end by exhaustion, which is what A6's step-count argument needs.

*Follow-up:* "Why would learned agents stop spending?"
*Reason:* We did not analyse it. The data show only that at least one agent kept ≥ 3 units until t = 105. A WAIT-heavy greedy policy is a plausible mechanism and an open question.

**41. Q: Why non-parametric tests? Wouldn't ANOVA be more powerful?**
*Tests:* methodological judgment.
**A:** With n = 10 we cannot check normality. RF is bounded and near the floor at Critical, and some metrics are undefined for some seeds. Rank tests are robust and were preregistered.
*Follow-up:* "What did you lose?"
*Reason:* Some power for small effects. That is why non-significant results are called inconclusive.

**42. Q: How do you know your metrics measure cooperation?**
*Tests:* construct validity.
**A:**
- Every metric has a fixed formula, a direction, and scripted test episodes with known answers.
- On the baselines, the cooperative policy scores higher than greedy where expected.
- 42/45 validity checks passed; the 3 failures are PSS tracking reward, which we report.

*Follow-up:* "Which metric would you drop?"
*Reason:* PSS as an indicator of cooperation. We kept it because it was preregistered, but never as independent evidence.

**43. Q: Would your conclusions change with pooled budgets?**
*Tests:* robustness.
**A:**
- Pooled raised RF modestly (+0.061 at Moderate, +0.042 at Critical).
- The scarcity trend was just as strong (W = 0.96, Page p ≈ 10⁻¹²).
- The per-agent constraint adds some difficulty but does not drive the main effect.

*Follow-up:* "Why does pooling help?"
*Reason:* Plausibly because the agent that must pay is never "the broke one". This is not tested further.

**44. Q: What single experiment would you add first?**
*Tests:* research judgment.
**A:** Longer training to the stability criterion, with more seeds. Non-convergence is the biggest threat to every conclusion.
*Follow-up:* "And second?"
*Reason:* A p_heavy dose-response at fixed ρ (0, 0.25, 0.5, 0.75), with a preregistered proportional contrast. That directly targets the unanswered H5 question.

**45. Q: How did you make sure the numbers in your report are right?**
*Tests:* reproducibility.
**A:**
- The report is generated from result files; 579 numbers are registered with their sources.
- `verify_results.py` (278 checks) recomputes the confirmatory statistics independently, re-runs the statistics script requiring byte-identical output, checks 72 claims, hashes the raw data, and confirms every report number appears in the document.
- The final ZIP was re-tested in a fresh folder.

*Follow-up:* "Does the verifier check your interpretation?"
*Reason:* No, only numbers. §0.1 is an example of a prose error that machine checks cannot catch.

---

# Reference section 1 — Mathematics and algorithms on one page

| Item | Definition |
|---|---|
| Budget | B₀ = round_half_up(ρ·B_ref); B_ref = 64; ρ ∈ {1.0, 0.5, 0.3, 0.2} |
| Horizon | H = ⌈T₉₀/0.7⌉ = ⌈73/0.7⌉ = 105 |
| Costs | move 1 (hazard 2), SEARCH 2, RESCUE 3, ASSIST 2, WAIT 0; c_min = 1; c_R = 3 |
| Dormant | B_t^i < c_min |
| Termination | all rescued → exhausted (max_i B_t^i < c_R) → t = H |
| Heavy rescue | ∃ i ≠ j on cell c with a^i = RESCUE and a^j = ASSIST at the same t |
| Reward | R_i = λ_I r_ind,i + λ_T r_team − λ_C c(a_i); λ = (1, 1, 0.02); r_ind: discovery 0.1, light 1.0, heavy rescuer 0.5, heavy assister 0.5 (split among co-actors); r_team = 1.0 per rescue |
| Observation | o = (f1..f5); \|O\| = 11·5·6·4·3 = 3,960; o = (((f1·5+f2)·6+f3)·4+f4)·3+f5 |
| Budget buckets | τ = (3, 16, 32); [0,3), [3,16), [16,32), [32,∞) |
| Q-update | Q(o,a) ← Q(o,a) + α[r + γ(1−done)·max_{a′∈M(o′)} Q(o′,a′) − Q(o,a)]; α = 0.1, γ = 0.98, Q₀ = 0 |
| ε schedule | ε(e) = 1 − 0.95·e/5,600 for e < 5,600, else 0.05 |
| Churn | mean over agents of the share of validation-visited o whose argmax_a Q changed since the last checkpoint |
| Stable | churn < 0.05 and range of validation RF over the last 3 checkpoints < 0.02 |
| RF | rescued / V (V = 6), averaged over 100 test episodes per seed |
| EAR | heavy rescues / ASSIST actions |
| RSR | SEARCHes with ≥ 50% of the footprint already covered / SEARCHes |
| TDI | 1 − mean_{i<j} \|U_i ∩ U_j\| / \|U_i ∪ U_j\| |
| PSS | Σ(c_R + c_A·heavy) over rescues / total spent |
| Gini | Σ_i Σ_j \|x_i − x_j\| / (2n²·mean x) |
| CR | \|cooperative non-WAIT actions\| / \|non-WAIT actions\| |
| DiD (A3) | [RF(Ab) − RF(Cr)]_heavy − [RF(Ab) − RF(Cr)]_all-light, per seed |
| Kendall's W | χ²_F / (n(k−1)) |
| Holm | sort p ascending; p̃_(i) = max_{j≤i} min(1, (m−j+1)·p_(j)) |
| δ₁ | (#above − #below) / n |
| Rank-biserial r | (W⁺ − W⁻) / (W⁺ + W⁻) |

**Algorithm summary (IQL training run).**
1. Q ← 0.
2. For each episode e: draw a map from the seed's order, set ε(e), reset, and play until done. At each step:
   - act ε-greedily over valid actions;
   - step the environment;
   - apply the TD update for each non-dormant agent.
3. Every 500 episodes: greedy validation on 50 maps; log RF, metrics, churn and TD error; keep the best-validation Q.
4. Save the final Q (primary) and the best-validation Q.

# Reference section 2 — Concepts to master before presenting

Tick each when you can explain it **without notes** and **connect it to our code or results**.

**Problem and environment**
- [ ] Partially observed Markov game; state vs observation
- [ ] Heavy vs light victims; why same-step simultaneity makes cooperation *necessary*
- [ ] Costs, masks, dormancy, the three terminations and their order
- [ ] The reward formula, and why a selfish agent prefers light victims
- [ ] f1–f5, the encoding, budget buckets (3/16/32), bucket 0's meaning, pooled-mode P4
- [ ] Stale memory: why it can misdirect walking but never cause an illegal RESCUE

**Learning**
- [ ] Q-values, the TD error, the update rule, α and γ
- [ ] ε-greedy and the schedule; greedy evaluation; CRN tie-breaks
- [ ] Independent learning and non-stationarity; churn; the stability criterion
- [ ] Training / validation / test / shifted / calibration sets; why final vs best-validation

**Design and calibration**
- [ ] H = ⌈T₉₀/0.7⌉; B_ref = 90th-percentile consumption; why Critical = 0.2; L ≥ 10 vs 8 × 8
- [ ] The baselines and their weaknesses (greedy lockstep; cooperative uses the full view); oracle as a reference
- [ ] The seven cooperation metrics; CR in detail; PSS's caveat; pooling of ratios

**Statistics**
- [ ] Unit = seed; pseudo-replication; paired designs via CRN
- [ ] Friedman, Kendall's W, Page's L, Wilcoxon (exact p floor 0.002), rank-biserial, δ₁
- [ ] Holm (why 0.0117 / 0.0234 / 0.0078 recur); bootstrap and cluster bootstrap
- [ ] Confirmatory vs secondary vs exploratory vs post hoc

**Results and attribution**
- [ ] H0–H6 outcomes with their key numbers
- [ ] Why H5's reversal is not "cooperation protects"; floor effects; scale and calibration dependence
- [ ] A4's distribution-shift confound; A1's dependence caveat; A8 is association
- [ ] A6 equal steps; transfer specialisation; shifted maps; pooled; alternate configuration
- [ ] The §0 discrepancies, especially the termination sentence (0.1)

**Integrity**
- [ ] Preregistration and the deviations (C1–C6, N1–N5)
- [ ] How the report numbers are generated and verified (V1–V7)
- [ ] What the quick run proves and does not prove
