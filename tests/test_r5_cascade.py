import numpy as np

from tracks.r5_jev.cascade import FLOOR, Panel, cascade_stats, escalation_rank, prepare, rand_threshold_rows
from amd.evaluation.calibration import randomized_threshold


def _panel(rng, nh=30, na=20):
    lens = rng.integers(1, 12, nh + na)
    g = [rng.random(n).round(2) for n in lens]            # ties on purpose
    L = [np.where(rng.random(n) < 0.1, np.nan, rng.integers(0, 10, n).astype(float)) for n in lens]
    return Panel("t", list(range(nh)), list(range(nh, nh + na)), np.arange(nh), np.arange(na),
                 {"g": g, "L": L}, "L")


def test_cascade_matches_bruteforce():
    rng = np.random.default_rng(1)
    P = _panel(rng)
    prep = prepare(P, "g", seed=3)
    cal = np.arange(P.nh)
    W = np.vstack([np.ones(P.nh), rng.integers(0, 3, (4, P.nh)).astype(float)])
    for e in (0.05, 0.2, 0.5, 1.0):
        r = escalation_rank(prep, cal, W, e)
        # the escalated weighted share of calibration steps never exceeds e
        for b in range(W.shape[0]):
            esc = [(prep.rank[prep.off[i]:prep.off[i] + prep.lens[i]] > r[b]).sum() * W[b, i] for i in cal]
            tot = sum(prep.lens[i] * W[b, i] for i in cal)
            assert sum(esc) / tot <= e + 1e-9
        S = cascade_stats(prep, np.arange(P.n), r)
        for b in range(W.shape[0]):
            for i in range(P.n):
                rk = prep.rank[prep.off[i]:prep.off[i] + prep.lens[i]]
                L = np.asarray(P.streams["L"][i])
                m = (rk > r[b]) & np.isfinite(L)
                want = L[m].max() if m.any() else FLOOR
                assert S[b, i] == want


def test_rand_threshold_rows_matches_unweighted():
    rng = np.random.default_rng(0)
    s = rng.integers(0, 6, 50).astype(float)
    h, g = rand_threshold_rows(s[None, :], np.ones((1, 50)), 0.05)
    t = randomized_threshold(s, 0.05)
    assert h[0] == t.h and abs(g[0] - t.gamma) < 1e-12


def test_evaluate_end_to_end_synthetic():
    from tracks.r5_jev.cascade import evaluate, make_design, summarize, tpr_boot
    rng = np.random.default_rng(2)
    nh, na = 300, 150
    lens = rng.integers(5, 30, nh + na)
    L, g = [], []
    for j, n in enumerate(lens):
        l = rng.normal(0, 1, n)
        if j >= nh:
            k = rng.integers(n)
            l[k] += 4
        L.append(l)
        g.append(l + rng.normal(0, 1, n))
    P = Panel("syn", list(range(nh)), list(range(nh, nh + na)), np.arange(nh) // 3, np.arange(na) // 3,
              {"L": L, "g": g, "rand": [rng.random(n) for n in lens]}, "L")
    d = make_design(P, 4, 50, 0)
    base = tpr_boot([evaluate(P, d, {"kind": "plain", "stream": "L"}, (0.01, 0.05))], 0.05)
    full = tpr_boot([evaluate(P, d, {"kind": "cascade", "first": "g", "e": 1.0}, (0.05,))], 0.05)
    assert np.allclose(base, full)          # escalating everything == LLM-only
    good = tpr_boot([evaluate(P, d, {"kind": "cascade", "first": "g", "e": 0.2}, (0.05,))], 0.05)
    rnd = tpr_boot([evaluate(P, d, {"kind": "cascade", "first": "rand", "e": 0.2}, (0.05,))], 0.05)
    assert good[0] > rnd[0]
    s = summarize(good - base, 0.03)
    assert s["lo"] <= s["est"] <= s["hi"]
