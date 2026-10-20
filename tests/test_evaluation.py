"""Evaluation tests with synthetic ground truth: matched-FPR calibration, sequential theory,
multi-chart calibration, max-vs-accumulator sanity, double counting, Logit-ROC, length-aware
thresholds, per-context allocation."""
import numpy as np
import pytest
from scipy.special import expit, logit

from amd.detectors import (CUSUM, ConformalEProcess, EDetectorSR, LengthAwareMax, Max,
                           MultiChart, WindowGLR, Whiten, default_suite)
from amd.evaluation import (alarm_times, arl0_simulation, calibrate, cfar_thresholds,
                            conformal_threshold, delay_summary, delay_table, evaluate_thresholds,
                            global_threshold, logit_roc_extrapolate, matched_budget_eval,
                            max_detection_allocation, partially_pooled_thresholds,
                            randomized_threshold, simple_matched, stackelberg_thresholds)
from amd.evaluation.synthetic import cumulative_judgment, inject, noise_streams, quantize

ALPHA = 0.05


def _suite_eval(kind, method, seed):
    rng = np.random.default_rng(seed)
    ar = 0.5 if kind == "ar1" else 0.0
    h = noise_streams(3000, (5, 25), rng, ar=ar)
    a, on = inject(noise_streams(600, (5, 25), rng, ar=ar), rng, "shift", 1.0)
    if kind == "int":
        h, a = quantize(h), quantize(a)
    df = matched_budget_eval(default_suite(supervised=True), h, a, alphas=[ALPHA],
                             attack_onsets=on, n_splits=2, crossfit=3, n_boot=50,
                             method=method, seed=seed)
    return df[df.threshold_kind == "calibrated"]


@pytest.mark.parametrize("kind,method", [("gauss", "conformal"), ("ar1", "conformal"),
                                         ("int", "conformal"), ("int", "randomized")])
def test_calibrated_fpr_matches_target_for_every_detector(kind, method):
    """Realized FPR on fresh honest test streams ~ alpha for all detectors (2 splits x 1500
    test streams; binomial + calibration sd ~ 0.006). Integer scores: the conformal rule is
    conservative (ties), the randomized rule restores ~alpha."""
    df = _suite_eval(kind, method, seed={"gauss": 1, "ar1": 2, "int": 3}[kind])
    assert len(df) == len(default_suite(supervised=True))
    tol = 0.022
    # statistics with few distinct values: the conformal rule is conservative (ties)
    discrete = {"count>q0.95"} | ({"max", "lr_max", "kth2", "kth3", "max_lenaware"}
                                  if kind == "int" else set())
    for _, r in df.iterrows():
        assert r.fpr <= ALPHA + tol, (r.detector, r.fpr)
        if method == "randomized" or r.detector not in discrete:
            assert r.fpr >= ALPHA - tol, (r.detector, r.fpr)
        assert r.fpr_lo <= r.fpr <= r.fpr_hi + 1e-12 and r.tpr_lo <= r.tpr_hi


def test_threshold_rules_discrete():
    rng = np.random.default_rng(0)
    cal = rng.integers(0, 4, 1000).astype(float)  # 4 values, massive ties
    test = rng.integers(0, 4, 200000).astype(float)
    thr_c = conformal_threshold(cal, 0.1)
    thr_r = randomized_threshold(cal, 0.1)
    assert thr_c.rate(test) <= 0.1  # conservative
    assert abs(thr_r.rate(test) - 0.1) < 0.02  # randomized hits alpha up to sampling error
    assert conformal_threshold(np.arange(50.0), 0.001).h == np.inf  # alpha below 1/(n+1)
    # continuous: conformal realized FPR <= alpha in expectation over calibration draws
    fprs = [calibrate(rng.normal(size=99), 0.05).rate(rng.normal(size=2000)) for _ in range(300)]
    assert np.mean(fprs) <= 0.05 + 0.003


def test_eprocess_anytime_validity():
    """Ville: P(sup_t E_t >= 1/alpha) <= alpha under i.i.d. honest units, for every length."""
    rng = np.random.default_rng(10)
    cal = noise_streams(200, 50, rng)  # 10k calibration units
    test = noise_streams(4000, 300, rng)
    for c in ("power", "powerint", "linear", "jumper"):
        e = ConformalEProcess(c).fit(cal)
        s = e.stats(test)
        for a in (0.1, 0.02):
            fpr = np.mean(s >= e.analytic_threshold(a))
            assert fpr <= a + 2.5 * np.sqrt(a * (1 - a) / len(test)), (c, a, fpr)
    # randomized p-values keep validity too
    e = ConformalEProcess("power", randomize=True, seed=0).fit(cal)
    assert np.mean(e.stats(test) >= np.log(10)) <= 0.1 + 0.012
    # SR e-detector: alarm at 1/alpha has ARL0 >= 1/alpha
    sr = EDetectorSR("power").fit(cal)
    r = arl0_simulation(sr, np.log(100), noise_streams(300, 50, rng), n_sims=150, sim_length=2000)
    assert r["arl0"] >= 100


def test_eprocess_ville_invalid_under_dependence():
    """Documented assumption: with strongly autocorrelated honest units (history-aware
    monitor) the Ville threshold no longer controls FPR; empirical calibration still does."""
    rng = np.random.default_rng(11)
    cal = cumulative_judgment(noise_streams(1000, 60, rng), rho=0.95)
    test = cumulative_judgment(noise_streams(3000, 60, rng), rho=0.95)
    e = ConformalEProcess("power").fit(cal)
    assert np.mean(e.stats(test) >= e.analytic_threshold(0.05)) > 0.1
    thr, fpr, *_ = simple_matched(ConformalEProcess("power"), cal, test, test[:5], 0.05)
    assert abs(fpr - 0.05) < 0.02


def test_cusum_delay_matches_theory():
    """i.i.d. N(mu,1) after the change from S=0: E[delay] ~ h/(mu-k) (Siegmund-corrected
    value (exp(-2D b) + 2 D b - 1)/(2 D^2), D = mu - k, b = h + 1.166)."""
    rng = np.random.default_rng(12)
    mu, k, h = 1.0, 0.5, 10.0
    d = CUSUM(k, transform=None).fit([[0.0]])
    t = alarm_times(d, [rng.normal(mu, 1, 300) for _ in range(3000)], h)
    n_samples = (t + 1).mean()
    D, b = mu - k, h + 1.166
    siegmund = (np.exp(-2 * D * b) + 2 * D * b - 1) / (2 * D**2)
    assert 0.95 < n_samples / (h / D) < 1.15
    assert abs(n_samples / siegmund - 1) < 0.05
    # design k = delta/2
    assert CUSUM.design(1.4).k == pytest.approx(0.7)


def test_cusum_arl0():
    """Page CUSUM k=0.5, h=4 on N(0,1): ARL0 ~ 336 (Siegmund approx 338)."""
    rng = np.random.default_rng(13)
    d = CUSUM(0.5, transform=None).fit([[0.0]])
    pool = noise_streams(6000, 50, rng)  # the honest pool size limits ARL precision
    r = arl0_simulation(d, 4.0, pool, n_sims=500, sim_length=3000, seed=1)
    assert 285 < r["arl0"] < 390 and r["censored_frac"] < 0.02
    rb = arl0_simulation(d, 4.0, pool[:500], n_sims=100, sim_length=3000, seed=2, n_boot=20)
    assert rb["arl0_lo"] < rb["arl0_hi"]


def test_multichart_joint_calibration():
    rng = np.random.default_rng(14)
    cal, test = noise_streams(3000, (10, 30), rng), noise_streams(6000, (10, 30), rng)
    shift, _ = inject(noise_streams(800, (10, 30), rng), rng, "shift", 0.8)
    spike, _ = inject(noise_streams(800, (10, 30), rng), rng, "spike", 4.5)
    comps = [Max(), CUSUM(0.5), ConformalEProcess("power")]
    thr, fpr, _, mc, _ = simple_matched(MultiChart(comps), cal, test, shift, ALPHA)
    assert abs(fpr - ALPHA) < 0.012
    # naive: each component at alpha separately -> OR exceeds the budget
    alarms = np.zeros(len(test), bool)
    for c in comps:
        t, *_ , dd, s = simple_matched(c, cal, test, shift, ALPHA)
        alarms |= s["test"] > t.h
    assert alarms.mean() > 1.6 * ALPHA
    # OR is close to the best component on each attack type
    tpr = {}
    for name, d in [("max", Max()), ("cusum", CUSUM(0.5)), ("or", MultiChart(comps))]:
        _, _, ts, *_ = simple_matched(d, cal, test, shift, ALPHA)
        _, _, tp, *_ = simple_matched(d, cal, test, spike, ALPHA)
        tpr[name] = (ts, tp)
    assert tpr["or"][0] > tpr["max"][0] + 0.15 and tpr["or"][1] > tpr["cusum"][1] + 0.15
    assert tpr["or"][0] > tpr["cusum"][0] - 0.12 and tpr["or"][1] > tpr["max"][1] - 0.12


def test_sustained_shift_favors_accumulators_spike_favors_max():
    rng = np.random.default_rng(15)
    cal, test = noise_streams(2000, (20, 40), rng), noise_streams(2000, (20, 40), rng)
    shift, _ = inject(noise_streams(1000, (20, 40), rng), rng, "shift", 0.6, onset=0.3)
    spike, _ = inject(noise_streams(1000, (20, 40), rng), rng, "spike", 4.0)
    ramp, _ = inject(noise_streams(1000, (20, 40), rng), rng, "ramp", 1.0, onset=0.3, ramp_len=10)
    res = {}
    for d in [Max(), CUSUM(0.5), ConformalEProcess("power"), WindowGLR(20)]:
        res[d.name] = [simple_matched(d, cal, test, x, ALPHA)[2] for x in (shift, spike, ramp)]
    for acc in ("cusum_k0.5", "eproc_power"):
        assert res[acc][0] > res["max"][0] + 0.1, res
        assert res[acc][1] < res["max"][1] - 0.2, res
    assert res["cusum_k0.5"][2] > res["max"][2] + 0.1


def test_history_aware_double_counting():
    """Same innovations seen by an innovation monitor (i.i.d. honest scores) vs a
    history-aware monitor (cumulative judgment, AR rho=0.95, same N(0,1) marginals).
    History-awareness inflates the accumulators' calibrated thresholds and flips the
    ranking: CUSUM >> max on innovations, max > CUSUM on cumulative-judgment scores."""
    rng = np.random.default_rng(16)
    L = (20, 40)
    cal, test = noise_streams(2000, L, rng), noise_streams(2000, L, rng)
    att, _ = inject(noise_streams(1500, L, rng), rng, "shift", 0.5, onset=0.3)
    hist = lambda s: cumulative_judgment(s, rho=0.95)
    out = {}
    for view, f in [("innov", lambda s: s), ("hist", hist)]:
        for d in [Max(), CUSUM(0.5), ConformalEProcess("power")]:
            thr, fpr, tpr, *_ = simple_matched(d, f(cal), f(test), f(att), 0.02)
            out[(view, d.name)] = (tpr, thr.h)
    # thresholds of accumulators inflate several-fold; max's threshold does not
    assert out[("hist", "cusum_k0.5")][1] > 4 * out[("innov", "cusum_k0.5")][1]
    assert out[("hist", "eproc_power")][1] > 4 * out[("innov", "eproc_power")][1]
    assert out[("hist", "max")][1] < 1.1 * out[("innov", "max")][1]
    # accumulation helps on innovations, hurts on history-aware scores
    assert out[("innov", "cusum_k0.5")][0] > out[("innov", "max")][0] + 0.2
    assert out[("hist", "max")][0] > out[("hist", "cusum_k0.5")][0] + 0.04
    assert out[("hist", "max")][0] > out[("hist", "eproc_power")][0] + 0.04


def test_logit_roc_extrapolation():
    """Logistic location shift: logit(TPR) = d + logit(FPR) exactly (slope 1)."""
    rng = np.random.default_rng(17)
    d = 3.0
    h = rng.logistic(0, 1, 5000)
    a = rng.logistic(d, 1, 5000)
    df = logit_roc_extrapolate(h, a, target_fprs=(1e-3, 1e-4), n_boot=100)
    truth = expit(d + logit(np.array([1e-3, 1e-4])))
    assert abs(df.slope.iloc[0] - 1) < 0.15 and df.r2.iloc[0] > 0.97
    for j in range(2):
        assert df.tpr_lo[j] <= truth[j] <= df.tpr_hi[j]
        assert abs(df.tpr_hat[j] - truth[j]) < 0.5 * truth[j]
    assert df.extrapolation_factor[1] >= 10


def test_length_aware_max():
    rng = np.random.default_rng(18)
    lens = (2, 100)
    cal, test = noise_streams(4000, lens, rng), noise_streams(8000, lens, rng)
    Ltest = np.array([len(s) for s in test])
    short, long_ = Ltest <= 20, Ltest >= 70
    # plain max with one global threshold: FPR grows with length
    t, _, _, _, s = simple_matched(Max(), cal, test, test[:5], ALPHA)
    f_short, f_long = t.rate(s["test"][short]), t.rate(s["test"][long_])
    assert f_long > 2 * f_short
    # length-aware analytic threshold: ~alpha at every length
    d = LengthAwareMax().fit(cal)
    assert abs(d.theta_ * 50**d.beta_ - 50) < 10  # i.i.d.: L_eff ~ L
    st = d.stats(test)
    h = d.analytic_threshold(ALPHA)
    for m in (short, long_):
        assert abs(np.mean(st[m] > h) - ALPHA) < 0.02
    # AR(1) honest streams: fewer effective units than L
    ar = LengthAwareMax().fit(noise_streams(3000, lens, rng, ar=0.8))
    assert ar.theta_ * 50**ar.beta_ < 0.7 * 50


def test_delay_table_and_summary():
    df = delay_table([5, -1, 2, 9], onsets=[3, 3, 4, 3], harm_steps=[6, 6, 6, None])
    assert list(df.alarm) == [True, False, True, True]
    assert list(df.early) == [False, False, True, False]
    assert df.delay[0] == 2 and np.isnan(df.delay[2])
    assert df.before_harm[0] == 1 and df.before_harm[1] == 0 and np.isnan(df.before_harm[3])
    s = delay_summary(df)
    assert s["detection_rate"] == 0.75 and s["before_harm_rate"] == pytest.approx(2 / 3)


def test_matched_eval_grouped_cluster_bootstrap():
    rng = np.random.default_rng(19)
    h = noise_streams(600, 20, rng)
    a, _ = inject(noise_streams(200, 20, rng), rng, "shift", 1.0)
    hg = rng.integers(0, 40, 600)
    ag = rng.integers(0, 20, 200)
    df, raw = matched_budget_eval({"max": Max(), "cusum": CUSUM(0.5)}, h, a, alphas=[0.05, 0.01],
                                  honest_groups=hg, attack_groups=ag, cluster_bootstrap=True,
                                  n_splits=3, n_boot=100, return_raw=True)
    assert set(df.detector) == {"max", "cusum"} and len(df) == 4
    for r in raw:  # grouped split: no task in both calibration and test
        assert not set(hg[r["cal_idx"]]) & set(hg[r["test_idx"]])
    assert (df.tpr_lo <= df.tpr).all() and (df.tpr <= df.tpr_hi).all()


def _ctx_data(rng, n_h, n_a):
    # contexts differ in honest level and spread; attacks add the same shift everywhere, so
    # the noisy context is the hardest to detect in at equal FPR
    spec = {"quiet": (0.0, 1.0), "mid": (0.7, 1.0), "noisy": (1.0, 2.0)}
    H = {c: rng.normal(m, sd, n_h) for c, (m, sd) in spec.items()}
    A = {c: rng.normal(m + 2.5, sd, n_a) for c, (m, sd) in spec.items()}
    return H, A


def test_per_context_allocations():
    rng = np.random.default_rng(20)
    H, A = _ctx_data(rng, 3000, 1000)
    Ht, At = _ctx_data(rng, 3000, 1000)
    B = 0.03
    rules = {
        "global": global_threshold(H, B),
        "cfar": cfar_thresholds(H, B),
        "pooled": partially_pooled_thresholds(H, B, n0=200),
        "maxdet": max_detection_allocation(H, A, B),
        "stackel": stackelberg_thresholds(H, A, B),
    }
    cal = {k: evaluate_thresholds(v, H, A) for k, v in rules.items()}
    test = {k: evaluate_thresholds(v, Ht, At) for k, v in rules.items()}
    for k in rules:  # every rule spends (about) the same global audit budget
        assert cal[k]["budget_used"] <= B + 1e-9 or k == "cfar"
        assert abs(test[k]["budget_used"] - B) < 0.008, k
    # CFAR equalizes per-context FPR; global does not
    assert test["cfar"]["fpr_spread"] < 0.015 < test["global"]["fpr_spread"]
    # on calibration data the optimizers attain their objectives exactly
    assert cal["maxdet"]["uniform_tpr"] >= max(cal[k]["uniform_tpr"] for k in rules) - 1e-9
    assert cal["stackel"]["attacker_payoff"] <= min(cal[k]["attacker_payoff"] for k in rules) + 1e-9
    assert test["stackel"]["attacker_payoff"] < test["cfar"]["attacker_payoff"] - 0.02
    # pooled thresholds sit between global and CFAR
    hq = {k: rules[k]["noisy"].h for k in ("global", "pooled", "cfar")}
    assert hq["global"] <= hq["pooled"] <= hq["cfar"]


def test_stackelberg_with_damage():
    rng = np.random.default_rng(21)
    H, A = _ctx_data(rng, 2000, 800)
    dmg = {"quiet": 1.0, "mid": 1.0, "noisy": 3.0}
    th = stackelberg_thresholds(H, A, 0.03, damage=dmg)
    ev = evaluate_thresholds(th, H, A, damage=dmg)
    ev_cfar = evaluate_thresholds(cfar_thresholds(H, 0.03), H, A, damage=dmg)
    assert ev["attacker_payoff"] < ev_cfar["attacker_payoff"]
    pc = ev["per_context"].set_index("context")
    assert pc.loc["noisy", "tpr"] > ev_cfar["per_context"].set_index("context").loc["noisy", "tpr"]
