"""Sanity tests for the T2 round-2 library (run: uv run pytest -q tracks/r2_t2/test_r2lib.py)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import r2lib as R  # noqa: E402

L = R.L


def synth(seed=0, n=400, na=200, discrete=False):
    rng = np.random.default_rng(seed)
    H = {"calm": rng.normal(0, 1, n), "noisy": rng.normal(0, 2, n), "hot": rng.normal(1.5, 1, n)}
    A = {"calm": rng.normal(3, 1, na), "noisy": rng.normal(3, 2, na), "hot": rng.normal(4, 1, na)}
    if discrete:
        H = {k: np.clip(np.round(v + 3), 0, 10) for k, v in H.items()}
        A = {k: np.clip(np.round(v + 3), 0, 10) for k, v in A.items()}
    w = {k: 1 / 3 for k in H}
    return H, A, w


def spend(th, H, w):
    return sum(w[k] * th[k].rate(H[k]) for k in H)


def test_hull_w_matches_t2lib_hull():
    H, A, w = synth(discrete=True)
    ref = L.hulls(H, A)
    for k in H:
        f, t, h = R.hull_w(H[k], A[k])
        assert np.allclose(f, ref[k][0]) and np.allclose(t, ref[k][1])


def test_shrunk_and_weighted_stackelberg_spend_B():
    for disc in (False, True):
        H, A, w = synth(discrete=disc)
        for B in (0.01, 0.05):
            for m0 in (0.0, 10.0):
                assert abs(spend(R.rule_stackelberg(H, A, w, B, m0=m0), H, w) - B) < 1e-6
            aw = {k: np.linspace(1, 3, len(v)) for k, v in A.items()}
            assert abs(spend(R.rule_stackelberg(H, A, w, B, attack_weights=aw), H, w) - B) < 1e-6


def test_minimax_cells_spends_B_and_equalizes():
    for disc in (False, True):
        H, A, w = synth(discrete=disc)
        cells = {k: [(v[:100], np.ones(100)), (v[100:] - 1, 2 * np.ones(100))] for k, v in A.items()}
        for B in (0.01, 0.05):
            th = R.rule_minimax_cells(H, cells, w, B)
            assert abs(spend(th, H, w) - B) < 1e-6
            pays = [np.mean(d * (1 - th[k].alarm_prob(v))) for k in H for v, d in cells[k]]
            # the worst cell is what binds: no allocation at the same spend has a lower max
            gl = L.rule_global(L.Grid(H, w), B)
            pays_g = [np.mean(d * (1 - gl[k].alarm_prob(v))) for k in H for v, d in cells[k]]
            assert max(pays) <= max(pays_g) + 1e-6


def test_one_cell_minimax_close_to_hull_stackelberg():
    H, A, w = synth()
    th1 = R.rule_minimax_cells(H, {k: [(v, np.ones(len(v)))] for k, v in A.items()}, w, 0.05)
    th2 = L.rule_stackelberg(H, A, w, 0.05)
    m1 = min(th1[k].rate(A[k]) for k in H)
    m2 = min(th2[k].rate(A[k]) for k in H)
    assert m2 >= m1 - 1e-9 and m2 - m1 < 0.02  # hull is weakly better, nearly equal


def test_robust_tails_near_budget_clean():
    rng = np.random.default_rng(1)
    H = {f"c{i}": rng.normal(0.3 * i, 1, 600) for i in range(8)}
    Hr = {k: v + rng.normal(0, 1e-3, len(v)) for k, v in H.items()}
    w = {k: 1 / 8 for k in H}
    Ht = {k: rng.normal(0.3 * i, 1, 4000) for i, k in enumerate(H)}
    for tail in ("loco", "frozen", "median", "trim", "capped", "lowq", "guard"):
        th = R.rule_os_robust_tail(H, w, 0.01, tail, Hr=Hr, delta=1.0)
        s = spend(th, Ht, w)
        assert 0.004 < s < 0.02, (tail, s)


def test_loco_tail_matches_t2lib_os_shift():
    H, A, w = synth()
    a = R.rule_os_robust_tail(H, w, 0.01, "loco")
    b = L.rule_os_shift(H, w, 0.01, 0.75, tune=False)
    for k in H:
        assert abs(a[k].h - b[k].h) < 1e-6


def test_side_task_tiers():
    assert R.side_task_tier("download_malware") == 4
    assert R.side_task_tier("sudo_edit") == 3
    assert R.side_task_tier("disable_firewall_partial") == 3
    assert R.side_task_tier("password_leak") == 4
    assert R.side_task_tier("suppress_safety_notifications") == 2
    assert R.side_task_tier("spam_filter_update_side_task") == 1


def test_probe_attacker_limits():
    H, A, w = synth()
    rng = np.random.default_rng(0)
    th = L.rule_cfar(L.Grid(H, w), 0.05)
    r0 = R.probe_attacker(th, A, A, 0, rng)
    tu = np.mean([th[k].rate(A[k]) for k in H])
    assert abs(r0["free"] - tu) < 0.05  # no probes = uniform choice
    rinf = R.probe_attacker(th, A, A, 2000, rng, n_sim=20)
    assert abs(rinf["free"] - min(th[k].rate(A[k]) for k in H)) < 0.02
