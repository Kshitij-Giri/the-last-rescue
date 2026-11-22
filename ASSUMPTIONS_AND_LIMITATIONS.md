# Assumptions and limitations

Every modelling assumption the results depend on, and every known limit on what the results show, in one place.
Where an assumption could be varied, the robustness experiment that tests it is named (R1-R7,
[`results/robustness/summary.md`](results/robustness/summary.md)). Numbers are test-set rescue fractions (RF), mean of
10 training seeds.

## Modelling assumptions

| # | Assumption | Why it was made | Tested by | Effect on the result |
|---|---|---|---|---|
| M1 | **Each agent has a private, non-transferable budget** that is never refilled. | Turns scarcity into a team allocation problem: an agent that spends its budget exploring may not be able to help later. | Pooled team budget (ablation) | Pooling raises RF slightly (Critical 0.129 vs 0.087); the decline with scarcity is just as strong. |
| M2 | **The static map is known in advance.** Walls, hazards and the base are known from t = 0; only victims must be found. The observation gives first moves on cheapest paths, so navigation is solved by the features and the learner chooses among planner directions and the non-move actions. | Keeps tabular learning tractable (3,960 observations). | Not varied | Results concern coordination and spending, not learning to navigate. In a real building the layout itself would be uncertain. |
| M3 | **No communication.** Agents see teammates' positions within radius 3 and nothing else (no budgets, memories or messages). | Isolates what independent learners can coordinate without a channel. | Not varied | Communication may change how scarcity affects cooperation; this study cannot say. |
| M4 | **Roles at a heavy victim are not signalled.** Two agents on the same heavy victim see the same observation, so nothing tells them who should RESCUE and who should ASSIST; two RESCUEs fail. | Follows from a compact observation without agent identity. | R2: one extra observation bit (lowest id on the cell) | Assist efficiency rises at Abundant (0.61 vs 0.45) but RF does not change beyond noise. |
| M5 | **The reward favours light victims for a selfish agent.** A solo light rescue pays 1.0 + 1.0 = 2.0 per agent; each role of a heavy rescue pays 0.5 + 1.0 = 1.5. | Individual credit is split between the two roles of a joint rescue. | R3: individual credit 1.0 per heavy role | Heavy rescues at Abundant rise (0.556 vs 0.422 of heavy victims); the decline with scarcity is unchanged. |
| M6 | **The cost term is small** (λ_C = 0.02, at most 1.28 per agent per episode), so scarcity acts mainly by ending episodes, not through the reward. | Keeps the reward identical at every budget level. | Not varied | Agents feel scarcity through shorter episodes and fewer options. |
| M7 | **Q-values start at 0 and WAIT is free**, which makes waiting a safe default. Learned teams WAIT in 53-63% of steps at every level. | Standard tabular initialisation. | R4: optimistic initial Q = 2.0 | Waiting at Abundant drops (46% vs 57%); RF unchanged. |
| M8 | **Dormant agents do not learn.** An agent with no budget left can only WAIT, so its steps are not used for updates, although it still receives team reward. | It has no choice to learn from. | R5: dormant agents also update | No change at any level. |
| M9 | **Budget buckets use absolute thresholds** (3, 16, 32 units), so Abundant and Moderate agents both start in the top bucket and a Critical agent (13 units) only sees the two lowest. | The same bucket means the same amount at every level. | R1: thresholds relative to each agent's own starting budget | The decline gets *stronger*: agents that can see their budget fall WAIT in 94% of steps at Critical. |
| M10 | **The budget scale comes from a hand-designed policy.** H = 105 and B_ref = 64 are percentiles of what the cooperative baseline needs with unlimited budget; "just enough" means just enough for that policy. | Gives ρ a concrete, measurable meaning. | Recalibration on 5 other configurations | ρ means nearly the same thing on 10 x 10 and 12 x 12 maps (cooperative RF within 0.08), not on 8 x 8 maps. |
| M11 | **The game ends at the horizon, and agents see time only in thirds.** The learner treats the horizon as terminal, so near it the observation is not Markov in time. | Coarse time keeps the table small. | Not varied | Mostly affects Abundant, where 90% of learned episodes end at the horizon; lower levels end by exhaustion. |
| M12 | **Heavy and light victims are fixed at 3 and 3** on a 10 x 10 grid with 3 agents. | One controlled configuration. | 12 x 12 configuration; all-light world (A3 analysis) | The decline appears in both. |

## Limitations

| # | Limitation | What it means for the conclusions |
|---|---|---|
| L1 | **No run converged.** None of the 40 main runs meets the stability criterion (policy churn < 5% and validation RF range < 0.02) after 8,000 episodes. | All results describe policies after a fixed training budget. Three times more training (R7) raises Abundant to 0.759 and Critical to 0.117: absolute levels change, the ordering does not. |
| L2 | **Ten seeds per condition.** The smallest possible two-sided Wilcoxon p is about 0.002. | Large, consistent effects are detected; small ones are not. Non-significant results (assist efficiency, territory division, spending Gini, IQL vs greedy at Critical) are inconclusive, not evidence of no effect. |
| L3 | **Two cooperation metrics depend on performance.** Productive spend share counts the cost of completed rescues, and the cooperation rate counts actions around joint rescues. | Their decline partly restates the fall in rescues. The metrics that do not depend on the number of rescues show no significant trend. |
| L4 | **Whether scarcity hurts cooperation specifically depends on the scale.** In points, the all-light world loses more under scarcity (DiD −0.248, 0/10 seeds positive); on a log scale the sign reverses. | No claim is made that the decline is specific to cooperation. |
| L5 | **The solo-training comparison (A4) has a confound**: solo agents never saw a teammate in training. | R6 removes it (agents trained beside scripted cooperative teammates) and the joint-training advantage remains. |
| L6 | **The greedy baseline is weak.** Its identical agents move in lockstep. | Beating it does not mean beating selfish behaviour in general. |
| L7 | **Calibration range.** The hardest level cannot go below ρ = 0.2: at ρ = 0.1 only 33% of maps allow any rescue. | Critical sits above its intended difficulty band; extreme scarcity is not studied. |
| L8 | **Cooperation-performance association is observational.** Seeds that cooperate more rescue more, but that analysis cannot show cause. | Causal statements rest only on the interventions (mismatched, removed and separately trained teammates). |
| L9 | **Robustness experiments R1-R7 were added after the main results.** | They are exploratory; their p-values are unadjusted and descriptive. |
| L10 | **Scope.** One environment family, three agents, tabular independent Q-learning with a hand-designed observation. | Other algorithms (for example centralised training with decentralised execution), larger teams or richer observations may respond to scarcity differently. The grid omits sensing noise, physics, dynamic obstacles and communication failures. |
