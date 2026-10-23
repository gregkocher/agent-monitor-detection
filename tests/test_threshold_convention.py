"""Threshold conventions: realized out-of-sample FPR of the plug-in randomized rule (historical default) and the
conformal randomized rule (smoothed conformal p-value), for continuous, integer-alpha*n and tied / discrete scores
(JEV-like probabilities rounded to 0.01)."""
import numpy as np
import pytest

from amd.evaluation import (calibrate, conformal_randomized_threshold, get_threshold_convention,
                            paired_gain_bootstrap, randomized_threshold, row_thresholds, threshold_convention)
from amd.evaluation.matched import _boot_threshold


def _cont(rng, k):
    return rng.random(k)


def _jev(rng, k):
    """JEV-like probabilities rounded to 0.01: heavy mass at 0.00-0.05, long right tail, many ties."""
    return np.round(rng.beta(0.4, 6.0, k), 2)


def _realized_fpr(gen, n, alpha, method, n_sim=12000, n_new=20, seed=0):
    rng = np.random.default_rng(seed)
    f = np.empty(n_sim)
    for i in range(n_sim):
        cal, new = gen(rng, n), gen(rng, n_new)
        f[i] = calibrate(cal, alpha, method).alarm_prob(new).mean()
    return f.mean(), f.std(ddof=1) / np.sqrt(n_sim)


@pytest.mark.parametrize("gen", [_cont, _jev], ids=["continuous", "jev_rounded"])
@pytest.mark.parametrize("n,alpha", [(100, 0.01), (200, 0.01), (100, 0.05), (137, 0.05), (60, 0.05)])
def test_conformal_randomized_realized_fpr_is_alpha(gen, n, alpha):
    m, se = _realized_fpr(gen, n, alpha, "conformal_randomized")
    assert abs(m - alpha) < 4.5 * se + 1e-4, (m, se)


@pytest.mark.parametrize("n,alpha", [(100, 0.01), (200, 0.01), (100, 0.05), (300, 0.01)])
def test_plugin_is_anticonservative_at_integer_alpha_n(n, alpha):
    """Continuous scores: plug-in out-of-sample FPR = (floor(alpha n) + 1)/(n + 1) > alpha."""
    m, se = _realized_fpr(_cont, n, alpha, "randomized")
    theory = (np.floor(alpha * n + 1e-9) + 1) / (n + 1)
    assert abs(m - theory) < 4.5 * se + 1e-4, (m, theory)
    assert m > alpha + 5 * se


def test_plugin_anticonservative_on_jev_scores():
    m, se = _realized_fpr(_jev, 100, 0.01, "randomized")
    assert m > 0.015, m          # ~0.0187 (ties soften the excess only slightly)


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("alpha", [0.01, 0.05, 0.1, 0.003])
def test_conformal_randomized_exact_leave_one_out(seed, alpha):
    """Exactness without simulation: for ANY multiset of n + 1 values (ties included), the average over which
    point is the new one of its alarm probability (the other n calibrate) equals alpha. Exchangeability then
    gives E[FPR] = alpha exactly."""
    rng = np.random.default_rng(seed)
    n1 = int(rng.integers(20, 250))
    vals = _jev(rng, n1) if seed % 2 else rng.integers(0, 6, n1).astype(float)
    p = [conformal_randomized_threshold(np.delete(vals, i), alpha).alarm_prob(vals[i:i + 1])[0] for i in range(n1)]
    assert np.isclose(np.mean(p), alpha, atol=1e-12)


def test_conformal_randomized_continuous_structure():
    """n = 100, alpha = 1% (integer alpha n): certain alarm above the 100th order statistic, band of
    probability frac(1.01) = 0.01 between the 99th and 100th, nothing below; in-sample rate below alpha."""
    s = np.arange(1, 101, dtype=float)
    t = conformal_randomized_threshold(s, 0.01)
    assert t.h == 100.0 and np.isclose(t.gamma, 0.01)
    assert t.alarm_prob(np.array([100.5]))[0] == 1.0
    assert np.isclose(t.alarm_prob(np.array([99.5]))[0], 0.01)
    assert t.alarm_prob(np.array([98.5]))[0] == 0.0
    # tied with a calibration point: rank uniform over the two slots -> (1 + 0.01)/2 at s == 100
    assert np.isclose(t.alarm_prob(np.array([100.0]))[0], 1.01 / 2)


def test_alpha_below_resolution_still_exact():
    """alpha (n + 1) < 1: only the top slot alarms, with probability alpha (n + 1)."""
    s = np.arange(50, dtype=float)
    t = conformal_randomized_threshold(s, 0.005)
    assert t.h == np.inf
    assert np.isclose(t.alarm_prob(np.array([100.0]))[0], 0.005 * 51)


@pytest.mark.parametrize("gen", [_cont, _jev])
def test_rows_match_scalar_on_expanded_multiset(gen):
    rng = np.random.default_rng(3)
    cal, new = gen(rng, 80), gen(rng, 30)
    W = rng.multinomial(80, np.full(80, 1 / 80), size=25).astype(float)
    for alpha in (0.01, 0.05):
        A = row_thresholds(cal, W, alpha, "conformal_randomized").alarm(new)
        A2 = row_thresholds(np.broadcast_to(cal, W.shape), W, alpha, "conformal_randomized").alarm(new)
        ref = np.array([conformal_randomized_threshold(np.repeat(cal, W[b].astype(int)), alpha).alarm_prob(new)
                        for b in range(len(W))])
        assert np.allclose(A, ref) and np.allclose(A2, ref)
        # per-row test statistics + row slicing
        T = np.broadcast_to(new, (len(W), len(new)))
        assert np.allclose(row_thresholds(cal, W, alpha, "conformal_randomized").alarm(T), ref)
        assert np.allclose(row_thresholds(cal, W, alpha, "conformal_randomized")[:1].alarm(new), ref[:1])


def test_rows_plugin_identical_to_boot_threshold():
    rng = np.random.default_rng(4)
    cal, new = _jev(rng, 90), _jev(rng, 40)
    W = rng.multinomial(90, np.full(90, 1 / 90), size=30).astype(float)
    order = np.argsort(cal, kind="stable")
    h, g = _boot_threshold(cal[order], W[:, order], 0.05, "randomized")
    A = (new[None, :] > h[:, None]) + g[:, None] * (new[None, :] == h[:, None])
    assert np.array_equal(row_thresholds(cal, W, 0.05, "randomized_plugin").alarm(new), A)


def test_convention_switch_is_opt_in_and_scoped():
    rng = np.random.default_rng(5)
    cal = rng.random(100)
    assert get_threshold_convention() == "plugin"
    old = randomized_threshold(cal, 0.01)
    assert old.method == "randomized" and calibrate(cal, 0.01, "randomized").method == "randomized"
    with threshold_convention("conformal"):
        assert randomized_threshold(cal, 0.01).method == "conformal_randomized"
        assert calibrate(cal, 0.01, "randomized").method == "conformal_randomized"
        assert calibrate(cal, 0.01, "randomized_plugin").h == old.h
        with pytest.raises(ValueError):          # fixed-(h, gamma) helper refuses to silently use plug-in
            _boot_threshold(np.sort(cal), np.ones((2, 100)), 0.01, "randomized")
    assert get_threshold_convention() == "plugin"
    assert calibrate(cal, 0.01, "randomized").h == old.h


def test_paired_bootstrap_under_conformal_convention():
    """A null contrast between a continuous and a tied copy of the same statistic: under the conformal rule both
    run at alpha, so the plug-in's tie-dependent FPR gap (and the spurious TPR gap it buys) disappears."""
    rng = np.random.default_rng(6)
    nh, na = 400, 200
    H, A = rng.normal(size=nh), rng.normal(1.0, 1.0, na)
    raw = []
    for sp in range(20):
        ci = np.sort(rng.permutation(nh)[:100])
        for d, f in (("cont", lambda x: x), ("tied", lambda x: np.round(x, 1))):
            raw.append(dict(split=sp, detector=d, cal=f(H[ci]), test=np.array([]), attack=f(A), cal_idx=ci,
                            test_idx=np.array([], int), attack_idx=np.arange(na)))
    kw = dict(n_honest=nh, n_attack=na, n_boot=200, seed=0)
    with threshold_convention("conformal"):
        o = paired_gain_bootstrap(raw, 0.01, "cont", "tied", **kw)
    assert abs(o["est"]) < 0.02 and o["lo"] <= 0 <= o["hi"]
