# The Last Rescue — Phase 0 Design Specification

Status: FROZEN v1.0 (2026-11-12, end of Phase 3) together with `preregistration.md`. Includes pre-freeze revisions P1–P8
(see deviations_log.md). Calibration results: `results/calibration/calibration_report.md`.
Any later change is recorded in `deviations_log.md`.

Notation: plain text math. `|X|` = size of a set; `[x]` = indicator (1 if x is true, else 0);
`d(a,b)` = cost of the cheapest path between cells a and b (hazard cells cost 2 to enter, normal cells 1).

---------------------------------------------------------------------------------------------------

## 0. Ambiguities in the draft and the defaults chosen

| # | Draft is vague about | Default chosen | Why (short) |
|---|---|---|---|
| A1 | Per-agent vs global budget | Per-agent, non-transferable, no recharge (main); pooled team budget (ablation) | Review point 1; per-agent creates a real allocation problem across agents |
| A2 | What happens at exhaustion | Masking + dormancy + "exhaustion" termination, Section 1.4 | Review point 1 |
| A3 | Is terrain observed or known? | The static map (walls, hazard cells, base) is known to every agent beforehand; victims, teammates' positions beyond range, teammates' memories and budgets are hidden | Puts the partial observability where the research question is (finding victims, not knowing teammates' intent) and keeps the tabular state small. Still a partially observed Markov game |
| A4 | How victims are discovered | Passive sensing of own cell and 8 neighbours (radius 1); SEARCH reveals radius 2 (5x5) | SEARCH is costly but efficient, which creates a real exploration trade-off |
| A5 | What "cooperation" means operationally | Five deterministic metrics (Section 3), never team reward | Review point 1 |
| A6 | Where cooperation is *necessary* | HEAVY victims need RESCUE + simultaneous ASSIST by a different agent | Gives a causal lever (p_heavy) for review point 2 |
| A7 | Number of agents | n = 3 | n = 2 makes the "remove one agent" ablation trivial (no heavy rescue possible); n = 3 still keeps tabular IQL tractable |
| A8 | Start positions | All agents start on a common base cell (rescue depot) | Realistic; forces agents to fan out, so territory division is measurable |
| A9 | Victim values | Every victim is worth the same to the team; individual credit for a heavy victim is split (0.5 + 0.5) vs 1.0 for a light victim | Builds a deliberate individual-vs-team tension for Exp4 |
| A10 | "Oracle upper bound" | A full-information centralized planner is a strong *achievable reference*, not a proven optimum (exact optimum is an NP-hard multi-agent orienteering problem). We report it as the "oracle reference" plus a loose but provable upper bound | Honesty: calling a heuristic an upper bound would be attackable |
| A11 | Mission success | All V victims rescued. Rescue fraction is the primary metric because success is ~0 under scarcity | Avoids a floor-effect primary outcome |
| A12 | Final policy used for testing | Final checkpoint (primary); best-on-validation checkpoint as sensitivity | No selection bias in the primary result; validation set used for any choice |
| A13 | Which policy defines the ρ levels | The hand-designed cooperative baseline and the oracle, never the RL agents | Avoids circularity (tuning conditions on the outcome being measured) |
| A14 | Communication in core | None. The optional extension is a cost-bearing BEACON action | Keeps the core clean; the extension is a natural add-on |

---------------------------------------------------------------------------------------------------

## 1. FIX 1 — Formal resource-constrained Markov game

### 1.1 Game
G = < N, S, (A_i), P, (R_i), (O_i), (Z_i), γ, H >, with N = {1,...,n}, n = 3.

Global state s_t = (M, V_t, X_t, B_t, t, K_t):
- M: static map on an L x L grid. Each cell is FREE, WALL or HAZARD (hazard is free but costs 2 to enter). One FREE cell is the base b.
  All free cells are connected (maps that are not connected are regenerated).
- V_t: victims. Each victim v has cell c_v, type τ_v ∈ {LIGHT, HEAVY}, status ∈ {waiting, rescued}.
- X_t = (x_t^1,...,x_t^n): agent cells. Several agents may share a cell (needed for ASSIST).
- B_t = (B_t^1,...,B_t^n): remaining integer budgets (per-agent setting) or a single B_t^team (pooled setting).
- t: time step, 0 ≤ t ≤ H.
- K_t = (K_t^1,...,K_t^n): each agent's private memory (cells it has observed, victims it has seen and their types/status as last seen).

### 1.2 Actions and costs (integer units; all values in `config/default.yaml`)

| Action | Cost c(a) | Effect | Valid (unmasked) iff |
|---|---|---|---|
| UP/DOWN/LEFT/RIGHT | 1 (2 if the target cell is HAZARD) | move one cell | target is FREE/HAZARD (not wall, not off-grid) and cost ≤ budget |
| SEARCH | 2 | reveals all victims within Chebyshev radius r_s = 2 | cost ≤ budget |
| RESCUE | 3 | see 1.3 | the agent's current observation of its own cell shows an unrescued victim, and cost ≤ budget |
| ASSIST | 2 | see 1.3 | the agent's current observation of its own cell shows an unrescued HEAVY victim and ≥1 teammate on that cell, and cost ≤ budget |
| WAIT | 0 | nothing | always |

Why these costs: moving is the cheap "unit"; hazard doubles it (terrain matters); SEARCH costs 2 moves but reveals up to 25 cells
(vs about 3 new cells per move), so it is efficient but not free; RESCUE is the most expensive single action (it is the "payload");
ASSIST is cheaper than RESCUE because the assister is a helper. WAIT costs 0 so an agent can never be forced into an invalid state.
The ratios, not the absolute values, matter, because B_ref is calibrated from the same costs (Section 4).

Masking rule: the mask m_t^i is a function of agent i's own observation only (see 1.3a): the known static map, its own cell
contents as currently observed, co-located teammates, and its own budget (the shared pool in the pooled ablation).
It applies identically to learners and all baselines. A masked action can never be chosen (ε-greedy samples among valid actions;
greedy argmax is over valid actions).

### 1.3 Transition (simultaneous moves, deterministic given actions)
All n actions are chosen at the same time from o_t. Then, in this order:
1. Budgets: B_{t+1}^i = B_t^i − c(a_t^i). (Pooled: see 1.5.)
2. Moves: every moving agent moves; agents may share cells.
3. RESCUE/ASSIST resolution, using each cell's agents (rescuing/assisting agents did not move, so order 2/3 is irrelevant):
   - LIGHT victim v on cell c is rescued at t iff ≥1 agent on c chose RESCUE.
     If k ≥ 2 agents chose RESCUE on the same light victim, it is rescued once; individual credit is split 1/k; the extra
     k−1 RESCUEs are logged as *duplicate rescues* (wasted).
   - HEAVY victim v on cell c is rescued at t iff ∃ i ≠ j on c with a^i = RESCUE and a^j = ASSIST.
     If several RESCUE/ASSIST agents are present, all of them share the credit (rescuer credit split among RESCUErs,
     assister credit split among ASSISTers). A RESCUE on a heavy victim with no ASSIST fails (cost is still paid);
     an ASSIST with no RESCUE fails.
4. Observation update (on the post-transition state s_{t+1}): SEARCH reveals victims within radius r_s around the searcher's
   cell; every agent passively sees victims on its own cell and the 8 neighbours (radius r_v = 1). For every observed cell the
   agent's memory is overwritten with the true current contents (victim present/absent, type, status). Cells not observed keep
   their last remembered contents, so a victim rescued out of range stays "waiting" in that agent's memory (stale memory is a
   genuine cost of partial observability, see 1.3a).
5. t ← t + 1; check termination; build o_{t+1}^i and m_{t+1}^i for every agent from its own memory and current observation.

The environment itself is deterministic given actions; all randomness is in map generation, the agents' exploration, and tie-breaking.

### 1.3a Information use, masking and stale victim information
Principle: a policy's input o_t^i and its action mask m_t^i are computed only from information agent i has actually observed:
the static map (known a priori), its own memory K_t^i, its current radius-1 view (which always includes its own cell),
teammates within radius r_tm, its own budget (in the pooled ablation, the shared pool, treated as a gauge every agent can read),
and t. Ground-truth victim status outside the agent's view is never used for o_t^i or m_t^i.
Hidden information is used only by (a) the environment to resolve actions and compute rewards (e.g., "first sighting by the
team"), which is feedback, not a policy input; (b) the oracle reference, which is full-information by design and labelled so;
(c) offline analysis of logs.

Stale information, case by case (agent A remembers victim v at cell c as waiting; agent B rescued v at step t_0 while c was outside
A's view):
1. Navigation: A's feature f1 may still point to v. A may walk toward c. These moves are ordinary valid actions; their cost is
   spent; nothing is blocked or corrected by the environment while c is outside A's view.
2. Correction: the first time c enters A's view (radius 1 when A is adjacent to or on c, or radius 2 if A SEARCHes nearby), step 4
   of 1.3 overwrites A's memory with "no waiting victim at c". This happens in the transition in which c is observed, so before A
   can choose its next action.
3. Consequence for RESCUE: RESCUE is valid only if A's *current observation of its own cell* shows an unrescued victim, and the
   own cell is always observed. Because the observation is rebuilt from the true post-transition state every step, A can never be
   offered RESCUE on a victim that was already rescued in an earlier step. A RESCUE "based on stale information" is therefore
   impossible by construction; stale information can only waste travel (and possibly a SEARCH).
4. Same-step contention: if at step t A and B are on the same cell and both (validly, from correct observations) act on the same
   victim, the action is resolved by the simultaneous rules in 1.3 step 3 (duplicate light RESCUE: rescued once, credit split, the
   extra RESCUEs logged as `duplicate_rescue` and their cost is spent; heavy: shared credit). This is contention, not staleness.
5. Safety check: the environment re-validates every submitted action against the mask it issued for that agent at that step.
   An action outside the mask raises `InvalidActionError` (never silently converted to WAIT). Masked policies cannot trigger it;
   it exists to catch bugs and is covered by tests.

Logged events (per-step log, used for diagnostics and replays, never as policy input):
- `stale_correction`: (t, agent, victim id, cell, steps since the victim was actually rescued) when an agent's memory changes
  from "waiting" to "absent" for a victim rescued by someone else.
- `stale_travel` (computed offline from the log using ground truth): the number and cost of moves agent i made while its f1
  target was a victim already rescued in ground truth. Reported per ρ as a diagnostic of partial observability; not a
  pre-registered outcome.
- `duplicate_rescue`, as in 1.3.

### 1.4 Feasibility and exhaustion semantics (exact definitions)
- c_min = 1 (cheapest costly action), c_R = 3 (RESCUE cost).
- Agent i is **dormant** at t iff B_t^i < c_min (it can only WAIT; it still occupies its cell; it cannot ASSIST/RESCUE).
- Agent i is **rescue-incapable** iff B_t^i < c_A = 2 (it can no longer ASSIST or RESCUE, though it may still move).
- **Termination**: the episode ends at the first t where one of the following holds (checked in this order; the reason is logged):
  1. `all_rescued`: every victim is rescued;
  2. `exhausted`: no further rescue is possible, i.e. max_i B_t^i < c_R (nobody can RESCUE any more, so nothing can change the
     primary outcome);
  3. `horizon`: t = H.
  Note: `exhausted` is strictly a budget event; reaching H with budget left is a time event. We report the fraction of each per ρ.
- **Instance feasibility at ρ**: instance (map, victims, budgets B_0(ρ)) is feasible iff a full-information centralized planner can
  rescue ≥1 victim, which is checked exactly:
  feasible(ρ) ⇔ ∃ light v, ∃ i: d(b, c_v) + c_R ≤ B_0^i and (number of steps on that path) + 1 ≤ H
             or ∃ heavy v, ∃ i ≠ j: d(b,c_v) + c_R ≤ B_0^i and d(b,c_v) + c_A ≤ B_0^j (and the same time check).
  (All agents start at b and the cheapest-path cost d(b,c_v) is computed by Dijkstra on the known map.)
  Test/validation instances that are infeasible at the *lowest* ρ level are regenerated with the next attempt seed
  (seed = split base + 100·index + attempt, P5); the rejection rate is
  reported. Because budgets increase with ρ, feasibility at the lowest ρ implies feasibility at all higher ρ.
- **Oracle reference** (Section 2.4): rescue count of the full-information centralized planner, per instance and per ρ.
  Learned performance is also shown as a fraction of it.
- **Provable (loose) upper bound** UB(ρ): every rescue must pay its action costs, m_v = c_R (light) or c_R + c_A (heavy),
  so even with free travel and perfectly shared budgets the team cannot exceed
  UB(ρ) = min( V, max{ k : sum of the k smallest m_v ≤ Σ_i B_0^i } ).
  It ignores travel, so it is valid but loose; it is reported only as a sanity ceiling, never as the denominator of a headline number.

### 1.5 Pooled-budget ablation
B_0^team = n · round(ρ · B_ref). An action is valid iff its cost ≤ B_t^team. If the sum of requested costs in one step exceeds
B_t^team, actions are paid in agent order rotated by t (priority (t mod n), (t+1 mod n), ...); unpaid actions become WAIT and are
logged as `preempted`. Exhaustion: B_t^team < c_R.
Two different budget quantities are used in the pooled setting and must not be confused:
- the *spendable* budget, used for masking, payment and exhaustion, is the actual shared pool B_t^team;
- the *observation feature* f4 is the integer per-capita share floor(B_t^team / n), bucketed with the rule of 1.7.
The per-capita value only summarises how much of the pool is "my share"; it never decides feasibility. In particular,
f4 = 0 in the pooled setting means "my per-capita share is below c_R", NOT "the team cannot afford RESCUE": with n = 3 and
B_t^team = 8, f4 = 0 (floor(8/3) = 2 < 3) while RESCUE is still valid because 3 ≤ 8.

### 1.6 Reward
For agent i at step t (rewards are paid on the transition):

r_ind^i = 0.1 · (number of victims that agent i saw first, i.e. before any other agent)
        + 1.0 · (credit share of light rescues completed by i as RESCUEr)
        + 0.5 · (credit share of heavy rescues completed by i as RESCUEr)
        + 0.5 · (credit share of heavy rescues completed by i as ASSISTer)
r_team  = number of victims rescued by anyone at this step (identical for all agents)
cost^i  = c(a_t^i)

R^i = λ_I · r_ind^i + λ_T · r_team − λ_C · cost^i, with λ_I = 1.0, λ_T = 1.0, λ_C = 0.02, fixed across every ρ and condition.

Why it cannot be gamed:
- Hoarding (WAITing to keep budget): unspent budget earns nothing at the end of the episode; any reachable rescue
  (worth ≥ λ_T·1 + λ_I·0.5 = 1.5 to its participants) outweighs its cost penalty (a typical rescue trip ≤ 40 units → ≤ 0.8).
- Wasting resources: every unit spent costs −0.02 with no return unless it produces a discovery or a rescue.
- Farming discovery: bounded by 0.1·V per team per episode, and only for *first* sightings.
- Farming ASSIST: ASSIST pays only when it completes a heavy rescue.
- Individual vs team tension (intentional, for Exp4): a light rescue pays its rescuer 1.0 individually; a heavy rescue pays each
  participant only 0.5 although the team value is the same. A purely individual learner prefers lights.

### 1.7 Observation model (what each learner sees: a compact discrete tuple)
o_t^i = (f1, f2, f3, f4, f5)

| Feature | Values | Count |
|---|---|---|
| f1 nearest known unrescued victim (from i's memory), first step of the cheapest path and distance | none; here-LIGHT; here-HEAVY; {N,S,E,W} × {near (≤3 steps), far} | 11 |
| f2 first step toward the nearest cell i has never observed | none (all observed); N; S; E; W | 5 |
| f3 nearest teammate within Chebyshev radius r_tm = 3 | none in range; same cell; N; S; E; W (dominant axis, ties → vertical) | 6 |
| f4 own remaining budget b (integer units), bucketed by thresholds τ1 < τ2 < τ3 defined below | 0: b < τ1; 1: τ1 ≤ b < τ2; 2: τ2 ≤ b < τ3; 3: b ≥ τ3 | 4 |
| f5 elapsed time | t < H/3; H/3 ≤ t < 2H/3; t ≥ 2H/3 | 3 |

Budget bucket rule (f4). b is a non-negative integer (masking guarantees b ≥ 0; in the pooled ablation b = floor(B_t^team / n)).
B_ref is a positive integer fixed per configuration by calibration (Section 4). The integer thresholds are
  τ1 = c_R = 3
  τ2 = max(τ1 + 1, ceil(0.25 · B_ref))
  τ3 = max(τ2 + 1, ceil(0.50 · B_ref))
  f4(b) = 0 if 0 ≤ b < τ1;  1 if τ1 ≤ b < τ2;  2 if τ2 ≤ b < τ3;  3 if b ≥ τ3.
Properties: the four intervals are half-open, so each boundary value belongs to exactly one bucket (the upper one);
since τ1 < τ2 < τ3 strictly, no interval is empty or reversed; and they cover every integer b ≥ 0, so the rule is mutually
exclusive and exhaustive. Because b is an integer, b ≥ ceil(x) ⇔ b ≥ x, so these integer thresholds are exactly the intended
real cut points 0.25·B_ref and 0.5·B_ref whenever those exceed the previous threshold; the max(·) terms only matter for a very
small B_ref (< 16) and keep the ordering strict. In the per-agent (main) setting bucket 0 means exactly "cannot pay for RESCUE"; in the pooled ablation it means only
"per-capita share below c_R" (see 1.5). τ1, τ2, τ3 are computed once per
configuration, written to the resolved config, and are identical at every ρ (that is what makes buckets comparable across ρ).

|O| = 11 · 5 · 6 · 4 · 3 = 3,960 observations; |O × A| = 3,960 · 8 = 31,680 Q-values per agent (many are unreachable).
Directions are the first move on the cheapest known path (precomputed per map with Dijkstra), so walls never trap the agent and no
"blocked-direction" feature is needed. Budget buckets are relative to B_ref (not B_0^i) so a bucket means the same absolute
amount at every ρ, which is what makes the cross-ρ transfer matrix (Exp5) interpretable.
What the learner does NOT see: other victims' positions it has not observed, teammates beyond radius 3, teammates' memory or budgets,
and which teammate is where by identity. Baselines read the same raw information (own memory, own budget, teammates within radius 3)
plus fixed conventions (agent index, map), but not the compressed tuple.

### 1.8 Map and instance generation
- Main config: L = 10, wall fraction 0.15, hazard fraction 0.10 of free cells, base in a corner region, V = 6 victims
  (density 0.06 per cell), number of heavy victims = round(p_heavy · V) = 3 (exact count, lower variance), victims at Chebyshev distance ≥ 2 from the base
  (so no victim is visible at t = 0; P5).
- Disjoint seed ranges: calibration 1,000,000+; training pool (1,000 maps) 2,000,000+; validation (50) 3,000,000+;
  test (100) 4,000,000+; shifted test (100; wall 0.25, density 0.09) 5,000,000+.
- Common random numbers: every method and every ρ is evaluated on exactly the same validation/test instances; in training,
  seed s uses the same map order and exploration seed stream under every ρ, so conditions differ only in ρ.

---------------------------------------------------------------------------------------------------

## 2. Algorithms (specified now, implemented in Phases 2 and 4)

### 2.1 Independent Q-learning (per agent, separate table)
Q_i(o,a) ← Q_i(o,a) + α [ R^i + γ · (1 − done) · max_{a' valid in o'} Q_i(o',a') − Q_i(o,a) ]
- α = 0.1 (constant), γ = 0.98, Q initialized to 0.
- ε-greedy over valid actions; ε decays linearly 1.0 → 0.05 over the first 70% of episodes, then stays 0.05.
- Evaluation: ε = 0; ties among valid actions broken by an RNG seeded by (test-instance id, agent id), identical across conditions.
- Dormant agents still produce transitions but have only WAIT available; they are excluded from updates after dormancy
  (their transitions carry no learnable choice).
- Checkpoints every 500 episodes, evaluated on the 50 validation instances.

### 2.2 Baselines (all decentralized, same information and masking as the learners)
- Random: uniform over valid actions.
- Greedy (individually myopic): go to the nearest known victim, preferring LIGHT over HEAVY at equal distance (higher individual
  pay); at a victim it RESCUEs; it never ASSISTs; with no known victim, it walks to the nearest unobserved cell and SEARCHes when
  ≥ 50% of the search footprint is unobserved by itself. Phase 2 details (D19): it only targets victims it can afford
  (d + c_R ≤ budget) and attempts each HEAVY victim at most once (no endless failed retries). Consequence (finding F1, P6):
  identical deterministic agents starting on one cell move in lockstep, so greedy teams search and rescue together.
- Hand-designed cooperative: (a) the free cells are split into n sectors by a fixed rule known to all (k-means-style partition
  seeded deterministically from the map); each agent explores its own sector first; (b) rescues lights it knows; (c) on finding a
  heavy victim it waits there (WAIT is free) for up to W = 2L steps; (d) an agent that sees a stationary teammate within radius 3
  for ≥2 consecutive steps goes to it; (e) two agents on a heavy victim: lower index RESCUEs, higher index ASSISTs;
  (f) search convention (D19/P7): an agent does not SEARCH while a lower-index teammate stands on the same cell.
  Full priority order, timeout and false-alarm handling: `src/tlr/baselines.py` (CooperativeController) and D19.
- Oracle reference: centralized, full information (all victims, types, budgets). Repeated greedy insertion: at each decision point
  assign the cheapest feasible remaining victim (lights to one agent; heavies to the cheapest feasible pair, with the earlier
  arrival WAITing), respecting budgets and H; executed in the real environment so the same rules apply. Ties: earliest finish,
  victim id, agent ids. Its quality is checked against an exhaustive search over the same macro-plan space on tiny instances
  (D20). It is always reported separately from learned and decentralized policies.

---------------------------------------------------------------------------------------------------

## 3. Cooperation metrics (formal, deterministic, computed from the per-step log)

Per episode e. Let 𝒜 = all (effective) actions, 𝒜_X = actions of type X, and θ = 0.5.
Minimal-requirement rule (P6): each rescue event has exactly one effective RESCUE and, for a heavy victim, exactly one
effective ASSIST; extra simultaneous RESCUEs/ASSISTs on the same victim are redundant co-actions (wasted). Where several
agents share a role, the lowest-index one is the canonical participant.

C1 Effective assist rate
  EAR = (number of heavy rescues, i.e. one effective ASSIST each) / |𝒜_ASSIST|. Undefined if there are no ASSISTs (reported as missing, with the count).

C2 Redundant search ratio
  For a SEARCH by agent i at t with footprint F (free cells within radius r_s):
    redundant_other ⇔ |F ∩ S^{−i}| / |F| ≥ θ, where S^{−i} = cells covered by SEARCHes of *other* agents at earlier steps,
                      plus same-step SEARCHes of lower-index agents (P6: identical simultaneous searches add no information);
    redundant_self  ⇔ |F ∩ S_{<t}^{i}| / |F| ≥ θ (own earlier SEARCHes) and not redundant_other.
  RSR = (redundant_other + redundant_self)/|𝒜_SEARCH|; RSR_other is the coordination-relevant part (re-searching your own area is
  inefficiency, not a coordination failure). Undefined if no SEARCHes.

C3 Territory division index
  U_i = set of cells visited by agent i during the episode, excluding the base b.
  TDI = 1 − (2 / (n(n−1))) · Σ_{i<j} J(U_i, U_j), J(A,B) = |A∩B| / |A∪B| (J = 0 if A∪B is empty).
  TDI = 1: disjoint territories; TDI = 0: all agents visited identical cells.

C4 Coordinated resource use
  C4a productive spend share PSS = Σ over rescues of the minimal required action cost (c_R; c_R + c_A for heavy) / total spent.
      Phase 2 finding F2: PSS is nearly a monotone function of collective return (Spearman 0.95–1.00 in the validity check),
      so it carries little information beyond reward; it is kept as pre-specified but interpreted with that caveat.
  C4b consumption Gini G = Σ_i Σ_j |u_i − u_j| / (2 n² ū), u_i = total cost paid by agent i (= B_0^i − B_end^i in the per-agent
      setting; also defined in the pooled setting) (0 if ū = 0). Low G = balanced load.
  We also report the Gini of remaining budgets (as the review asks) with the same formula on B_end^i (per-agent setting only).

C5 Headline cooperation rate
  CR = |cooperative non-WAIT actions| / |non-WAIT actions|, where an action is cooperative iff it is
  (i) the effective ASSIST of a heavy rescue (canonical assister), or
  (ii) the effective RESCUE of a heavy rescue (canonical rescuer), or
  (iii) a move by a canonical participant of a successful heavy rescue at (t*, c), during [t* − 2L, t*), that reduced its
       cheapest-path cost to c (the "converging" moves).
  Light rescues, solo exploration and discovery never count as cooperative: they can be done by a lone agent.
  By construction CR = 0 when p_heavy = 0; in that world C2–C4 carry the cooperation evidence.

Construct validity plan (Phase 2): unit tests on hand-written scripted episodes with known answers for every metric; the
cooperative baseline must score higher than random and greedy on C1, C3, C5 and lower on RSR_other; we report the correlation
between each metric and team return across episodes to show they are not identical to reward (e.g., a team that rescues only
lights has positive return and CR = 0).

Performance metrics: rescue fraction RF = rescued / V (PRIMARY); mission success MS = [all rescued]; oracle-normalized
RF / RF_oracle (where RF_oracle > 0); collective return Σ_i Σ_t R^i (undiscounted) and each individual return; resource
efficiency = rescued per 100 units spent; coverage = |cells observed by any agent| / |free cells|; termination-reason shares.

Individual-vs-collective (Exp4) event definitions:
  E1 abandonment: two agents are on a cell with an unrescued heavy victim, one plays RESCUE or ASSIST, and the other does not
     play the complementary action (the partner's action is wasted);
  E2 duplicate light rescue (see 1.3);
  E3 per-episode conflict (P6): the episode's best agent has an individual return ABOVE the median of all individual returns
     in its condition AND the team's collective return is BELOW the condition median of collective returns. (The v0.2 wording
     was true of every below-median team, so it flagged ~50% of episodes by construction.) Concrete replays will be shown.
Ratio metrics are pooled per seed as Σ numerators / Σ denominators (preregistration §3); the code returns both parts.
Diagnostics: stale corrections count only memory that was wrong for ≥ 1 step (a same-step observation is logged, not counted).

---------------------------------------------------------------------------------------------------

## 4. FIX 3 — Calibration of H, B_ref and ρ

Step 1 (horizon). On 200 calibration instances with unlimited budget, run the cooperative baseline with a long cap (H_max = 40L).
Let T90 = the 90th percentile over instances of the step at which ≥90% of victims are rescued. Set H = ceil(T90 / 0.7). Then verify
that with this H and unlimited budget, ≥90% of instances reach ≥90% rescues (time is not the binding constraint).

Step 2 (B_ref). With H fixed and unlimited budget, record per-agent consumption u_i of the cooperative baseline on the same 200
instances. B_ref = 90th percentile of all u_i (pooled over agents and instances). Meaning: at ρ = 1 an agent has enough budget in
about 90% of cases, i.e. "just enough".

Step 3 (analytic cross-check). With f = free fraction, h = hazard fraction, c̄_m = 1 + h, A = f·L² free cells, swath w = 2r_s+1:
  searches needed       N_S ≈ A / w²
  coverage path length  D ≈ A / w   (lawn-mower with swath w)
  rescue action cost    C_V = V·[(1 − p_h)·c_R + p_h·(c_R + c_A)]
  heavy convergence     D_h ≈ p_h·V·(L/2)  (the second agent's extra travel)
  B_ref_analytic ≈ (1/n)·[ c_S·N_S + c̄_m·(D + D_h) ] + C_V / n
This is a back-of-envelope estimate; the table will report analytic vs empirical and their ratio per configuration.
Large disagreement is a finding, not a failure (it would show the planner-free intuition misses detours/waiting).

Step 4 (ρ pilot sweep). For ρ ∈ {1.0, 0.9, ..., 0.1}: run oracle and cooperative baseline on the 200 calibration instances; record
mean RF, feasibility rate, and termination shares. Pick four levels by minimizing |RF_coop(ρ) − target| for targets
Abundant ≈ 1.0 (take ρ = 1.0), Moderate ≈ 0.70, Scarce ≈ 0.40, Critical ≈ 0.10–0.15, subject to: oracle rescues ≥ 1 victim in
≥ 95% of instances at Critical (otherwise move Critical up one step). The levels are fixed before any RL experiment.

Step 5 (sensitivity grid). Repeat steps 1–4 for L ∈ {8, 12} × density ∈ {0.04, 0.08} (plus the main 10 / 0.06). Report
H, B_ref (empirical and analytic) and RF_coop(ρ) curves; if ρ means "fraction of just-enough budget", the RF_coop(ρ) curves
should roughly overlap. One full IQL scarcity sweep is repeated on one alternate configuration (L = 12, density 0.04 unless
calibration shows another is more informative; the choice is recorded before running).

Step 6 (p_heavy = 0 world for A3). Calibrated separately with the same procedure (result: H = 48, B_ref = 41). Because its
own Critical budget (b0 = 8) leaves 27–38% of the frozen instances unsolvable, the PRIMARY A3 comparison uses the main H and
B_ref in both worlds (only victim types differ) and the world-specific calibration is the secondary analysis (P8).

Calibration results (Phase 3): main H = 105, B_ref = 64, ρ levels 1.0 / 0.5 / 0.3 / 0.2 (b0 = 64 / 32 / 19 / 13);
per-configuration values in `config/calibrated.yaml`; full report `results/calibration/calibration_report.md`.

---------------------------------------------------------------------------------------------------

## 5. FIX 2 — Attribution under non-stationarity

What is causal and what is not:
- ρ is manipulated with everything else held fixed (common random numbers), so "ρ changes rescue fraction" is a causal claim
  *about this environment and this learning procedure*.
- "Cooperation mediates the ρ effect" is not identified by correlations; it is supported (or not) by interventions A1–A4.

A1 Teammate mismatch. For each ρ, form 20 mismatched teams in 2 shuffle rounds. In each round, slot 1 keeps seed s's agent 1, and
   slots 2 and 3 take agents from seeds σ_2(s) and σ_3(s), where σ_2 and σ_3 are permutations of {0..9} drawn from a pre-registered
   RNG such that s, σ_2(s), σ_3(s) are all distinct for every s. Each round gives 10 teams and uses every seed's agent once per
   slot. Mismatch score of seed s = mean RF of its two mismatched teams (the teams containing seed s's agent 1). Compared with
   the original team of seed s on the same test instances (paired by s; see preregistration §5).
   Prediction if coordination is co-adapted: RF and CR drop. No drop ⇒ the policies are "interchangeable", i.e. little co-adapted
   convention.
A2 Agent ablation. At test time replace agent k (each k in turn) by RANDOM or by WAIT-only. Report the drop in RF and in C1–C5.
   Same ablation on the cooperative baseline for comparison.
A3 Cooperation-necessary vs optional worlds. Full IQL sweep with p_heavy = 0 and p_heavy = 0.5 (primary: identical main H and
   B_ref in both worlds; secondary: p_heavy = 0 world at its own calibration, and DiD on oracle-normalised RF; P8).
   p_heavy = 0 instances use the same seeds, so they have the same layouts and victim positions as the p_heavy = 0.5 instances,
   with every victim set to LIGHT; training seed s uses the same map order and exploration stream in both worlds.
   Per seed: DiD_s = [RF_s(Abundant) − RF_s(Critical)]_{p=0.5} − [RF_s(Abundant) − RF_s(Critical)]_{p=0}; the estimate is the
   mean of DiD_s with a paired bootstrap CI over seeds (also the full 4-level interaction curve).
A4 Solo-learner control. Train each agent alone (n = 1 environment, same instance pool, same per-agent budget, same episodes),
   then deploy the three solo agents together. Solo team s consists of three solo agents trained with seed s's map order and
   exploration streams (one stream per agent slot, as in joint training). Compared with joint team s, paired by s.
   Solo agents cannot ever experience a heavy rescue, so the gap on heavy rescues measures what was learned *from* teammates.
A5 Non-stationarity diagnostics. Per checkpoint: policy churn = fraction of observations visited in validation whose greedy action
   changed since the last checkpoint; mean |TD error|; validation RF with CI across seeds.
   Stability criterion (pre-registered): churn < 5% between the last two checkpoints AND validation RF changes by < 0.02 across the
   last three checkpoints. We report which runs meet it.
A6 Sample-size confound. Main: equal episodes for every ρ. Sensitivity: equal environment steps (each ρ trains until it has used
   the step count of the Abundant run with the same seed). Both reported.
A7 Statistics: unit of analysis, paired vs independent comparisons, tests and effect sizes are defined in
   `preregistration.md` §3 and §5 (the single authoritative source).
A8 Mediation (observational, labelled as such). Regress per-seed RF on C1–C5 with ρ-level as a categorical covariate; report
   coefficients with bootstrap CIs and per-seed scatter plots. Explicitly not a causal estimate.

---------------------------------------------------------------------------------------------------

## 6. Default parameter table (all in config; ★ = fixed by calibration in Phase 3)

| Parameter | Value |
|---|---|
| Grid L | 10 (sensitivity 8, 12) |
| Wall fraction / hazard fraction | 0.15 / 0.10 (shifted test: wall 0.25) |
| Agents n | 3, common base |
| Victims V | 6 (density 0.06; sensitivity 0.04, 0.08; shifted test 0.09) |
| p_heavy | 0.5 (A3: 0.0) |
| Radii r_v / r_s / r_tm | 1 / 2 / 3 |
| Costs move / hazard / SEARCH / RESCUE / ASSIST / WAIT | 1 / 2 / 2 / 3 / 2 / 0 |
| Horizon H | 105 (calibrated; alternate config 150; p_heavy = 0 world 48, secondary only) |
| B_ref | 64 (calibrated; alternate config 87; p_heavy = 0 world 41, secondary only) |
| ρ levels | Abundant 1.0, Moderate 0.5, Scarce 0.3, Critical 0.2 → b0 = 64 / 32 / 19 / 13 |
| γ | 0.98 |
| α | 0.1 constant |
| ε | 1.0 → 0.05 linear over first 70% of episodes |
| λ_I / λ_T / λ_C | 1.0 / 1.0 / 0.02 |
| Training episodes per run | 8,000 provisional; fixed in Phase 4 pilot on validation data only, then identical for all conditions |
| Checkpoint interval | 500 episodes |
| Training seeds | 10 per condition (0–9) |
| Instances: train pool / validation / test / shifted test / calibration | 1000 / 50 / 100 / 100 / 200 |

---------------------------------------------------------------------------------------------------

## 7. Run plan and compute estimate (to be replaced by a measured benchmark in Phase 1)

Assumption: ~40 µs per agent-step (env + features + Q update) in pure Python, ~70 steps per episode, n = 3
→ ~8.5 ms/episode → ~70 s per 8,000-episode run (fewer at low ρ because episodes end earlier).

| Block | Runs |
|---|---|
| Main sweep: 4 ρ × 10 seeds | 40 |
| A3 p_heavy = 0 sweep | 40 |
| A4 solo-trained (3 solo agents per seed) | 40 (≈ cost of 40 joint runs) |
| A6 equal-steps sensitivity | 30 (Abundant reused) |
| Pooled-budget ablation | 40 |
| Alternate configuration sweep | 40 |
| Total training | ≈ 230 runs ≈ 4.5 CPU-hours |
| Evaluation, A1/A2, transfer matrix, calibration | ≈ 0.3 CPU-hours |

Wall time ≈ 1.2 h on a 4-core laptop, ≈ 2.5 h on this 2-core sandbox. If the Phase 1 benchmark shows the step cost is higher,
the order of cuts (recorded in the deviations log before running) is: training episodes (if the pilot shows earlier plateau) →
alternate-configuration seeds 10 → 5 → A6 seeds 10 → 5. The main sweep, A1–A4 and the 10-seed rule for primary outcomes are not
cut. `--quick` mode: 2 seeds, 1,000 episodes, 20 test instances, all blocks once (< 10 min).
