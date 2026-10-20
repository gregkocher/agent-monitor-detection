"""Unit tests: detector statistics against brute-force definitions, NaN handling, transforms."""
import numpy as np
import pytest
from scipy import stats as st

from amd.detectors import (CUSUM, KDELogLR, CountAbove, ConformalEProcess, EDetectorSR,
                           KthLargest, LLRCUSUM, LRMax, Max, Mean, MultiChart, PValue,
                           ShiryaevRoberts, TopKSum, UnitCalibrator, WindowGLR, Whiten,
                           default_suite, pack)
from amd.evaluation.synthetic import inject, noise_streams, quantize

RNG = np.random.default_rng(0)
STREAMS = [RNG.normal(size=L) for L in RNG.integers(1, 30, size=60)]


def test_pack_nan_and_alignment():
    s = np.array([0.5, np.nan, 2.0, np.nan, -1.0, 3.0])
    d = Max().fit([np.zeros(5)])
    path = d.stat_path(s)
    assert len(path) == len(s)
    np.testing.assert_allclose(path, [0.5, 0.5, 2.0, 2.0, 2.0, 3.0])
    assert d.stat(s) == 3.0
    assert d.first_alarm([s], 1.0)[0] == 2  # original index, NaNs skipped
    assert d.stat([np.nan, np.nan]) == -np.inf  # empty stream -> empty_value
    lead = d.stat_path([np.nan, 1.0])
    assert lead[0] == -np.inf and lead[1] == 1.0


def test_batch_equals_single():
    for d in default_suite().values():
        d.fit(STREAMS)
        batch = d.stats(STREAMS[:10])
        single = [d.stat(s) for s in STREAMS[:10]]
        if "rand" in d.name:
            continue
        np.testing.assert_allclose(batch, single, err_msg=d.name)
        # alarm-type statistic = max over its path; otherwise final value
        for s, b in zip(STREAMS[:10], batch):
            p = d.stat_path(s)
            np.testing.assert_allclose(b, p.max() if d.alarm_type else p[-1], err_msg=d.name)


def test_order_statistics_bruteforce():
    ident = None
    for s in STREAMS:
        srt = np.sort(s)[::-1]
        assert Max(ident).fit(STREAMS).stat(s) == srt[0]
        assert np.isclose(Mean(ident).fit(STREAMS).stat(s), s.mean())
        for k in (2, 3):
            exp = srt[k - 1] if len(s) >= k else -np.inf
            assert KthLargest(k).fit(STREAMS).stat(s) == exp
        for k in (3, 5):
            # path max of top-k sum with missing slots = 0
            path = [np.sort(s[: t + 1])[::-1][:k].sum() for t in range(len(s))]
            assert np.isclose(TopKSum(k).fit(STREAMS).stat(s), max(path))
    d = CountAbove(0.9).fit(STREAMS)
    u = np.quantile(np.concatenate(STREAMS), 0.9)
    for s in STREAMS:
        assert d.stat(s) == np.sum(s > u)


def _cusum_naive(z, k):
    S, out = 0.0, []
    for x in z:
        S = max(0.0, S + x - k)
        out.append(S)
    return np.array(out)


def test_cusum_sr_glr_bruteforce():
    for s in STREAMS[:20]:
        c = CUSUM(0.3, transform=None).fit(STREAMS)
        np.testing.assert_allclose(c.stat_path(s), _cusum_naive(s, 0.3))
        # SR: R_t = (1 + R_{t-1}) LR_t
        sr = ShiryaevRoberts(delta=0.8, transform=None).fit(STREAMS)
        R, path = 0.0, []
        for x in s:
            R = (1 + R) * np.exp(0.8 * x - 0.32)
            path.append(np.log(R))
        np.testing.assert_allclose(sr.stat_path(s), path, rtol=1e-10)
        # window GLR
        W = 7
        g = WindowGLR(W, transform=None).fit(STREAMS)
        exp = []
        for t in range(len(s)):
            best = 0.0
            for m in range(1, min(W, t + 1) + 1):
                S = s[t - m + 1: t + 1].sum()
                best = max(best, max(S, 0) ** 2 / (2 * m))
            exp.append(best)
        np.testing.assert_allclose(g.stat_path(s), exp)


def test_eprocess_bruteforce():
    cal = UnitCalibrator().fit(np.concatenate(STREAMS))
    e = ConformalEProcess("power", lambdas=[0.1, 0.5]).fit(STREAMS)
    for s in STREAMS[:10]:
        p = cal.pvalues(s, "conservative")
        prods = [np.cumprod(k * p ** (k - 1)) for k in (0.1, 0.5)]
        np.testing.assert_allclose(e.stat_path(s), np.log(np.mean(prods, axis=0)), rtol=1e-10)
    sr = EDetectorSR("linear", lambdas=[0.5]).fit(STREAMS)
    for s in STREAMS[:10]:
        p = cal.pvalues(s, "conservative")
        M, path = 0.0, []
        for pi in p:
            M = (1 + 0.5 * (1 - 2 * pi)) * (1 + M)
            path.append(np.log(M))
        np.testing.assert_allclose(sr.stat_path(s), path, rtol=1e-10)


@pytest.mark.filterwarnings("ignore::scipy.integrate.IntegrationWarning")
def test_calibrators_integrate_to_one():
    from amd.detectors import log_evalues
    from scipy.integrate import quad
    for cal, lam in [("power", 0.1), ("power", 0.5), ("linear", 0.9), ("powerint", None)]:
        val, _ = quad(lambda u: float(np.exp(log_evalues(np.array([u]), cal, lam))[0]), 0, 1,
                      limit=200)
        assert abs(val - 1) < 5e-3, cal  # quad error near the p=0 singularity


def test_conformal_pvalues_validity():
    rng = np.random.default_rng(1)
    cal = UnitCalibrator().fit(rng.normal(size=500))
    s = rng.normal(size=20000)
    pc = cal.pvalues(s, "conservative")
    pr = cal.pvalues(s, "randomized", rng=rng)
    pm = cal.pvalues(s, "mid")
    assert np.all(pc >= pr) and np.all(pm <= pc)
    # marginal validity over the calibration draw: one test unit per fresh calibration set
    for rounding in (False, True):  # continuous, and integer scores with heavy ties
        prs, pcs = [], []
        for _ in range(3000):
            v = rng.normal(size=31)
            v = np.round(v) if rounding else v
            c = UnitCalibrator().fit(v[:30])
            prs.append(c.pvalues(v[30:], "randomized", rng=rng)[0])
            pcs.append(c.pvalues(v[30:], "conservative")[0])
        assert st.kstest(prs, "uniform").pvalue > 1e-3
        for a in (0.1, 0.3):
            assert np.mean(np.array(pcs) <= a) <= a + 0.02


def test_whiten_is_standard_normal():
    rng = np.random.default_rng(2)
    h = [rng.exponential(size=40) for _ in range(300)]  # skewed raw scores
    w = Whiten(kind="randomized", seed=0).fit(pack(h))
    z = w.apply(pack([rng.exponential(size=40) for _ in range(300)]))
    z = z.ravel()
    assert abs(z.mean()) < 0.05 and abs(z.std() - 1) < 0.05
    wl = Whiten(link="logit").fit(pack(h))
    assert np.all(np.isfinite(wl.apply(pack(h))))


def test_mondrian_and_hierarchical_fallback():
    rng = np.random.default_rng(3)
    # two contexts with different honest levels; a tiny third context
    ctxs = ["a"] * 400 + ["b"] * 400 + ["tiny"] * 5
    h = [rng.normal(0 if c == "a" else 2 if c == "b" else 1, 1, 20) for c in ctxs]
    pm = PValue(mondrian=True, min_n=200).fit(pack(h, ctxs))
    pg = PValue().fit(pack(h, ctxs))
    x = np.full((1, 1), 2.5)
    pa = pm.apply(pack(x, ["a"]))[0, 0]
    pb = pm.apply(pack(x, ["b"]))[0, 0]
    assert pa < 0.02 and 0.2 < pb < 0.45
    # unknown / tiny contexts fall back to the global p-value exactly
    pglob = pg.apply(pack(x, ["a"]))[0, 0]
    assert pm.apply(pack(x, ["tiny"]))[0, 0] == pglob
    assert pm.apply(pack(x, ["never_seen"]))[0, 0] == pglob
    # hierarchical: (env, task) with shrinkage toward the env level
    ctx2 = [("a", "t1")] * 300 + [("a", "t2")] * 5 + [("b", "t3")] * 300
    h2 = [rng.normal(0 if c[0] == "a" else 2, 1, 20) for c in ctx2]
    one = np.ones((1, 1))
    env_a = np.sort(np.concatenate([x for x, c in zip(h2, ctx2) if c[0] == "a"]))
    p_env = UnitCalibrator._p(env_a, np.array([1.0]), "conservative", None)[0]
    p2 = PValue(mondrian=True, min_n=300, n0=0).fit(pack(h2, ctx2))
    # t2 has 100 units < min_n -> falls back to its env level, not to the global pool
    assert np.isclose(p2.apply(pack(one, [("a", "t2")]))[0, 0], p_env)
    p_glob = PValue().fit(pack(h2, ctx2)).apply(pack(one))[0, 0]
    assert abs(p_env - p_glob) > 0.1
    # partial pooling: huge n0 -> global, moderate n0 -> in between
    p3 = PValue(mondrian=True, min_n=10, n0=1e7).fit(pack(h2, ctx2))
    assert np.isclose(p3.apply(pack(one, [("a", "t1")]))[0, 0], p_glob, atol=1e-3)
    p4 = PValue(mondrian=True, min_n=10, n0=6000).fit(pack(h2, ctx2))
    v4 = p4.apply(pack(one, [("a", "t1")]))[0, 0]
    assert min(p_env, p_glob) < v4 < max(p_env, p_glob)


def test_mondrian_equalizes_per_context_fpr():
    from amd.evaluation import simple_matched
    rng = np.random.default_rng(4)

    def make(n):
        ctx = rng.choice(["quiet", "noisy"], size=n)
        return [rng.normal(0 if c == "quiet" else 1.5, 1, 15) for c in ctx], list(ctx)

    cal, cc = make(3000)
    test, tc = make(6000)
    tc = np.array(tc)
    out = {}
    for name, d in [("global", Max()), ("mondrian", Max(transform=Whiten(mondrian=True)))]:
        thr, _, _, dd, s = simple_matched(d, cal, test, test[:10], 0.05, cal_contexts=cc,
                                          test_contexts=list(tc), attack_contexts=list(tc[:10]))
        out[name] = {c: thr.rate(s["test"][tc == c]) for c in ("quiet", "noisy")}
    assert out["global"]["noisy"] > 5 * out["global"]["quiet"]
    assert abs(out["mondrian"]["noisy"] - out["mondrian"]["quiet"]) < 0.025


def test_kde_llr_transform():
    rng = np.random.default_rng(5)
    h = [rng.normal(0, 1, 20) for _ in range(200)]
    a, on = inject([rng.normal(0, 1, 20) for _ in range(200)], rng, "shift", 2.0, onset=10)
    t = KDELogLR(clip=2.0, monotone=True).fit(pack(h), pack(a), list(on))
    g = np.linspace(-3, 5, 50)
    v = t.apply(pack(g[None, :]))[0]
    assert np.all(np.diff(v) >= -1e-12) and v.max() <= 2.0 and v.min() >= -2.0
    with pytest.raises(ValueError):
        LRMax().fit(h)  # supervised without attacks
    d = LLRCUSUM(clip=3).fit(h, attack_streams=a, attack_onsets=list(on))
    assert d.supervised and np.isfinite(d.stats(a)).all()


def test_multichart_statistic():
    rng = np.random.default_rng(6)
    h = noise_streams(400, 20, rng)
    mc = MultiChart([Max(), CUSUM(0.5)], weights=[1, 3]).fit(h)
    s = mc.stats(h[:50])
    p = np.array([mc.stat_path(x).max() for x in h[:50]])
    np.testing.assert_allclose(s, p)
    assert set(np.unique(mc.which_component(h[:50]))) <= {0, 1}
    assert np.isclose(mc.weights.sum(), 1) and mc.weights[1] == 0.75


def test_onset_estimates():
    from amd.evaluation import localization_errors
    rng = np.random.default_rng(7)
    a, on = inject(noise_streams(300, 60, rng), rng, "shift", 2.0, onset="uniform", min_post=15)
    for d in [CUSUM(1.0, transform=None), ShiryaevRoberts(2.0, transform=None),
              WindowGLR(60, transform=None)]:
        d.fit([np.zeros(3)])
        le = localization_errors(d, a, on)
        assert le.abs_error.median() <= 1, d.name
    q = quantize(noise_streams(50, 30, rng))  # integer scores still work end to end
    assert np.isfinite(Max().fit(q).stats(q)).all()
