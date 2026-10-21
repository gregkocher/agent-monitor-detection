"""Sanity tests for the T2 library (run: uv run pytest -q tracks/t2_per_context/test_t2lib.py)."""
import numpy as np

import t2lib as L


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


def test_budget_matched_rules_spend_exactly_B():
    for disc in (False, True):
        H, A, w = synth(discrete=disc)
        G = L.Grid(H, w)
        for B in (0.005, 0.01, 0.05):
            for th in (L.rule_global(G, B), L.rule_cfar(G, B), L.rule_pooled(G, B, 30.0),
                       L.rule_stackelberg(H, A, w, B), L.rule_maxdet(H, A, w, B),
                       L.rule_os_shift(H, w, B), L.rule_tm_scale(H, w, B)):
                assert abs(spend(th, H, w) - B) < 1e-6, (disc, B, th)


def test_cfar_equalizes_and_pooled_interpolates():
    H, A, w = synth(discrete=True)
    G = L.Grid(H, w)
    B = 0.05
    cf = L.rates(L.rule_cfar(G, B), H)
    assert np.allclose(cf, B)
    gl = L.rates(L.rule_global(G, B), H)
    assert gl.std() > 0.02
    p0 = L.rates(L.rule_pooled(G, B, 0.0), H)
    assert np.allclose(p0, cf, atol=1e-6)
    pinf = L.rates(L.rule_pooled(G, B, np.inf), H)
    assert np.allclose(pinf, gl, atol=1e-6)
    mid = L.rates(L.rule_pooled(G, B, 300.0), H)
    assert cf.std() < mid.std() < gl.std()


def test_stackelberg_minimizes_selection_payoff():
    H, A, w = synth(1)
    B = 0.02
    G = L.Grid(H, w)
    st = L.rates(L.rule_stackelberg(H, A, w, B), A)
    for th in (L.rule_global(G, B), L.rule_cfar(G, B), L.rule_maxdet(H, A, w, B)):
        assert L.rates(th, A).min() <= st.min() + 1e-9
    floor = np.array([L.hulls(H, A)[k][1][0] for k in H])  # TPR at FPR 0 (cannot go lower)
    above = st > floor + 1e-9
    assert np.ptp(st[above]) < 1e-6 and (st[~above] >= st[above].max() - 1e-9).all()
    md = L.rates(L.rule_maxdet(H, A, w, B), A).mean()
    assert md >= st.mean() - 1e-9


def test_damage_weighted_stackelberg_equalizes_damage():
    H, A, w = synth(2)
    D = {"calm": 1.0, "noisy": 3.0, "hot": 2.0}
    th = L.rule_stackelberg(H, A, w, 0.02, damage=D)
    miss = 1 - L.rates(th, A)
    pay = np.array([D[k] for k in H]) * miss
    floor = np.array([L.hulls(H, A)[k][1][0] for k in H])
    free = 1 - L.rates(th, A) < 1 - floor - 1e-9
    assert np.ptp(pay[free]) < 1e-6 and (pay[~free] <= pay[free].max() + 1e-9).all()


def test_varcomp_recovers_components():
    rng = np.random.default_rng(0)
    ctx, units = [], []
    for c in range(80):
        a = rng.normal(0, 1.0)
        for t in range(40):
            b = rng.normal(0, 0.7)
            L_ = rng.integers(5, 30)
            units.append(a + b + rng.normal(0, 0.5, L_))
            ctx.append(c)
    r = L.varcomp_nested(units, ctx)
    assert abs(r["var_ctx"] - 1.0) < 0.4 and abs(r["var_traj"] - 0.49) < 0.1
    assert abs(r["var_unit"] - 0.25) < 0.02
    y = np.array([u.mean() for u in units])
    o = L.varcomp_oneway(y, ctx)
    assert o["icc"] > 0.5


def test_logitnormal_tau():
    rng = np.random.default_rng(0)
    eta = rng.normal(-3, 0.8, 200)
    n = np.full(200, 400)
    x = rng.binomial(n, 1 / (1 + np.exp(-eta)))
    r = L.logitnormal_re(x, n)
    assert abs(r["tau"] - 0.8) < 0.2 and r["p"] < 1e-3
    x0 = rng.binomial(n, 0.05)
    assert L.logitnormal_re(x0, n)["tau"] < 0.3


def test_eb_n0_orders():
    H, A, w = synth(3)
    same = {k: np.random.default_rng(i).normal(0, 1, 400) for i, k in enumerate(H)}
    assert L.eb_n0(L.Grid(same, w)) > L.eb_n0(L.Grid(H, w))


def test_os_shift_breakdown():
    """Poison 10% of one context at a high value: CFAR's threshold jumps, OS-CFAR (p0 = 0.75)
    barely moves."""
    H, A, w = synth(4)
    B = 0.01
    Hp = dict(H)
    Hp["calm"] = np.concatenate([H["calm"], np.full(45, 8.0)])
    G, Gp = L.Grid(H, w), L.Grid(Hp, w)
    assert L.rule_cfar(Gp, B)["calm"].h >= 8.0 > L.rule_cfar(G, B)["calm"].h + 3
    a = L.rule_os_shift(Hp, w, B, tune=False)["calm"].h
    b = L.rule_os_shift(H, w, B, tune=False)["calm"].h
    assert abs(a - b) < 0.5
    Hq = dict(H)
    Hq["calm"] = np.concatenate([H["calm"], np.full(30, 8.0)])  # 7% < trim fraction 10%
    assert abs(L.rule_tm_scale(Hq, w, B, tune=False)["calm"].h -
               L.rule_tm_scale(H, w, B, tune=False)["calm"].h) < 1.0
