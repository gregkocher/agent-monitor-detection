# Track 2: per-context thresholds for AI-agent monitors

The full write-up is the PDF `~/Desktop/monitoring-research/reports/02_Idea2_Per_Context_Thresholds.pdf`. All numbers are in `results/t2/tables.md` and the CSVs; figures are in `results/t2/figures/`.

## Key findings

1. **Heterogeneity is real across deployments and small within one.**
   - Across 7 deployments sharing one monitor and rubric, a global 5% threshold gives 0–9% per-context FPR (τ = 1.34 logit, p < 0.001). Across ControlArena setting × agent it is 0–16%.
   - Within LinuxArena it is 2–7% across environments. Agent model has no effect.
   - Environment effects are shared across all 12 sweep monitors (mean Spearman 0.70).
2. **CFAR (constant FPR per context) is the worst rule against an attacker who picks its context.**
   - 7 settings, B = 1%: 0.40 vs 0.64 for global.
   - ControlArena: 0.22 vs 0.60.
3. **Damage-equalizing Stackelberg thresholds are best against attack selection.**
   - 7 settings: 0.79 vs 0.64 at 1%, and 0.97 vs 0.89 at 5%.
   - Cost: ≤ 0.02 TPR against a uniform attacker.
4. **Per-context quantiles fail with few honest runs per context.**
   - Plug-in quantiles spend ≈ 1/(n+1), i.e. 7× budget at n = 10.
   - Mondrian conformal never alarms when n < 1/B.
   - Partial pooling with CV-chosen n0 stays near budget.
5. **Poisoning.**
   - CFAR breaks once the poisoned share ε ≈ B: at ε = 2%, TPR in the poisoned context falls from 0.95 to 0.37.
   - OS-CFAR with a leave-one-context-out tail holds 0.77–0.86 and still tracks genuine drift.
   - Outlier filters only slow down a boiling-frog attack.

Spend: $17.11.
