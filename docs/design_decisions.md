# Design decisions log

Format: Decision / Alternatives / Why / Risk. Review point addressed in brackets.

D1 Per-agent budgets (main), pooled budget (ablation) [R1]
- Alternatives: global pool only; transferable budgets.
- Why: per-agent budgets create a team allocation problem (who spends on what), and the pooled ablation shows whether conclusions depend on this choice.
- Risk: pooled setting needs a payment-order rule; we rotate priority by t to avoid favouring agent 1.
- Clarification (Phase 1, P4): in the pooled setting the mask, payment and exhaustion use the actual pool B_team; the observation
  feature f4 uses the per-capita share floor(B_team/n). Pooled f4 = 0 does not mean the team cannot afford RESCUE.
  Implemented as two separate fields of the agent's view (`spendable` vs `budget_feature_value`) and tested.

D2 Exhaustion = "nobody can RESCUE any more" (max_i B_i < c_R) [R1]
- Alternatives: end when all budgets are 0; never end before H.
- Why: after this point no action can change the primary outcome, so continuing only wastes compute and dilutes per-step metrics.
- Risk: an agent with 1–2 units could still SEARCH; this affects coverage only, not rescues. Documented.

D3 Action masking from agent-observable preconditions, identical for all policies [R1]
- Alternatives: allow invalid actions with a penalty.
- Why: penalties make learners spend samples learning rules; masking defines feasibility exactly and keeps baselines comparable.
- Risk: masking ASSIST unless a teammate is co-located slightly helps learners; it applies equally to every method.
- v0.2: the mask is computed only from the agent's own observation (spec §1.3a); see D17.

D4 HEAVY victims need RESCUE + simultaneous ASSIST by a different agent; p_heavy is a parameter [R2]
- Alternatives: "two agents on cell" without role split; time-extended joint lift.
- Why: makes cooperation causally necessary for part of the outcome, and p_heavy = 0 gives a control world.
- Risk: simultaneous coordination is hard for IQL; may produce few heavy rescues. That would itself be a reported result; the pilot checks.

D5 Static map known a priori; victims and teammates partially observed [R1]
- Alternatives: also hide terrain.
- Why: keeps the tabular observation to 3,960 states and focuses partial observability on the research question.
- Risk: weaker partial observability than the draft implied; stated in Limitations.

D6 Observation = 5-feature discrete tuple with path-based directions [R1]
- Alternatives: raw local window (too many states for tabular), blocked-direction mask.
- Why: |O×A| = 31,680; directions from Dijkstra first steps avoid getting stuck at walls without a blocked-direction feature.
- Risk: aliasing (different situations look identical); probed by the learnability pilot.

D7 Budget buckets relative to B_ref, not to the agent's own starting budget [R3]
- Alternatives: fraction of own initial budget.
- Why: a bucket means the same amount of resource at every ρ, so cross-ρ transfer is interpretable.
- Risk: at Critical, agents start in a low bucket; that is intended.
- v0.2 (precise boundaries): integer thresholds τ1 = c_R = 3, τ2 = max(τ1+1, ceil(0.25·B_ref)), τ3 = max(τ2+1, ceil(0.5·B_ref));
  half-open buckets [0,τ1), [τ1,τ2), [τ2,τ3), [τ3,∞). Alternatives: real-valued cut points (ambiguous at boundaries and can
  overlap or invert when 0.25·B_ref ≤ c_R). Why: on integer budgets the rule is mutually exclusive, exhaustive and never has an
  empty or reversed interval; it equals the intended cut points whenever B_ref ≥ 16. Risk: none beyond bucket coarseness.

D8 Reward: individual credit split for heavy victims (0.5/0.5) vs 1.0 for light; equal team value [R2]
- Alternatives: heavy victims worth more.
- Why: equal value per life; built-in individual-vs-team tension for Exp4.
- Risk: learners may ignore heavies under scarcity; the team term (λ_T) counterweights it and this is a measurable result.

D9 Cooperation metrics are behavioural and computed from logs; never from reward [R1]
- Alternatives: team-reward proxy.
- Why: requested by the review; avoids tautology.
- Risk: each metric has blind spots (e.g., TDI depends on episode length); hence five metrics plus validation.

D10 Oracle = full-information centralized greedy-insertion planner, called "oracle reference"; plus a provable loose upper bound [R1]
- Alternatives: exact optimum (intractable), mixed-integer program.
- Why: honesty about what is and is not optimal.
- Risk: learners could in principle exceed the oracle on some instances; reported if it happens.

D11 Calibrate H, then B_ref from the cooperative baseline; ρ levels from the cooperative baseline and oracle [R3]
- Alternatives: guess values; calibrate from RL agents.
- Why: ties ρ to a reproducible definition ("fraction of just-enough budget") and avoids circularity.
- Risk: B_ref depends on the quality of the cooperative baseline; the analytic formula and sensitivity grid check it.

D12 n = 3 agents
- Alternatives: 2 or 4.
- Why: 2 makes the agent ablation trivial; 4 increases non-stationarity and compute.
- Risk: results may not extend to larger teams (limitation).

D13 Training on a fixed pool of 1,000 maps, disjoint seed ranges for validation/test/shifted test [R2]
- Why: no test leakage; common random numbers across conditions.

D14 Primary policy = final checkpoint; best-on-validation as sensitivity [R2]
- Why: avoids selection bias; any selection uses validation only.

D15 Unit of analysis = training seed; 10 seeds; paired non-parametric tests with Holm, bootstrap CIs [R2]
- Alternatives: per-episode tests (pseudo-replication); unpaired Kruskal–Wallis / Mann–Whitney (v0.1).
- Why: seeds are the independent replicates; test episodes are repeated measurements of one trained team. Because seed s uses
  the same map order, exploration stream and test instances in every condition, conditions are matched by seed, so paired
  tests (Friedman, Page's L, Wilcoxon signed-rank, paired bootstrap) remove between-seed variation and are the correct choice.
  IQL vs deterministic baselines is a one-sample comparison against a constant. Unpaired tests are kept as secondary only.
- Risk: matching by seed produces correlation only if the shared streams actually make outcomes similar; if not, paired tests lose
  little. Mismatched teams (A1) share agents across teams, so their paired differences are not perfectly independent (stated).

D16 No communication in core; optional extension is a cost-bearing BEACON [R2]
- Why: keeps the scarcity effect uncontaminated; the extension adds one action only after the core is verified.

D17 Policies and masks use only observed information; stale memory affects navigation only [R1, R2]
- Alternatives: (a) mask RESCUE using ground-truth victim status anywhere (leaks hidden information); (b) let an agent RESCUE an
  empty cell and charge it (never needed: the own cell is always observed).
- Why: o_t and m_t are built from the agent's own memory and current radius-1 view, which always includes its own cell and is
  refreshed from the true post-transition state every step. So a RESCUE on an already-rescued victim can never be offered;
  stale memory only wastes travel until the cell is observed again, when memory is corrected. Hidden state is used only by the
  environment (resolution, reward), the oracle (by design) and offline analysis. Every action is re-validated against the issued
  mask; a violation raises InvalidActionError.
- Risk: the reward's "first sighting by the team" uses hidden information; this is legitimate environment feedback, not a policy
  input, and is documented. Stale travel is logged (`stale_correction`, offline `stale_travel`) so its cost is visible.

D18 Phase 1 implementation choices (no change to the approved design)
- Extra module `mapgen.py` (map/instance generation, path tables, feasibility). Alternative: put it in env.py.
  Why: keeps env.py focused on transitions; tables are reused by baselines/oracle later. Risk: none.
- Victims at Chebyshev distance >= 2 from the base (spec said ">= 2 steps"). Why: Chebyshev >= 2 implies >= 2 steps and
  also guarantees no victim is visible at t = 0 (radius-1 view), so discovery is always earned. Recorded as P5.
- Instance seed = split base + 100*index + attempt. Why: "regenerate with the next seed" must not collide with the
  next instance's seed. Ranges stay disjoint for <= 10,000 instances per split (tested). Recorded as P5.
- Rounding: round-half-up everywhere (B_0 = round(rho*B_ref), counts of walls/victims/heavies). Python's round() is
  banker's rounding and would make results depend on parity. Tested (e.g. 0.5*5 -> 3).
- Deterministic tie-breaks: cheapest-path first step prefers UP, DOWN, LEFT, RIGHT in that order; f1 nearest victim by
  (cost, steps, cell index); f2 nearest unobserved cell by (cost, cell index); f3 nearest teammate by (Manhattan, agent
  id), dominant axis with ties -> vertical; teammate radius r_tm is inclusive (Chebyshev <= 3). All tested.
- Walls are placed one candidate at a time and kept only if all non-wall cells stay connected, so generation always
  terminates without rejection sampling; the achieved wall count is recorded in the instance metadata (all tested
  configurations reached the target).
- Test/scenario hooks `start_positions` and `budgets` in `reset()` exist only for hand-written scripted episodes;
  experiments always start all agents on the base with equal budgets.
- A map with no waiting victims ends at reset with `all_rescued` (vacuously true); every scenario map has a victim.
- A step that both rescues the last victim and exhausts the budget is labelled `all_rescued` (termination order).
- In pooled mode one shared pool is logged; "dormant" applies to all agents together when the pool < c_min.

D19 Baseline implementation (Phase 2) [R2]
- Interface: each baseline agent is a controller that receives only its own AgentView + mask each step and a
  StaticContext (map tables, costs, n, H, own index). It never receives the environment. Views carry a COPY of the
  agent's memory and a read-only observed mask, so a policy cannot alter ground truth (tested).
- Random: uniform over valid actions, seeded per (episode seed, agent).
- Greedy: targets only affordable victims (d + c_R <= budget); LIGHT before HEAVY at equal cost; at most one RESCUE
  attempt per HEAVY victim (otherwise it would burn its whole budget retrying - a strawman, not a myopic policy).
  Alternatives: endless retries; random tie-breaking per agent. Risk / finding F1: identical deterministic agents on one
  start cell act in lockstep (verified: identical positions at every step), so greedy teams triple-search and
  triple-rescue. This is the honest behaviour of uncoordinated identical agents, but it makes greedy weak; an
  agent-specific tie-break would desynchronise them. Kept as specified; flagged for the group to decide (Phase 2 report).
- Cooperative: priority rules 1-7 in baselines.py (joint-rescue role convention, light rescue, wait <= W = 2L at a heavy
  victim only if it can afford either role, help signal = teammate seen on the same cell in 3 consecutive own views,
  false-alarm memory, affordable light then heavy targets, sector-first exploration). Sectors: deterministic k-means with
  farthest-point seeding, numbered by centroid order. Exploration uses exactly greedy's SEARCH rule so that greedy and
  cooperative differ only in the cooperation conventions.
- Search convention (added after the validity check, P7): a cooperative agent does not SEARCH while a lower-index
  teammate stands on its cell. Why: 50 of its 62 redundant searches in the first validity run were all three agents
  searching the base simultaneously at t = 0, contradicting the baseline's own design intent. No learned policy existed,
  so this cannot be tuning against RL results; calibration (Phase 3) has not been run.

D20 Oracle reference (Phase 2) [R1]
- Greedy insertion: repeatedly add the remaining victim with the lowest total action+travel cost (ties: earliest finish,
  victim id, agents), with exact budget and horizon checks; compiled to per-agent action sequences and executed in the
  real environment (any masked action would raise). After its plan is done the oracle WAITs; such episodes end by the
  horizon (or exhaustion), which is recorded truthfully.
- Quality check: an exhaustive search over the same macro-plan space (all insertion orders/assignments) on tiny instances
  (6x6, V = 3). Result: oracle = optimum in 297/300 cases, 370 vs 373 rescues (99.2%), max gap 1. Macro-plans use
  cheapest-cost paths, so the "optimum" is over that plan space, not over every raw action sequence (stated).
- Tests: plan executes exactly; oracle rescues >= 1 iff the exact feasibility check says feasible (25 instances x 6
  budgets x 2 modes); oracle <= exhaustive optimum <= provable UB.
- Alternatives: MILP (dependency and runtime), exact search (intractable at V = 6).

D21 Metric implementation (Phase 2) [R1]
- Minimal-requirement rule and canonical participants (P6); ratio metrics return numerator/denominator for per-seed pooling;
  coverage and all metrics recomputed from the EpisodeLog only (no environment internals) so they can be re-verified.
- C2 same-step rule (P6, after the validity check): identical simultaneous searches were counted as zero redundancy.
- E3 redefined (P6): the v0.2 wording flagged every below-median team.
- Stale-correction count excludes same-step observations (steps_since_rescue = 0), which were never wrong at decision time.
- Finding F2: C4a PSS is nearly a monotone function of collective return in the validity check (Spearman 1.000, 0.984,
  0.951 at three budgets; pre-stated threshold 0.95). It is kept (pre-specified) but reported with this caveat; it is not
  used as evidence of cooperation on its own.

D22 Group decisions on the Phase 2 open issues (2026-11-12)
- Greedy baseline kept exactly as implemented (no agent-specific tie-breaking). Limitation to report: identical
  deterministic greedy agents starting on one cell move in lockstep, so a greedy team behaves like one agent paying
  three times (simultaneous searches, triple light rescues, no heavy rescues). Comparisons against greedy must be read
  as "uncoordinated identical agents", not as the best possible selfish policy.
- C4a PSS kept in the pre-specified H2 family. Its near-monotone relation to collective return (Phase 2: Spearman
  1.000 / 0.984 / 0.951) is reported next to every C4a result, and C4a is never presented as independent evidence of
  cooperation.

D23 Calibration (Phase 3) [R3, R1, R2]
- Pre-stated rules (config/calibration.yaml) hashed before the first run; numpy quantile method "higher" so T90 and B_ref are
  observed values (integer, slightly conservative). Alternatives: linear interpolation (non-integer B_ref), mean (would make
  rho = 1 insufficient for about half the agents).
- Results: main H = 105, B_ref = 64, levels 1.0/0.5/0.3/0.2. Critical's cooperative RF (0.220) lies above the 0.10-0.15 target
  because rho = 0.1 is solvable in only 33% of instances; the feasibility rule took precedence as pre-stated, and the grid was
  not refined after seeing the result (refining would be a data-dependent change of the procedure).
- ρ means "fraction of the configuration's own just-enough budget"; verified to be comparable across L >= 10 (spread <= 0.08
  at every level) but not on 8x8 maps (limitation, report §3).
- Analytic B_ref: correct scaling (r = 0.998 across 6 configurations), constant underestimate x2.1; reported as a finding.
- Instance sets for all experiments generated and frozen after the levels were fixed (feasible at Critical; seed lists and
  SHA-256 in results/calibration/instance_sets.json). No policy was evaluated on validation/test/shifted instances in Phase 3.
- A3 primary budgets = main budgets (P8). Why: the world-specific calibration makes Critical unsolvable for 27-38% of
  instances in the p_heavy = 0 world, which would confound the DiD with infeasibility. Risk: the p_heavy = 0 world is
  relatively "richer" at the same rho (its just-enough budget is 41, not 64); this is exactly the point of the comparison
  (same resources, different cooperation demand) and the world-specific calibration is still reported.

D24 IQL implementation and pilot outcome (Phase 4)
- IQL as specified (spec §2.1): separate Q-table per agent (3,960 x 8), masked epsilon-greedy with random tie-breaks
  (own RNG in training; RNG seeded by (instance seed, agent) in evaluation = common random numbers), max over the next
  state's valid actions, done = 1 on every termination, no updates for dormant agents. Training-instance order is a
  per-epoch permutation of the frozen pool drawn from the seed alone, so it is identical in every condition.
- Policy churn is measured on the unmasked greedy action (lowest index on ties) over observations visited during the
  validation evaluation of the current checkpoint (the mask depends on state, not only on o, so an unmasked comparison is
  the condition-independent choice). Best-on-validation ties -> later checkpoint.
- Pilot (docs/pilot_protocol.md, hashed first): P0 passed the gate; episode rule did not trigger (rise 0.018 < 0.02).
  No permitted parameter was changed. Findings carried into Phase 5: 0/5 runs meet the stability criterion; joint rescue
  learned but unreliably; learned teams time-limited at Abundant. See results/pilot/pilot_report.md.

D25 Phase 5 execution
- Orchestrated by scripts/run_experiments.py in resumable chunks (run.json written last = completion marker; evaluation
  parts written atomically). 350 training runs (main, A3 primary + secondary, pooled, alternate, A4 solo x 3 slots, A6)
  and 67 evaluation parts; 4.48 CPU-hours of training, about 2 h 10 min wall-clock on 2 cores (corrected in Phase 8: 8,752 s of chunk run time, 2 h 36 min from first start to last end; see N5).
- Extensions to iql.py/train.py for A4 (exploration stream by slot) and A6 (step budget, epsilon by steps) leave the default
  path bit-identical: the Phase 4 pilot Q-table for seed 1000 was reproduced exactly before any Phase 5 run.
- Mixed-team evaluator (A1, A2, A4) reproduces the plain team evaluation exactly for all-learned teams (tested).
- The optional extension (communication) was not run: the instructions limit Phase 5 to the preregistered core.

D26 Phase 6 analysis decisions (recorded before any Phase 6 test statistic was computed; Phase 5 descriptive means
were already known, see N3)
- Unit and values: per training seed, mean over its test episodes; ratio metrics pooled (sum num / sum den); C2 RSR =
  (redundant_other + redundant_self) / searches; C4b = mean per-episode consumption Gini. Recomputed from the raw episode
  CSVs in results/eval (never from summaries).
- Wilcoxon signed-rank: scipy.stats.wilcoxon, zero_method="wilcox", method="auto" (exact null when n <= 50 and there are
  no ties or zeros, else normal approximation) with continuity correction=True; n used is reported. Effect size: matched-
  pairs rank-biserial r = (W+ - W-) / (W+ + W-) over non-zero differences; also the median paired difference.
- One-sample comparisons (H0, H3): differences seed value - baseline value; same Wilcoxon; delta_1 = (#above - #below)/n.
- Friedman: scipy.stats.friedmanchisquare over complete blocks; Kendall's W = chi2 / (n (k - 1)).
- Page's L: scipy.stats.page_trend_test, both predicted orderings (Abundant highest, and Abundant lowest), two-sided
  p = min(1, 2 min(p1, p2)); applied to H1 and to every H2 metric (spec table row "4 levels together (H1, H2)"), Holm
  across the 7 H2 metrics separately for Friedman and for Page.
- Holm: step-down, adjusted p = max over the cumulative max of (m - i + 1) p_(i), capped at 1.
- Bootstrap: 10,000 percentile resamples of seeds; paired contrasts resample seeds and keep each seed's conditions
  together; generator seeded by CRC32 of the quantity's label, so every interval is reproducible independently of order.
- Secondary (unpaired, robustness only): Kruskal-Wallis across levels; Cliff's delta for the 6 level pairs.
- A3 oracle-normalised RF (preregistered secondary b): per seed, RF_seed / RF_oracle(condition), where RF_oracle is the
  oracle reference's mean RF on the same test instances, same world and budgets (ratio of means; the oracle is never 0 at
  the condition level). DiD_norm,s = [nRF(Ab) - nRF(Cr)]_{p=0.5} - [nRF(Ab) - nRF(Cr)]_{p=0}. Also reported: the full
  4-level interaction curve (each level vs Abundant), raw and normalised. Secondary (a): p_heavy = 0 at its own calibration.
- A8 (observational): OLS of per-seed RF (40 seed x level observations, main block) on standardized C1 EAR, C2 RSR_other,
  C3 TDI, C4a PSS, C4b Gini, C5 CR plus level dummies (Abundant reference); seeds with an undefined EAR are excluded from
  the joint model (reported). Coefficient CIs: cluster bootstrap over seeds (10,000). Also: one-metric-at-a-time models
  (metric + level dummies), within-level Spearman correlations, and VIFs. Labelled association only.
- Exploratory, unadjusted p-values labelled as such: A2, A6, pooled, alternate configuration, shifted test, transfer
  matrix, best-validation sensitivity, stable-runs sensitivity, Exp4 (E1, E2, E3, individual vs collective returns).

D27 Phase 6 execution and verification
- run_stats.py reads only raw episode CSVs; make_tables.py / make_figures.py read only saved statistics; verify_results.py
  recomputes seed values and confirmatory statistics independently (scipy + its own Holm), re-runs the statistics into a
  scratch directory (byte-identical), and checks every entry of docs/claims.yaml (generating docs/claims_ledger.md).
- Figures: ordinal blue ramp for rho levels (validated), categorical palette for methods, 95% bootstrap CIs, per-seed
  lines, oracle drawn as a labelled reference; every caption checked against the statistics files.
- Two analysis bugs were found and fixed, both before any deliverable reported their results: the post hoc log-scale
  sign convention (C5) and floating-point tie handling in Wilcoxon (C6).

D28 Final report (Phase 7)
- The report is generated, not typed: scripts/build_report_content.py reads every result number through a small set of
  readers (scripts/report_lib.py) that record source file, locator, raw value and displayed text in
  docs/report_numbers.yaml; scripts/render_report.js renders report/report.docx (docx-js, A4) and scripts/build_report.sh
  converts it to PDF and fills the static contents page in a second pass. verify_results.py V7 re-reads every registered
  value, re-formats it and checks that it appears in the .docx; figures, captions and length are also checked.
- Figure numbers in the report match the result file names (fig1-fig9); environment diagrams are Fig. 0a/0b and the
  calibration figures C1-C3, so a reader can find each file. Two new diagrams were added (make_report_diagrams.py:
  frozen test instance 0 and the step pipeline); they show design, not results.
- Wording rules: performance is always "after 8,000 episodes"; the oracle is always "oracle reference (full information,
  not a learner)"; every analysis carries its family label (confirmatory / secondary / exploratory / post hoc);
  non-significant results are called inconclusive; A8 is called association; A3 is reported as significant in the
  opposite direction, scale- and calibration-dependent, with no cooperation-bottleneck claim.
- References: only the proposal's [1]-[7], plus seven standard method references [8]-[14] marked "added, verify".
- The verifier's own check count is not printed in the report (it would be self-referential); the report points to
  results/logs/verify_results.txt instead.

D29 Phase 8: quick mode, reference verification, viva package
- `scripts/run_all.py --quick` runs every stage of the pipeline at reduced scale: tests; main-sweep IQL training with
  4 levels x 3 seeds x 3,000 episodes on the first 200 training maps; evaluation of learned teams, baselines and the
  oracle reference on the first 30 test maps; H0 and H1 statistics; a figure and a summary. It writes only to
  results_quick/ and refuses results/. 3,000 episodes (not 1,500) was chosen so that the quick run shows a learning
  signal (at 1,500 episodes greedy RF is still about 0.04, as in the full runs' own checkpoints); measured 2 min 55 s on
  2 cores. Its numbers are a pipeline check, never study results. `--full` runs the full study commands in order
  (resumable, so on the delivered repository it skips completed runs).
- References [8]-[14] were checked against their original publication records (docs/references_verification.md);
  issue numbers, proceedings details and DOIs were added; no reference remains marked "verify". [10]-[14] are now cited
  where the methods are described (report Section 8.3).
- Viva package: docs/viva_guide.md (pitch, numbers, explanations, 41 model answers, things not to say, demo, self-test)
  and docs/module_owners.md (owner per module following the proposal roles).
