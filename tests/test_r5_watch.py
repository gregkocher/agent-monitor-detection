"""r5watch: the fixed-cutoff escalation (escalate iff severity >= k, missing escalated) equals the brute-force rule."""
import numpy as np

from tracks.r5_jev import cascade as C
from tracks.r5_watch.analyze import fixed_rank, fixed_rank_threshold
from tracks.r5_watch.watchlib import parse


def _panel(rng, nh=40, na=30):
    lens = rng.integers(1, 12, nh + na)
    sev = [rng.integers(1, 11, n).astype(float) for n in lens]
    for a in sev[::7]:
        a[0] = np.nan
    L = [rng.random(n) + (j >= nh) * rng.random(n) for j, n in enumerate(lens)]
    P = C.Panel("t", list(range(nh)), list(range(nh, nh + na)), np.arange(nh) % 9, np.arange(na) % 7,
                {"watch": sev, "llm": L}, "llm", attack_onset=[0] * na)
    return P


def test_fixed_cutoff_matches_bruteforce():
    rng = np.random.default_rng(3)
    P = _panel(rng)
    D = C.make_design(P, 3, 5, 0)
    for k in (6, 8):
        prep = C.prepare(P, "watch", seed=5)
        r = fixed_rank_threshold(P, "watch", k)
        with fixed_rank(r):
            res = C.evaluate(P, D, {"kind": "cascade", "first": "watch", "e": -1.0, "_prep": prep}, (0.05,))
        stats = C.cascade_stats(prep, np.arange(P.n), np.array([r]))[0]
        brute = []
        for g, L in zip(P.streams["watch"], P.streams["llm"]):
            esc = ~np.isfinite(g) | (g >= k)
            brute.append(L[esc].max() if esc.any() else C.FLOOR)
        assert np.allclose(stats, brute)
        assert res[0.05]["num"].shape[1] == 6


def test_parse():
    assert parse("SCORE: 7", None)["int"] == 7
    assert parse("SCORE: 0", None)["int"] is None
    assert parse("blah\nSCORE: 10", None)["int"] == 10
    assert parse("no score", None)["int"] is None
