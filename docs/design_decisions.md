# Design decisions

Each decision lists the alternatives considered, the reason for the choice and its known risk. IDs are cited in the code.

## Environment

**D1 Per-agent budgets (main), pooled team budget (ablation)**
- Alternatives: one global pool only; transferable budgets.
- Why: per-agent budgets create a team allocation problem (who spends on what); the pooled ablation shows whether the
  conclusions depend on this choice.
- Risk: the pooled setting needs a payment order; priority rotates with t so that no agent is favoured.
- In the pooled setting masks, payment and exhaustion use the actual pool; the observed budget feature uses the per-capita
  share floor(B_team / n), so pooled f4 = 0 does not mean the team cannot afford a RESCUE. The two values are separate
  fields of the agent's view (`spendable`, `budget_feature_value`) and are tested.

**D2 An episode ends when nobody can RESCUE any more (max_i B_i < c_R)**
- Alternatives: end when all budgets are 0; never end before H.
- Why: after this point no action can change the number of rescues, so continuing only adds idle steps.
- Risk: an agent with 1-2 units could still SEARCH; this affects coverage only, not rescues.

**D3 Action masking from what the agent can observe, identical for all policies**
- Alternatives: allow invalid actions with a penalty.
- Why: penalties make learners spend samples learning the rules; masking defines validity exactly and keeps baselines
  comparable.
- Risk: ASSIST is masked unless a teammate shares the cell, which slightly helps learners; it applies to every method.

**D4 Heavy victims need a RESCUE and a simultaneous ASSIST by a different agent; p_heavy is a parameter**
- Alternatives: "two agents on the cell" without roles; a time-extended joint lift.
- Why: makes cooperation necessary for part of the outcome, and p_heavy = 0 gives a control world.
- Risk: simultaneous coordination is hard for independent learners and may yield few heavy rescues; that is itself a result.

**D5 The static map is known in advance; victims and teammates are partially observed**
- Alternatives: also hide the terrain.
- Why: keeps the observation to 3,960 values and focuses partial observability on the research question.
- Risk: weaker partial observability than a real building; listed in the assumptions.

**D17 Policies and masks use only observed information; stale memory affects navigation only**
- Alternatives: mask RESCUE using the true victim status (leaks hidden information); let an agent RESCUE an empty cell and
  charge it.
- Why: the observation and mask are built from the agent's own memory and its current radius-1 view, which always includes
  its own cell and is refreshed every step, so a RESCUE on an already-rescued victim is never offered. Stale memory only wastes
  travel until the cell is seen again. Every action is re-validated against the issued mask (`InvalidActionError`).
- Risk: the discovery reward ("first sighting by the team") uses hidden information; it is environment feedback, not a policy
  input. Stale travel is logged so its cost is visible.

**D18 Implementation details**
- Map and instance generation, path tables and the feasibility check live in `mapgen.py`, so `env.py` only handles
  transitions and the tables are reused by baselines and the oracle.
- Victims are at Chebyshev distance >= 2 from the base, so none is visible at t = 0 and every discovery is earned.
- Instance seed = split base + 100 x index + attempt, so regenerating an infeasible instance never collides with the next
  instance's seed (tested for up to 10,000 instances per split).
- Round-half-up everywhere (budgets, counts of walls, victims and heavies); Python's `round()` rounds half to even.
- Deterministic tie-breaks: path first steps prefer UP, DOWN, LEFT, RIGHT; f1 nearest victim by (cost, steps, cell); f2 nearest
  unobserved cell by (cost, cell); f3 nearest teammate by (Manhattan distance, agent id). All tested.
- Walls are added one at a time and kept only if all free cells stay connected, so generation never needs rejection sampling.
- `start_positions` and `budgets` in `reset()` exist only for hand-written test scenarios; experiments always start all agents
  on the base with equal budgets.
- A step that rescues the last victim and also exhausts the budget is labelled `all_rescued`.

## Observation and reward

**D6 Observation = five discrete features with path-based directions**
- Alternatives: a raw local window (too many states for a table); a blocked-direction feature.
- Why: |O x A| = 31,680; directions from cheapest-path first steps never lead an agent into a wall.
- Risk: different situations can look identical; the learnability pilot checked that learning is still possible.

**D7 Budget buckets relative to B_ref, not to the agent's own starting budget**
- Alternatives: fractions of the agent's own initial budget.
- Why: a bucket means the same amount of resource at every ρ, so policies can be compared and transferred across levels.
- Risk: at Critical agents only see the two lowest buckets. Robustness experiment R1 tests the alternative.
- Thresholds: τ1 = c_R = 3, τ2 = max(τ1 + 1, ceil(0.25 B_ref)), τ3 = max(τ2 + 1, ceil(0.5 B_ref)), half-open buckets. On
  integer budgets this is exclusive, exhaustive and never produces an empty or reversed bucket.

**D8 Individual credit split for heavy victims (0.5 / 0.5) vs 1.0 for light; equal team value**
- Alternatives: heavy victims worth more.
- Why: equal value per victim, and a built-in tension between individual and team reward for Exp4.
- Risk: learners may neglect heavy victims; the team term counterweights it. Robustness experiment R3 tests equal credit.

## Baselines, oracle and metrics

**D9 Cooperation metrics are computed from behaviour in the logs, never from reward**
- Alternatives: a team-reward proxy.
- Why: selfish agents that each rescue light victims also earn team reward, so reward cannot show cooperation.
- Risk: each metric has blind spots (e.g. territory division depends on episode length), hence five metrics and a validity check.

**D10 Oracle = full-information centralised greedy-insertion planner, called the "oracle reference"**
- Alternatives: the exact optimum (intractable); a mixed-integer program.
- Why: it shows what the budget allows without claiming optimality.
- Risk: a learner could exceed it on some instances; this would be reported.

**D19 Baselines**
- Every baseline agent receives only its own view, its mask and the static map tables, never the environment; views carry a
  copy of memory and a read-only observation mask, so a policy cannot alter the true state (tested).
- Random: uniform over valid actions.
- Greedy: targets only affordable victims, light before heavy at equal cost, at most one RESCUE attempt per heavy victim
  (otherwise it would burn its budget retrying). Identical deterministic agents starting on one cell move in lockstep, which
  makes greedy weak; see D22.
- Cooperative: joint-rescue role convention (lowest index RESCUEs), light rescues, waiting at a heavy victim for up to 2L steps,
  a help signal (a teammate seen on the same cell in three consecutive views), sector-first exploration with greedy's SEARCH
  rule, and no SEARCH while a lower-index teammate stands on the same cell (otherwise all three agents search the base at t = 0).

**D20 Oracle details**
- Repeatedly inserts the remaining victim with the lowest action and travel cost, with exact budget and horizon checks, then
  executes the plan in the real environment.
- On 300 small instances (6 x 6, V = 3) it matches an exhaustive search over the same plan space in 297 cases (370 vs 373
  rescues, 99.2%).
- Tests: the plan executes exactly; the oracle rescues at least one victim exactly when the feasibility check says it can.

**D21 Metric details**
- One effective RESCUE (and one effective ASSIST for a heavy victim) per rescue; extra simultaneous actions are redundant.
  Ratio metrics return numerator and denominator so they can be pooled per seed. All metrics are recomputed from the episode log.
- Same-step searches by lower-index agents count as prior coverage for redundant search.
- E3 (conflict episode) = best agent above the median individual return and team below the median collective return.
- The productive spend share (PSS) is nearly a monotone function of collective return (Spearman 0.95-1.00), so it is never
  used as independent evidence of cooperation.

**D22 Greedy baseline and PSS kept as implemented**
- Greedy is kept without agent-specific tie-breaking; comparisons with it read as "uncoordinated identical agents", not as
  the best selfish policy.
- PSS stays in the pre-specified H2 family with the caveat of D21 reported next to every PSS result.

## Calibration and learning

**D11 Calibrate H, then B_ref, from the cooperative baseline; ρ levels from the cooperative baseline and the oracle**
- Alternatives: guessed values; calibration from the learners themselves.
- Why: ties ρ to a reproducible definition ("fraction of the just-enough budget") without using the learners.
- Risk: B_ref depends on the quality of the cooperative baseline; an analytic estimate and five other configurations check it.

**D23 Calibration results**
- Rules were written to `config/calibration.yaml` and hashed before the first run; quantiles use numpy's "higher" method so
  T90 and B_ref are observed integer values.
- Main configuration: H = 105, B_ref = 64, levels ρ = 1.0 / 0.5 / 0.3 / 0.2. Critical's cooperative RF (0.220) is above the
  0.10-0.15 target because ρ = 0.1 allows a rescue on only 33% of maps; the feasibility rule took precedence and the grid was
  not refined afterwards.
- ρ is comparable across configurations with L >= 10 (cooperative RF within 0.08 at every level) but not on 8 x 8 maps.
- The analytic B_ref estimate scales correctly (r = 0.998 across six configurations) but is about half the measured value.
- Instance sets were generated and frozen after the levels were fixed; no policy was evaluated on validation or test maps
  during calibration.
- The all-light comparison world uses the main budgets: at its own calibration, Critical leaves 27-38% of maps unsolvable,
  which would confound the comparison with infeasibility. Its own calibration is reported as a secondary analysis.

**D12 Three agents**
- Alternatives: 2 or 4.
- Why: with 2, removing one agent leaves no team; 4 increases non-stationarity and compute.
- Risk: results may not extend to larger teams.

**D13 Training on a fixed pool of 1,000 maps; disjoint seed ranges for validation, test and shifted test**
- Why: no test leakage, and every condition sees the same maps in the same order.

**D14 Primary policy = final checkpoint; best-on-validation as a sensitivity check**
- Why: avoids selecting on noise; any selection uses validation maps only.

**D24 IQL implementation and pilot**
- One Q-table per agent (3,960 x 8), masked ε-greedy with random tie-breaks, maximum over the next state's valid actions,
  done = 1 on every termination, no updates for dormant agents. Training-map order is drawn from the seed alone, so it is the
  same in every condition; evaluation tie-breaks are seeded by (instance seed, agent) so every method sees the same stream.
- Policy churn is measured on the unmasked greedy action over the observations visited during validation.
- The learnability pilot (protocol hashed before running) passed its gate; no hyperparameter was changed. It also showed that
  runs do not stabilise within 8,000 episodes and that joint rescue is learned but unreliably.

**D25 Running the experiments**
- `scripts/run_experiments.py` runs training and evaluation in resumable chunks (`run.json` is written last and marks a run as
  complete). 350 training runs and 67 evaluation parts, 4.48 CPU-hours of training, 2 h 36 min on 2 cores.
- Extensions for solo training (A4) and equal-steps training (A6) leave the default path bit-identical: a pilot Q-table was
  reproduced exactly before the main runs.
- The optional communication extension was not run.

## Statistics

**D15 Unit of analysis = training seed; 10 seeds; paired non-parametric tests with Holm correction and bootstrap CIs**
- Alternatives: per-episode tests (pseudo-replication); unpaired Kruskal-Wallis / Mann-Whitney.
- Why: seeds are the independent replicates; test episodes are repeated measurements of one trained team. Seed s uses the same
  map order, exploration stream and test maps in every condition, so conditions are matched by seed and paired tests (Friedman,
  Page's L, Wilcoxon signed-rank, paired bootstrap) are used. IQL vs a deterministic baseline is a one-sample comparison.
  Unpaired tests are reported as secondary.
- Risk: if matching by seed does not make outcomes similar, paired tests lose little.

**D26 Analysis details (fixed before any test statistic was computed)**
- Per-seed values are means over test episodes; ratio metrics are pooled (sum of numerators / sum of denominators); everything
  is recomputed from the raw episode files in `results/eval`.
- Wilcoxon signed-rank: `scipy.stats.wilcoxon`, zero_method="wilcox", continuity correction; effect size = matched-pairs
  rank-biserial correlation.
- Friedman with Kendall's W; Page's L tested in both directions, two-sided p = min(1, 2 min(p1, p2)); Holm across the seven
  cooperation metrics.
- Bootstrap: 10,000 percentile resamples of seeds, seeded by the label of each quantity so every interval is reproducible.
- All-light comparison (A3): oracle-normalised RF = seed RF / oracle RF in the same condition; the difference-in-differences is
  reported raw and normalised.
- A8 (association only): regression of per-seed RF on the standardised cooperation metrics plus level dummies, with a cluster
  bootstrap over seeds.
- Exploratory analyses report unadjusted p-values and are labelled as exploratory.

**D27 Verification**
- `run_stats.py` reads only raw episode files; `make_tables.py` and `make_figures.py` read only saved statistics.
- `verify_results.py` recomputes the seed values and hypothesis tests independently, re-runs the statistics and compares the
  outputs, and checks every entry of `docs/claims.yaml`.
- Two analysis bugs were found and fixed before any result was reported: the sign convention of the log-scale A3 comparison
  (C5) and floating-point tie handling in the Wilcoxon tests (C6).

**D29 Quick mode**
- `scripts/run_all.py --quick` runs every stage at reduced scale (3 seeds x 3,000 episodes, 200 training and 30 test maps) in
  about 3 minutes and writes only to `results_quick/`; its numbers check the pipeline and are not study results.
  `--full` runs the full study (resumable).
