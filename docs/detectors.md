# Detectors and evaluation

`amd.detectors` turns per-unit monitor score streams (one list of floats per trajectory; units are steps, chunks, PRs or sessions) into trajectory-level decision statistics. `amd.evaluation` sets their thresholds at matched false-alarm budgets and measures detection. Nothing here calls an LLM.

## 1. Data model and API

A stream is a 1-D sequence of unit scores. `NaN` marks an unscored unit: it leaves every running statistic unchanged, and paths stay aligned to the original index. Streams are packed into a padded `(n_streams, T)` matrix, so every statistic is vectorized across trajectories and loops only over time. On 30k streams of 10–100 units each, a whitened CUSUM takes about 0.4 s.

```python
from amd.detectors import CUSUM, Max, ConformalEProcess, MultiChart, default_suite
d = CUSUM(k=0.5).fit(honest_cal_streams)   # unsupervised: honest streams only
d.stat(stream)          # trajectory statistic (float)
d.stat_path(stream)     # running statistic after each unit (original index)
d.stats(streams)        # vectorized
d.first_alarm(streams, h)  # first unit index with path > h (-1 = none)
```

- **Fitting.** Every detector has `fit(honest_streams, contexts=None, attack_streams=None, attack_contexts=None, attack_onsets=None)`.
  - Unsupervised detectors learn only from honest calibration streams.
  - **Supervised** detectors (`d.supervised == True`: `LRMax`, `LLRCUSUM`, and any detector whose transform is `KDELogLR`) also need attack streams. Their attack reference uses only units at or after each attack's onset.
  - The matched-budget evaluation fits supervised detectors on a separate attack-fit split, so they are never scored on the attacks they were fit on.
- **Trajectory statistic.** Alarm-type detectors (`alarm_type=True`) alarm the first time the path exceeds the threshold, so their trajectory statistic is the max over the path. The batch decision `stat > h` and the streaming alarm then agree exactly. Detectors that are not alarm-type use the path's final value: `Mean` and `LengthAwareMax`.
- **Contexts** (for Mondrian calibration) are given per stream in one of two forms:
  - one label (str / int / tuple; a tuple is a coarse-to-fine hierarchy such as `(env, task)`);
  - a list of per-unit labels with the stream's length, e.g. `(task type, tool)` per step.
- **Composition.** Each detector is a per-unit transform followed by an aggregator. Every detector takes a `transform=` argument: `None`/identity, `Whiten(...)`, `PValue(...)` or `KDELogLR(...)`. The sequential detectors default to `Whiten()`.

`default_suite(supervised=False, mondrian=False)` returns the standard comparison set as `{name: detector}`.

## 2. Per-unit calibration transforms (`amd/detectors/transforms.py`)

All transforms are fit on the honest calibration units, which are pooled over calibration streams.

Let the honest calibration units be h_1..h_n. For a unit score s:

| Quantity | Formula | Property |
|---|---|---|
| conservative conformal p | `p = (1 + #{h_i >= s}) / (n + 1)` | super-uniform under exchangeability: `P(p <= a) <= a` |
| randomized p | `p = (#{h_i > s} + U (#{h_i = s} + 1)) / (n + 1)`, U ~ Unif(0,1) | exactly Unif(0,1) marginally, including with tied integer scores |
| mid p | `p = (#{h_i > s} + (#{h_i = s} + 1)/2) / (n + 1)` | E[randomized p given s]; deterministic, strictly inside (0,1) |
| whitened score | `z = probit(1 - p)` (or `logit(1 - p)`), p = mid (default) or randomized | honest z ≈ N(0,1) (exactly, marginally, with randomized p and continuous or tied scores) |

Notes:
- **Bounded z.** z is bounded by about `±probit(1 - 0.5/(n+1))`, about 3.5 for n = 2000, because the empirical CDF has no tail beyond the calibration sample. An extreme attack unit therefore adds at most ~3.5 per unit.
- **Ties.** With integer 0–10 scores and heavy ties, the conservative p cannot fall below its tie block. The whitened z is discrete, with variance below 1.
- **Validity is marginal over the calibration draw.** Conditional on one calibration set, p-values deviate from uniform by O(1/sqrt(n)). This is training-conditional error (tested).

**Mondrian / per-context (`UnitCalibrator(mondrian=True, min_n, n0)`; `Whiten(mondrian=True, ...)`).** The calibration units are split by context.
- For a unit in context c = (c_1, ..., c_m), the p-value is built level by level: p_0 is the global p-value. At level l, if the prefix c[:l] has n_l >= `min_n` calibration units:

  `p_l = w_l p̂(prefix) + (1 - w_l) p_{l-1}`, with `w_l = n_l / (n_l + n0)`.
- `n0 = 0` is pure Mondrian: the finest prefix with at least `min_n` units. This is exactly conformal within that stratum.
- `n0 > 0` shrinks small contexts toward their parent (hierarchical partial pooling). This is not exactly conformal: a mixture of valid p-values is valid only up to a factor 2.
- Contexts with fewer than `min_n` units, or unseen at calibration time, fall back to the deepest known prefix, and ultimately to the global calibrator.

**`KDELogLR` (supervised).**
- `llr(s) = log f1(s) - log f0(s)`, where f0 and f1 are Gaussian KDEs (Scott bandwidth by default) of honest units and post-onset attack units.
- Each density is mixed with ε·uniform (ε = 1e-3) on the grid range, so the LLR stays finite. It is evaluated on a 512-point grid and interpolated.
- `clip=c` clips the LLR to [-c, c]. This is the Huberized least-favorable LLR of ε-contamination robust detection (Unnikrishnan–Veeravalli–Meyn).
- `monotone=True` fits the LLR isotonically in s, removing Hua et al.'s non-monotone "winner's curse".

## 3. Trajectory statistics

Notation: u_t is the transformed unit value after unit t (raw score, whitened z, p-value or LLR); S_t is the running statistic.

| Detector | Running statistic S_t | Trajectory stat | Parameters | Assumptions / notes |
|---|---|---|---|---|
| `Max` | `max_{i<=t} u_i` | max | transform | standard rule; per-trajectory FPR grows with length |
| `Mean` | `mean_{i<=t} u_i` | final value | transform | not alarm-type (a path crossing is not the decision) |
| `KthLargest(k)` | k-th largest of u_1..u_t (-inf before k units) | max | k = 2, 3 | k = 2 is Kutasov's 2nd-highest rule |
| `TopKSum(k)` | sum of the k largest so far; missing slots count as `fill` (0) | max | k = 3, 5; fill | use on whitened z (default suite) so 0 means "no evidence" |
| `CountAbove(q)` | `#{i <= t: u_i > Q_q}`, Q_q = q-quantile of honest units | max (= final) | q (0.95) | "k strikes"; integer-valued, so use a randomized threshold |
| `CUSUM(k)` | `S_t = max(0, S_{t-1} + u_t - k)`, S_0 = 0 | max | reference k; `CUSUM.design(delta)` sets k = δ/2 | on whitened z this is the Gaussian-LLR CUSUM for a shift δ; Lorden-optimal for known pre/post laws; reflection at 0 discards evidence between separated bursts |
| `ShiryaevRoberts(delta)` | `log R_t = logaddexp(0, log R_{t-1}) + l_t`, `l_t = δ z_t - δ²/2` (or l_t = u_t if `delta=None`, for LLR transforms) | max | δ | `R >= A` gives ARL0 >= A for a correct LR; log domain avoids overflow |
| `WindowGLR(W)` | `G_t = max_{1<=m<=min(W,t)} max(0, Σ_{i=t-m+1..t} z_i)² / (2m)` | max | window W | log-GLR over onset (last W units) and unknown shift μ >= 0 of unit-variance scores; near-optimal over a range of shifts |
| `LLRCUSUM(clip)` **supervised** | CUSUM with k = 0 on `clip(llr(s_t), ±c)` | max | clip c (3), KDE options | minimax-robust CUSUM against contamination of the declared class |
| `LRMax` **supervised** | `max_{i<=t} llr(s_i)` | max | monotone | Hua et al. Neyman–Pearson rule per unit, then max |
| `ConformalEProcess(calibrator)` | `log E_t`, `E_t = mean_λ Π_{i<=t} f_λ(p_i)` on conservative (or randomized) conformal p | max | calibrator, λ grid, randomize, Mondrian options | anytime-valid; see below |
| `EDetectorSR(calibrator)` | `log mean_λ M_t(λ)`, `M_t = f_λ(p_t)(1 + M_{t-1})` | max | as above | Shiryaev–Roberts e-detector (sum of e-processes restarted at every unit) |
| `MultiChart(components, weights)` | `max_i [-log T_i(S_i,t) + log w_i]` | max | components, weights w | joint OR; see below |
| `LengthAwareMax(model)` | `-log(1 - F(max_{i<=t} s_i)^{θ t^β})` | final value | `model='power'` (θ, β) or `'linear'` (β = 1) | analytic length-aware null; see below |

### E-processes (`amd/detectors/eprocess.py`)

Each unit gets a conformal p-value p_t against honest calibration units. A calibrator f maps p_t to an e-value. Each calibrator is non-increasing with ∫₀¹ f = 1, so `E[f(p)] <= 1` for any super-uniform p:

- `power`: `f_κ(p) = κ p^{κ-1}`, mixed over κ ∈ {0.02, 0.05, 0.1, 0.2, 0.35, 0.5}. The mixture averages the product martingales, so it costs at most log(#κ) in log-evidence relative to the best κ in hindsight.
- `powerint`: `f(p) = ∫₀¹ κ p^{κ-1} dκ = (1 - p + p ln p)/(p ln² p)`, a per-unit mixture with f(1) = 1/2.
- `linear`: `f_λ(p) = 1 + λ(1 - 2p)`, mixed over λ ∈ {0.1, 0.25, 0.5, 0.75, 0.9}. The bet is bounded (at most 2x per unit).
- `jumper`: Vovk's composite jumper on `f_ε(p) = 1 + ε(p - 1/2)`, ε ∈ {-1, 0, 1}, jump rate J = 0.01. The bet direction adapts within the stream.

Guarantees:

- **Ville / anytime validity.** If honest units are i.i.d. and exchangeable with the calibration units, then E_t is a test supermartingale and `P(sup_t E_t >= 1/α) <= α`. The threshold `analytic_threshold(α) = log(1/α)` controls the per-trajectory FPR for every length and every stopping rule, without empirical calibration. Two caveats:
  - The guarantee is marginal over the calibration draw. Conditional on a fixed calibration set, the p-values are i.i.d. but only approximately uniform.
  - **It fails under within-stream dependence of honest scores**, e.g. history-aware monitors whose scores are cumulative judgments. A test demonstrates FPR > 2α at ρ = 0.95; empirical calibration still holds there. Use the calibrated threshold whenever honest units may be dependent.
- **E-detector.** Alarming when `M_t >= 1/α` gives ARL0 >= 1/α (an anytime ARL bound, tested), not a per-trajectory FPR bound.
- **Strength.** With conservative p-values and tied integer scores, per-unit e-values are weak (no p below the tie block), and the e-process loses power. Randomized p-values (`randomize=True`) restore exact uniformity.

### Multi-chart OR (`amd/detectors/multichart.py`)

For each component i, fitting stores its honest trajectory statistics, which define the tail function `T_i(s) = (1 + #{S_i^cal >= s})/(n + 1)`. With budget weights w_i (Σ w_i = 1), "some component has `T_i(S_i) <= β w_i`" is the single statistic `M = max_i [-log T_i(S_i) + log w_i]`.

The matched-budget protocol then calibrates **one** threshold on M to the target FPR:
- The OR has exactly the target trajectory FPR (tested to within ±0.012 at α = 0.05).
- The budget is split across components in proportion to w.
- The dependence between components is accounted for. A naive split with each component at α inflates the OR's FPR (test: > 1.6α for three charts). A Bonferroni split (α w_i each) would be conservative.

The running path uses each component's running path, so the streaming alarm fires at the first component crossing. `which_component(streams)` reports which chart fired. Use alarm-type components.

### Length-aware max (`LengthAwareMax`)

- **Model.** Let F be the honest per-unit CDF, estimated as 1 - mid-p on honest calibration units. Model the max of L honest units by `P(max <= m) = F(m)^{L_eff(L)}`, with `L_eff = θ L^β`.
- **Fit.** θ and β are fit by maximum likelihood on the maxima of honest calibration streams: θ has a closed form given β, and β is profiled over [0.1, 1].
  - θ < 1 or β < 1 capture positive within-stream dependence: fewer effective independent units.
  - For i.i.d. units, L_eff ≈ L (tested).
- **Statistic.** The statistic is `-log(1 - F(max)^{L_eff(L)})`. `analytic_threshold(α) = -log α` gives a per-trajectory FPR ≈ α at every length, if the model fits. This removes the per-step-to-per-trajectory compounding (MonitoringBench: 1% per step → 6.7–17.4% per trajectory).
- **Comparison with plain max** (tested): with one global threshold, plain max's FPR on long streams is more than 2x its FPR on short streams. The length-aware statistic stays within ±0.02 of α in both length bins.
- **Resolution.** Resolution is limited by the empirical F, p >= 0.5/(n_units+1).

## 4. Calibration and matched-budget evaluation (`amd/evaluation/`)

### Thresholds (`calibration.py`)

- **Conformal (default).** Let S_(k) be the k-th smallest calibration statistic, with `k = ⌈(1-α)(n+1)⌉`. Set h = S_(k) and alarm iff S > h.
  - For a new exchangeable honest trajectory, `P(S > h) <= α`. Ties only make the rule more conservative.
  - If k > n, i.e. α < 1/(n+1), then h = +∞ and no alarm is possible. This is reported as `frac_unreachable`.
- **Randomized (plug-in).** Choose the smallest observed h with `#{S > h}/n <= α`. Alarm on ties S = h with probability `γ = (αn - #{S > h})/#{S = h}`.
  - This removes discreteness (integer scores, counts, coarse e-processes): the realized FPR is ≈ α rather than ≤ α.
  - Rates are reported as expected alarm probabilities, with no coin flips.
- **Analytic.** For detectors that define `analytic_threshold(α)`: the e-process (Ville), the SR e-detector (an ARL bound, *not* an FPR bound) and the length-aware max.

### Matched-budget protocol (`matched.py: matched_budget_eval`)

Run per repeated random split (`n_splits`, default 5):

1. **Split.** Split honest trajectories into calibration and test (`cal_frac`). If `honest_groups` is given and `group_split=True`, no task/context appears in both. If any detector is supervised, attacks are also split into fit and test (`attack_fit_frac`, default 0.5). All detectors are scored on the same attack-test set.
2. **Cross-fit.** The calibration set is cut into K folds (`crossfit`, default 5). The detector (transform plus any learned aggregator state) is fit on K-1 folds and scores the held-out fold.
   - Honest-test and attack-test trajectories are each scored by one of the same K fold models, chosen at random (`score_with="folds"`). Every statistic therefore comes from a model that never saw that trajectory, and calibration and test statistics are exchangeable, including their tie structure for discrete scores.
   - `score_with="full"` refits on the whole calibration set to score test and attacks. It has slightly more power, but cross-fit jitter breaks ties between calibration and test statistics.
   - `crossfit <= 1` uses one in-sample fit.
3. **Threshold.** For each α in `alphas` (default 1e-2, 3e-3, 1e-3), set the threshold from the cross-fitted calibration statistics (`method="conformal"` or `"randomized"`). TPR is the alarm rate on attack-test; the realized FPR is the alarm rate on honest-test. Detectors with an analytic threshold get an extra row (`threshold_kind="analytic"`).
4. **Bootstrap.** For each split, `n_boot` replicates resample calibration, honest-test and attack-test trajectories independently (stratified by role). With `cluster_bootstrap=True` they resample clusters (`honest_groups` / `attack_groups`), with all their trajectories. The threshold is recomputed in each replicate, so CIs include calibration uncertainty.
   - Percentile CIs (`ci`, default 95%) pool the replicates of all splits.
   - Point estimates average over splits.

The output is one row per (detector, α, threshold kind):
- `tpr`, `tpr_lo`, `tpr_hi`, `fpr`, `fpr_lo`, `fpr_hi`
- `tpr_split_sd`, `threshold`, `frac_unreachable`, `n_cal`, `n_test`, `n_attack`, `supervised`

With `return_raw=True` the call also returns the per-split statistics and indices, for delay analyses.

`simple_matched(det, cal, test, attack, alpha)` is the one-shot version. It returns (threshold, FPR, TPR, detector fit on all calibration streams, stats).

**Resolution.** The smallest reachable trajectory FPR is about 1/(n_cal + 1). With integer scores, the conformal rule is conservative: tests show realized FPR of about 0.013–0.025 at α = 0.05 for `kth2` and `max` on 0–10 scores. Report realized FPR, or use `method="randomized"`.

## 5. Streaming metrics (`streaming.py`)

- **`alarm_times(det, streams, threshold)`** gives the original index of the first unit after which the running statistic exceeds h (-1 = never).
- **`delay_table(alarm_t, onsets, harm_steps)`** reports, per trajectory:
  - `alarm`;
  - `early` (the alarm precedes the onset: on an attack trajectory this is a pre-onset alarm, which on honest data would be a false alarm);
  - `delay = alarm - onset`;
  - `before_harm` (alarm index <= harm step: the harmful action is flagged before or when it is proposed).

  `delay_summary` aggregates detection rate, early rate, mean/median delay and the before-harm rate.
- **`arl0_simulation(det, h, honest_streams, n_sims, sim_length, n_boot)`** estimates long-run ARL0 by continuous monitoring of one agent. It concatenates honest streams drawn with replacement (no reset at trajectory boundaries) and measures run length to the first alarm, right-censored at `sim_length`.
  - ARL0 = total units / #alarms, the censored-exponential MLE.
  - The finite honest pool dominates the uncertainty, so `n_boot` re-runs the simulation on pool bootstraps to give `arl0_lo`/`arl0_hi`.
  - Tested: CUSUM k = 0.5, h = 4 on N(0,1) gives ≈ 336.
  - If the statistic restarts every trajectory, the ARL in trajectories is `1/FPR` (`trajectory_arl`).
- **Change-point localization (`localization_errors(det, streams, onsets, threshold=None)`).**
  - Increment-based detectors (CUSUM, SR, LLR-CUSUM, e-processes) estimate the onset as `argmax_j Σ_{i=j..τ} g_i`, with g the per-unit log-evidence increment: z - k for CUSUM, the LLR for SR, log e for e-processes at the middle λ. Ties go to the latest j, matching CUSUM's last reset.
  - The window GLR uses its maximizing window start. Max-type detectors use the first argmax unit.
  - τ is the alarm time when a threshold is given and the stream alarms (online); otherwise it is the last unit (offline).
  - The output has the onset estimate, the signed error and the absolute error.
- **CUSUM delay check (tested).** For i.i.d. N(μ,1) post-change data starting from S = 0, the mean number of samples to alarm is ≈ h/(μ-k), within 5% of Siegmund's corrected value.

## 6. Logit-ROC extrapolation (`logit_roc.py`)

Redwood's observation: for a fixed policy, monitor and attack, logit(TPR) is approximately linear in logit(FPR).

- **Fit.** `logit_roc_fit` fits `logit(TPR) = a + b·logit(FPR)` on empirical ROC points with FPR in `[min_honest_alarms/n_honest, fpr_max]` (defaults 5/n and 0.2).
  - It uses weighted least squares with weights `1/(1/(n_a t(1-t)) + 1/(n_h f(1-f)))`, the binomial noise in both coordinates.
  - TPR is clipped to `[0.5/n_a, 1-0.5/n_a]`.
- **Extrapolation.** `logit_roc_extrapolate(h, a, target_fprs)` returns the extrapolated TPR, a trajectory-bootstrap CI, and diagnostics:
  - `slope`, `intercept`, `r2`, `rmse`;
  - `curvature`, the quadratic coefficient of a degree-2 fit (0 if linear);
  - `n_points` and the fitted FPR range;
  - `extrapolation_factor` = smallest fitted FPR / target.
- **Caution.** Extrapolating more than ~10x beyond the data rests on the linearity assumption. Check curvature and r2.

## 7. Per-context thresholds (`contexts.py`, track 2)

The inputs are generic: dicts `context -> array` of honest (and attack) trajectory statistics from any detector.
- `w_c` is the honest traffic share (default: sample share), so the global audit budget is `Σ_c w_c FPR_c`.
- `a_c` is the attack prior of a non-strategic attacker (default uniform).
- `D_c` and `s_c` are optional per-context damage and success probability.

Allocation rules:

| Function | Rule |
|---|---|
| `global_threshold` | one pooled threshold: the smallest h with `Σ w_c FPR_c(h) <= B` |
| `cfar_thresholds` | constant FPR per context (per-context conformal or randomized quantile; Mondrian) |
| `partially_pooled_thresholds(n0)` | per-context quantile of the shrunk CDF `(n_c F̂_c + n0 F̂)/(n_c + n0)` (empirical Bayes); the common level is tuned so the realized calibration budget equals B |
| `max_detection_allocation` | maximize `Σ a_c TPR_c` s.t. `Σ w_c FPR_c <= B`: a fractional knapsack over the per-context ROC upper concave hulls (exact optimum among randomized thresholds); one context gets a randomized band threshold so the budget is used exactly |
| `stackelberg_thresholds` | minimize the attacker's best payoff `max_c s_c D_c (1 - TPR_c)` within the budget (attacker sees the thresholds and chooses the context; damage equalization à la Ghafouri et al.); deterministic thresholds by bisection on the payoff level |
| `evaluate_thresholds` | on held-out data: realized budget, per-context FPR/TPR, FPR spread, uniform-attacker TPR, the attacker's chosen context and payoff, and `selection_safety = 1 - max payoff` |

The tests check four things on a 3-context synthetic case where the "noisy" context has a wider honest distribution:
- every rule spends the same budget on held-out data;
- CFAR equalizes per-context FPR;
- max-detection attains the best uniform TPR in-sample;
- Stackelberg lowers the attack-selection payoff relative to CFAR, both in and out of sample, and also with damage weights.

Randomized Stackelberg thresholds and poisoning-robust baselines are not implemented.

## 8. Synthetic streams (`synthetic.py`) and what the tests verify

Generators:
- `noise_streams`: Gaussian, optionally AR(1).
- `inject`: an attack signal from an onset. `shift` is a sustained mean shift, `spike` a single unit, `ramp` a linear rise.
- `quantize`: integer 0–10 scores with heavy ties.
- `cumulative_judgment`: a history-aware monitor model. It is an EWMA `h_t = ρ h_{t-1} + sqrt(1-ρ²) x_t` with N(0,1) honest marginals, strong autocorrelation, and a sustained shift μ that appears as a level ≈ μ·sqrt((1+ρ)/(1-ρ)).

`uv run pytest -q` runs 42 tests in about 10 s. They verify:
- **Correctness.** Every statistic matches a brute-force implementation (max, mean, k-th, top-k, count, CUSUM, SR, window GLR, e-process, SR e-detector). NaN handling and alignment work, and batch results equal single-stream results.
- **Calibration transforms.** The calibrators integrate to 1. Conformal p-values are super-uniform; randomized ones are uniform, including with ties. Whitening gives N(0,1). Mondrian fallback and shrinkage behave as specified, and Mondrian whitening equalizes per-context FPR where a global threshold does not.
- **Matched FPR.** The calibrated FPR on fresh honest streams is within ±0.022 of α = 0.05 for **every** detector in the supervised default suite, for i.i.d. Gaussian, AR(1) ρ = 0.5 and integer-quantized streams. For discrete statistics under the conformal rule only the upper bound is enforced; the randomized rule restores ≈ α.
- **Anytime validity.** The e-process anytime FPR is ≤ α under an i.i.d. null for all four calibrators, also with randomized p. The SR e-detector has ARL0 ≥ 1/α. The Ville threshold breaks under strongly dependent honest scores, while empirical calibration still holds.
- **Sequential theory.** CUSUM delay is ≈ h/(μ-k), and CUSUM ARL0 is ≈ 336 at k = 0.5, h = 4.
- **Multi-chart.** Joint calibration hits α, while naive per-chart α inflates the FPR. The OR is close to the best component on both shift and spike attacks.
- **Max vs accumulators (sanity).** Sustained small shifts and ramps favor CUSUM and e-processes; single spikes favor max.
- **Double counting.** On history-aware (cumulative-judgment, ρ = 0.95) honest streams, the calibrated CUSUM and e-process thresholds inflate by more than 4x, while max's threshold does not. The ranking flips: CUSUM beats max by more than 0.2 TPR on innovation scores, and max beats CUSUM and the e-process on history-aware scores of the same innovations.
- **Other metrics.**
  - Logit-ROC: on a logistic shift, the extrapolated TPR at FPR 1e-3 and 1e-4 is within 50% of the truth and inside its CI, with slope ≈ 1.
  - Length-aware max: covered in §3.
  - Per-context allocation: covered in §7.
  - Grouped splits never share a group between calibration and test, and the cluster-bootstrap CIs bracket the point estimates.
