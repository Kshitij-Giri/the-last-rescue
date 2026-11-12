# Viva guide: The Last Rescue (Group 14)

This guide is for preparation. Every number below is copied from `report/report.pdf`, where each number is traced to its source in `docs/report_numbers.yaml`. If a number here ever disagrees with the report, the report wins.

Contents:
1. The 2-minute pitch
2. Numbers to know by heart
3. Methodology in plain words
4. Results and how to say them
5. Limitations and how to own them
6. Likely questions with model answers
7. Never say this
8. Live demonstration
9. Self-test

---

## 1. The 2-minute pitch

**The question.** How does resource scarcity affect whether independently learning agents learn to cooperate in a rescue task? And is the effect of scarcity on performance *because of* cooperation?

**The game.**
- A 10 × 10 grid, three agents starting at one base and six victims.
- Half of the victims are **heavy**. A heavy victim is rescued only when one agent plays RESCUE and a different agent plays ASSIST on its cell **in the same step**, so cooperation is physically required.
- Every action costs units from a **private budget** that cannot be refilled or shared.
- Scarcity ρ is the fraction of a *calibrated just-enough budget* B_ref = 64. Four levels: Abundant 1.0, Moderate 0.5, Scarce 0.3, Critical 0.2, giving budgets of 64, 32, 19 and 13.

**The method.**
- Independent tabular Q-learning (IQL), 8,000 episodes per run, 10 training seeds per condition.
- 350 training runs, evaluated on 100 frozen test maps.
- Compared with a random, a greedy and a hand-designed cooperative baseline, plus a full-information **oracle reference** (not a learner).
- Everything was preregistered and frozen before the first learning run.

**The answer.**
- Scarcity sharply reduces rescue performance: RF 0.573 → 0.087, the same order in all 10 seeds.
- It wipes out joint rescues: the cooperation rate falls from 0.180 to 0.023, and the heavy-victim share from 0.422 to 0.016.
- The learned teams do have co-adapted conventions: mixing teammates from other seeds hurts, and solo-trained agents fail.
- But the preregistered test of whether scarcity hurts *more when cooperation is necessary* (H5) came out significant in the **opposite** direction, and its sign depends on the scale and the calibration. So we do **not** claim that scarcity specifically destroys cooperation-dependent rescues.
- No run converged. All statements are "after 8,000 episodes".

---

## 2. Numbers to know by heart

| What | Value |
|---|---|
| Calibration | H = 105 (T90 = 73), B_ref = 64; b0 = 64 / 32 / 19 / 13 |
| Learned RF, Abundant → Critical | 0.573, 0.344, 0.180, 0.087 |
| H1 | Friedman χ²(3) = 30.0, p = 1.4 × 10⁻⁶, Kendall's W = 1.00; all 6 pairwise tests have Holm p = 0.0117 |
| Heavy share / light share | 0.422 → 0.016 / 0.723 → 0.159 |
| CR (cooperation rate) | 0.180 → 0.023 (H2 Holm p = 1.7 × 10⁻⁴) |
| H2 not significant | EAR (p = 0.41, n = 8), TDI (0.59), consumption Gini (0.90) |
| RSR_other | Non-monotone; peaks at Scarce (0.476) |
| Baselines (RF, Abundant / Critical) | random 0.063 / 0.005; greedy 0.465 / 0.075; cooperative 0.985 / 0.233; oracle reference 1.000 / 0.403 |
| H3, IQL vs greedy at Critical | Not significant: Holm p = 0.0742 (7 seeds above, 2 below, 1 tie) |
| H4 (A1, mismatched teammates) | Drops 0.1335 / 0.090 / 0.043 / 0.017; significant except at Critical (Holm p = 0.084) |
| H6 (A4, joint vs solo) | 0.471 / 0.305 / 0.165 / 0.081, Holm p = 0.0078 at every level (distribution-shift caveat) |
| H5 (A3 DiD, primary) | −0.248 [−0.322, −0.171]; 0/10 seeds positive; p = 0.002 |
| A3, retained fraction at Critical | 15% (heavy-victim world) vs 21% (all-light world); post hoc log DiD +0.331 [0.113, 0.575] |
| A3, own calibration, oracle-normalised | +0.052 [−0.029, 0.147] (CI includes 0) |
| A5 | 5 of 350 runs stable; 0 of 40 main runs |
| A8 | R² 0.927 (levels only) → 0.978; joint model: only PSS's CI excludes 0; VIF ≈ 8 |
| Pilot | Validation RF 0.622 vs random 0.066, 5/5 seeds, p = 0.031; no setting changed |
| Compute | 350 runs, 4.48 CPU-hours; 264 tests; verifier passes all checks (log: `results/logs/verify_results.txt`) |

---

## 3. Methodology in plain words

### The game (Section 3 of the report)
- **Partially observed Markov game.** Agents act at the same time. Each sees only its own view, never the full state.
- **Termination.** Checked in this order every step: all rescued; then *exhausted*, meaning nobody can afford a RESCUE (max budget < 3); then the horizon t = H. After exhaustion no action can change the result, which makes "the mission is over" exact.
- **Dormant agent.** An agent with budget < 1 can only WAIT and makes no learning update.
- **Feasibility.** An instance is feasible if at least one victim can be rescued within budget and horizon (an exact check on the known map). Test maps infeasible at Critical were regenerated before the freeze.
- **Reward.** R = λI·individual + λT·team − λC·cost (1, 1, 0.02).
  - A heavy rescue pays its two participants 0.5 each individually; a light rescue pays its rescuer 1.0. So a *selfish* agent prefers lights.
  - The team term pays every agent 1 per rescue by anyone.
- **Observation.** A 5-feature tuple with 3,960 values:
  - f1: nearest victim the agent believes unrescued;
  - f2: direction to unexplored cells;
  - f3: nearest visible teammate;
  - f4: budget bucket;
  - f5: time third.

  Budget buckets use fixed thresholds 3 / 16 / 32. Bucket 0 means exactly "cannot pay for a RESCUE", and the same bucket means the same absolute amount at every ρ.
- **Masking.** Masks are computed only from the agent's own information, and they are the same for learners and baselines. An invalid action raises an error, so no policy can cheat with hidden state.

### Why calibrate (review point R3)
"30 units" means different things on different maps. B_ref is the 90th percentile of the per-agent consumption of the cooperative baseline with unlimited budget. H = ⌈T90/0.7⌉ so that time is not the binding limit.

The ρ levels were chosen so that the cooperative baseline reaches about 1.0 / 0.70 / 0.40 / 0.10–0.15 RF, subject to the oracle rescuing at least one victim in ≥ 95% of instances at Critical. That constraint pushed Critical from 0.1 (feasible in only 33% of instances) to 0.2, so Critical's cooperative RF is 0.220, above its target band (note N1).

A sensitivity check on 4 other map configurations showed that ρ means the same thing for L ≥ 10 (spread ≤ 0.079) but not on 8 × 8 maps. The analytic budget formula tracks consumption (r = 0.998) but predicts only about half of it.

### IQL and non-stationarity (review point R2)
Each agent updates its own Q-table:
Q ← Q + α[r + γ·max over valid a′ of Q(o′, a′) − Q].
- α = 0.1, γ = 0.98.
- ε decays from 1.0 to 0.05 over the first 70% of episodes.

Teammates learn at the same time, so from each agent's view the environment changes. The single-agent convergence guarantee (Watkins & Dayan) no longer applies. We **measure** this (churn, TD error, a stability criterion) instead of assuming convergence.

### Baselines and oracle
- **Random:** a uniformly random valid action.
- **Greedy:** walks to the nearest affordable victim and never ASSISTs. All three agents run the identical rule, so they move in lockstep. Read it as "uncoordinated identical agents", not "the best selfish policy" (decision D22).
- **Cooperative:** sectors, help call, role convention, a bounded wait of 2L steps, and a search convention.
- **Oracle reference:** a centralised, full-information greedy-insertion planner. On small instances it equals the exhaustive optimum in 297 of 300 cases. It is never tested and never called a learner.

### Cooperation metrics (review point R1)
Each metric is computed from action logs, never from reward:
- **C1 EAR:** heavy rescues per ASSIST.
- **C2 RSR / RSR_other:** redundant searches.
- **C3 TDI:** territory overlap.
- **C4a PSS:** productive spend share. It tracks reward, so it is not independent evidence.
- **C4b Gini:** load balance.
- **C5 CR:** share of non-WAIT actions that are part of a heavy rescue, including converging moves.

CR is 0 by construction when there are no heavy victims. All metrics were validated on scripted episodes (42 of 45 checks passed; the 3 failures are PSS's correlation with reward).

### Statistics (preregistration §5)
- **Unit of analysis = training seed.** Test episodes are repeated measurements of one trained team, so using them as n would be pseudo-replication.
- **Paired design.** Seed s has the same training-map order and exploration stream in every condition. So: Friedman across the 4 levels (+ Kendall's W), Page's L for the ordered trend (two-sided), and Wilcoxon signed-rank for two conditions (+ rank-biserial r).
- **One-sample design.** Greedy, cooperative and oracle are deterministic: one number per level. IQL's 10 seed values are tested against that constant.
- **Holm** correction within each preregistered family. **Bootstrap** percentile CIs over seeds (10,000 resamples).
- With n = 10, the smallest possible two-sided Wilcoxon p is 2/1024 ≈ 0.002. That is why so many p-values equal 0.0117 after Holm across 6 (0.00195 × 6).
- **Ties:** differences below 10⁻⁹ are treated as exact zeros (C6). This mattered once: seed 8 tied greedy exactly at Critical.

### Attribution design (review point R2)
- ρ is manipulated with everything else fixed, so "scarcity lowers RF" is causal for this environment and procedure.
- "Through cooperation" needs interventions:
  - **A1:** swap teammates between seeds.
  - **A2:** replace one agent at test time.
  - **A3:** a world where cooperation is never needed.
  - **A4:** train agents alone.
- **A5 / A6** check the alternatives: non-stationarity, and fewer training steps.
- **A8** is the observational regression, labelled as association.

---

## 4. Results and how to say them

| Finding | Say | Label |
|---|---|---|
| H0 | "IQL learns: 10/10 seeds beat random at Abundant." | Confirmatory |
| H1 | "Scarcity causes a large monotone drop in rescues, identical ordering in every seed." | Confirmatory |
| H2 | "Joint behaviour collapses (CR, heavy rescues). Territory division, load balance and assist efficiency show no significant change, which is inconclusive with 10 seeds." | Confirmatory |
| H3 | "IQL beats random everywhere and greedy at three levels, not at Critical; it is below the cooperative baseline everywhere." | Confirmatory |
| H4 | "Mismatched teammates lower RF by 23–26% at three levels: conventions are co-adapted." | Confirmatory |
| H6 | "Joint training matters a lot, but part of the gap is distribution shift." | Confirmatory, with caveat |
| H5 | "Significant in the opposite direction on the absolute scale; scale- and calibration-dependent; we make no cooperation-bottleneck claim." | Confirmatory, negative |
| A6 | "Equal steps change Moderate a little; the trend is unchanged." | Exploratory |
| A5 | "Policies have not converged; the scarcity order still holds at the best-validation checkpoint." | Exploratory / secondary |
| A8 | "Seeds that cooperate more rescue more within a level: association only." | Exploratory |
| Exp5 | "Policies are specialised to their training budget; Abundant-trained teams collapse at Critical (0.010)." | Exploratory |
| Pooled / alternate / shifted | "The trend survives every variant." | Exploratory |

**Why the A3 result is negative but not a contradiction.**
- The all-light world starts high (0.931) and the heavy world starts low (0.573) and is near the floor at Critical (0.087). In points, the all-light world loses more; as a fraction, the heavy world keeps less (15% vs 21%).
- An additive DiD is pulled negative by this scale effect. The proportional (post hoc) version is positive.
- With the comparison world at its own calibration, the normalised DiD is null.
- Three readings, no consistent sign, so no claim.

---

## 5. Limitations and how to own them

1. **No convergence.** "Our claims are about policies after a fixed budget of 8,000 episodes. We measured non-stationarity rather than assume convergence. 0/40 main runs met our preregistered stability criterion, so the stable-only analysis could not be computed. We report that rather than redefine 'stable'."
2. **Ten seeds.** "We detect large consistent effects. Our non-significant results are inconclusive, not evidence of no effect."
3. **A3 depends on scale and calibration.** See Section 4 above.
4. **A4 distribution shift.** "Solo agents never saw a teammate, so at deployment they face observations they never visited."
5. **Greedy lockstep.** "A deliberate group decision (D22) to keep the baseline as preregistered; we interpret it accordingly."
6. **PSS tracks reward.** It is kept in H2 because it was preregistered, but never used as independent evidence.
7. **Calibration.** Critical sits above its target band; ρ is not comparable on 8 × 8 maps.
8. **Time-limited Abundant.** Most Abundant episodes end at the horizon (98.5% on 12 × 12 maps).
9. **Scope.** One environment, 3 agents, tabular IQL, no communication.

---

## 6. Likely questions with model answers

Owner tags follow `docs/module_owners.md`: **K** = Kshitij (formulation, integration), **P** = Panjari (environment), **S** = Snehal (rewards, metrics, baselines), **M** = Kshitish (RL, evaluation, ablations). Everyone should be able to answer every question.

### Formulation and environment
1. **Why per-agent budgets instead of one pool? (K/P)** Per-agent budgets create an allocation problem: the agent that needs to ASSIST may be the one that is broke. The pooled ablation tests whether conclusions depend on this. Pooled raises RF a little (Moderate +0.061, Critical +0.042), and the trend is equally strong.
2. **What exactly happens at exhaustion? (P)** The episode ends as soon as max_i B_i < c_R = 3: nobody can RESCUE, so the outcome is fixed. Agents with 1–2 units could still SEARCH, but that cannot change RF. This is documented in D2.
3. **Why mask invalid actions instead of penalising them? (P)** Penalties make learners waste samples learning the rules, and baselines would need the same penalties. Masks define feasibility exactly and identically for all policies, and they use only the agent's own information.
4. **Can an agent RESCUE a victim it wrongly remembers? (P)** No. Its own cell is observed every step, so RESCUE is offered only on a real unrescued victim. Stale memory affects navigation only and is corrected when the cell is seen.
5. **Why does the observation have only 3,960 states? (M)** Tabular IQL needs a small table. The tuple keeps what matters for the decisions: nearest victim, exploration direction, teammate nearby, budget bucket and time. Directions are cheapest-path first moves, so walls are handled implicitly.
6. **Why are budget buckets relative to B_ref, not to the agent's own start budget? (K)** So that a bucket means the same absolute amount at every ρ. Otherwise "bucket 3" at Critical would mean 13 units and at Abundant 64, and the transfer matrix would be meaningless.
7. **Why is the reward designed so that a selfish agent prefers lights? (S)** Deliberately, to create individual-versus-collective tension for Exp4. The team term still makes every rescue valuable to everyone. In practice the best agent's return and the team return stayed aligned (Spearman ≈ 0.95).

### Calibration
8. **How did you choose B_ref? (K)** The 90th percentile of the cooperative baseline's per-agent consumption with unlimited budget on 200 calibration maps. The rules were hashed before the first calibration run.
9. **Why is Critical 0.2 and not 0.1? (K)** At ρ = 0.1 only 33% of instances are solvable at all. The pre-stated rule required ≥ 95%, so Critical moved to 0.2 (99% solvable). We did not refine the grid afterwards (N1).
10. **Does ρ mean the same on any map? (K)** For L ≥ 10, yes within 0.079 RF. On 8 × 8 maps, no: fixed costs are a bigger share of small budgets. We state this limit.
11. **Why did the analytic formula underestimate? (K)** It ignores detours, waiting for a partner and revisits. It tracks consumption (r = 0.998) but at about half the level, so we used the empirical value.

### Learning
12. **Why IQL and not a centralised method? (M)** The proposal asked how *independent* learners cope. IQL is the simplest MARL baseline and makes non-stationarity explicit. Other methods are listed as scope limits.
13. **What is non-stationarity here, concretely? (M)** Agent i's transition probabilities depend on teammates' policies, which change every update. The target for its Q-values moves. We measured churn (5–13% at the end) and TD error (still rising).
14. **Did training converge? (M)** No. 5/350 runs met the preregistered stability criterion, and 0 of the 40 main runs. We say "after 8,000 episodes" everywhere.
15. **Then why trust the results? (M/K)** The ordering by scarcity is identical at the final and the best-validation checkpoint (both W = 1), in every seed and in every robustness variant. Absolute levels may change with more training; we do not claim they would not.
16. **Why 8,000 episodes? (M)** Fixed before the experiments by the pilot rule on validation data only. The rise in the last quarter was 0.018 < 0.02, so the rule did not ask for more. Nothing was tuned on test data.
17. **Why is the horizon treated as terminal? (M)** For consistency with the time feature; it is documented. It ignores value beyond H.
18. **What does the quick mode show? (M)** That every stage runs end to end in about 3 minutes. Its numbers are not results: 3 seeds cannot pass the gate.

### Metrics
19. **Why not measure cooperation with reward? (S)** A team of selfish agents rescuing lights earns team reward with zero cooperation. Our metrics are behavioural, from logs.
20. **What counts as a cooperative action in CR? (S)** The effective RESCUE and ASSIST of a heavy rescue, plus the participants' moves that converge on the victim in the 2L steps before. Light rescues never count.
21. **Why keep PSS if it tracks reward? (S)** It was preregistered. Dropping it after seeing data would be a deviation. We report it with its caveat (D22).
22. **Why does abandonment (E1) fall under scarcity? Is that better coordination? (S)** Most likely not. Agents rarely meet at heavy victims at all under scarcity, so there is less to abandon.
23. **Why is RSR_other non-monotone? (S)** It peaks at Scarce (0.476). At Critical agents hardly search, so there is little left to be redundant.

### Statistics
24. **What is your unit of analysis and why? (K)** The training seed. Test episodes from one trained team are not independent replicates.
25. **Why Friedman and not ANOVA? (K)** Paired, small n, and RF is bounded and not normal. Friedman is the rank-based repeated-measures test, and Page's L adds the ordered alternative.
26. **Why are so many Holm p-values exactly 0.0117 or 0.0234? (K)** With 10 seeds all in one direction, the exact Wilcoxon p is 2/1024 = 0.00195. Holm multiplies the smallest by the family size: 0.00195 × 6 = 0.0117 and × 12 = 0.0234.
27. **H3 compares against a constant: why one-sample? (K)** Greedy, cooperative and oracle are deterministic, with one value per level. There is no seed variation to pair.
28. **What is Kendall's W = 1? (K)** Every seed ranks the four levels in exactly the same order.
29. **Why bootstrap CIs? (K)** No distributional assumption. We resample seeds, keeping each seed's conditions together for paired contrasts.
30. **What was the floating-point tie issue? (K)** Seed 8 rescued exactly as many victims as greedy at Critical, but the floating means differed by about 10⁻¹⁷, so the test either kept or dropped the seed by accident. We snapped |d| < 10⁻⁹ to zero (C6). The p-value moved from 0.084 to 0.0742; still not significant.

### Attribution
31. **How do you know the scarcity effect is due to cooperation? (K)** We don't claim it fully. A1 and A4 show learned teams depend on co-adapted conventions. A3 shows a large scarcity effect even when cooperation is never needed, and the cooperation-bottleneck test went the other way. A8 is only association.
32. **Explain the H5 result. (K)** See Section 4. In points the all-light world loses more; as a fraction the heavy world keeps less; on own calibration it is null. No claim.
33. **Isn't the log-scale analysis p-hacking? (K)** It was added after seeing H5 and is labelled post hoc everywhere (C4). It never replaces the preregistered result; it explains why the additive result should not be over-read. We also found and fixed a sign error in it (C5) before reporting.
34. **Why is the solo comparison (A4) confounded? (M)** Solo agents never observed a teammate, so f3 was always "none". At deployment they meet unseen observations with zero Q-values.
35. **Why does a WAIT-only teammate hurt more than a random one? (M)** Plausibly because a random teammate sometimes ASSISTs by chance. Part of any A2 drop is just losing a third of the team's search and budget.
36. **Does A8 show cooperation causes performance? (S/K)** No. It is association: seeds differ in many ways, CR and PSS are collinear (VIF ≈ 8), and PSS tracks reward.
37. **Couldn't scarce levels simply learn less because they see fewer steps? (M)** That is what A6 tests. With equal environment steps, Moderate improves (+0.078) but the trend is unchanged (Page p = 8.0 × 10⁻¹⁰).

### Integrity and process
38. **What changed after the preregistration? (K)** Six post-freeze entries (C1–C6) and notes N2–N4. None changed a hypothesis, parameter, test or test instance. C1/C3 fixed mechanics before results; C4 is the labelled post hoc analysis; C5/C6 are bug fixes; C2 is a logging bug.
39. **How do we know the numbers in the report are right? (K)** The report text is generated from the result files. Every number is registered with its source (579 entries), and `verify_results.py` re-reads each one and checks that it appears in the .docx. The verifier also recomputes the confirmatory tests independently and requires the statistics script to reproduce byte-identical outputs.
40. **Did you rerun anything to get better results? (all)** No. All 350 runs and all seeds are reported, including unstable runs, and nothing was tuned on test data.
41. **How was AI used? (all)** As allowed by the course: to help implement, check and write, under the group's decisions at every phase gate. Each member must be able to explain their modules (`docs/module_owners.md`).

---

## 7. Never say this

- "The agents converged" / "optimal policy". Say: **after 8,000 episodes**.
- "Scarcity destroys cooperation-dependent rescues more" / "cooperation causes ...". H5 does not support it, and A8 is association.
- "The oracle" as if it were a method we trained. Say: **oracle reference (full information, not a learner)**.
- "IQL beats selfish agents". Say: beats **uncoordinated identical agents** at three of four levels.
- "No effect" for EAR, TDI or Gini. Say: **not significant; inconclusive with 10 seeds**.
- Any number not in the report.

---

## 8. Live demonstration

```bash
python -m pytest -q                         # 264 tests
python scripts/run_all.py --quick           # whole pipeline at reduced scale, about 3 min on 2 cores
python scripts/verify_results.py            # recompute statistics, check every report number
python scripts/make_replays.py              # or open results/replays/phase6_*.txt to show behaviour
```

Good replays to show: a heavy rescue at Abundant (two agents converge, then RESCUE and ASSIST on the same step), and an exhausted Critical episode. Use `results/replays/phase6_index.csv`.

---

## 9. Self-test (answer without notes)

1. Why is H = ⌈T90/0.7⌉ and not T90?
2. What does f4 = 0 mean in the per-agent setting, and why is it different in the pooled setting?
3. Why is the training seed the unit of analysis?
4. Give the three readings of A3 and why they disagree.
5. Why does H3 use a one-sample test?
6. What would change your conclusion about convergence?
7. What exactly is in a heavy rescue, and which actions does CR count?
8. What is the difference between C4 and C5 in the deviations log?
