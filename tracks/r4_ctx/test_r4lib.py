"""Tests for the round-4 library: exact spend matching, grouped splits, shared cluster weights.

    unset VIRTUAL_ENV; uv run pytest -q tracks/r4_ctx/test_r4lib.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r4lib as X  # noqa: E402


def _panel(n_h=(400, 300, 200), n_a=(150, 120, 90), seed=0, n_groups=40):
    rng = np.random.default_rng(seed)
    rows = []
    for c, (nh, na) in enumerate(zip(n_h, n_a)):
        for i in range(nh):
            rows.append(dict(traj_id=f"h{c}_{i}", label="honest", ctx=f"c{c}",
                             stat=float(np.round(rng.normal(c * 0.5, 1), 1)), group=f"c{c}|g{i % n_groups}",
                             damage=np.nan, side_task=None, policy=None))
        for i in range(na):
            rows.append(dict(traj_id=f"a{c}_{i}", label="attack", ctx=f"c{c}",
                             stat=float(np.round(rng.normal(3 + c * 0.3, 1), 1)), group=f"c{c}|g{i % n_groups}",
                             damage=float(rng.integers(0, 11)), side_task=f"st{i % 4}", policy=f"p{i % 3}"))
    return pd.DataFrame(rows)


def test_split_disjoint_and_grouped():
    U = X.Universe(_panel())
    sp = X.make_split(U, np.random.default_rng(1))
    for k in U.keys:
        hc, ht = set(sp["hc"][k]), set(sp["ht"][k])
        assert not hc & ht and len(hc) and len(ht)
        assert set(U.group[list(hc)]).isdisjoint(set(U.group[list(ht)]))
        parts = [set(sp[p][k]) for p in ("ad", "aa", "at")]
        assert all(len(p) for p in parts)
        assert not (parts[0] & parts[1]) and not (parts[0] & parts[2]) and not (parts[1] & parts[2])
        g = [set(U.group[list(p)]) for p in parts]
        assert g[0].isdisjoint(g[1]) and g[0].isdisjoint(g[2]) and g[1].isdisjoint(g[2])


def test_transfer_split_side_tasks_disjoint():
    df = _panel()
    U = X.Universe(df)
    sp = X.make_split(U, np.random.default_rng(2), transfer="side_task")
    for k in U.keys:
        s_def = set(df.side_task.iloc[sp["ad"][k]])
        s_eval = set(df.side_task.iloc[np.concatenate([sp["aa"][k], sp["at"][k]])])
        assert s_def.isdisjoint(s_eval)


def test_cluster_weights_shared_within_group():
    U = X.Universe(_panel())
    W = U.boot_weights(5, np.random.default_rng(3))
    for g in np.unique(U.group)[:10]:
        idx = np.flatnonzero(U.group == g)
        assert (W[:, idx] == W[:, idx[:1]]).all()
    for k in U.keys:  # stratified: each context keeps its number of groups drawn
        assert W[:, U.rows[k]].sum(axis=1).min() > 0


def test_match_spend_exact_or_unmatched():
    U = X.Universe(_panel())
    sp = X.make_split(U, np.random.default_rng(4))
    S = X.materialize(U, sp, None)
    F = X.fitters(S, U.w)
    for r in X.RULES:
        th, floor, real = X.match_spend(F[r], S["ht"], U.w, 0.05)
        assert th is not None
        assert abs(real - 0.05) < 1e-9
        assert floor <= 0.05
    # tiny calibration sets: floor above a 0.1% budget -> unmatched, never clamped
    small = _panel(n_h=(8, 8, 8), n_a=(30, 30, 30), n_groups=8)
    U2 = X.Universe(small)
    sp2 = X.make_split(U2, np.random.default_rng(5))
    S2 = X.materialize(U2, sp2, None)
    F2 = X.fitters(S2, U2.w)
    th, floor, real = X.match_spend(F2["cfar"], S2["ht"], U2.w, 0.001)
    if floor > 0.001:
        assert th is None and np.isnan(real)


def test_run_cell_rows():
    U = X.Universe(_panel())
    sp = X.make_split(U, np.random.default_rng(6))
    W = U.boot_weights(2, np.random.default_rng(7))
    rows = X.run_cell(U, sp, W[0], (0.01, 0.05))
    assert len(rows) == len(X.RULES) * 2
    for r in rows:
        if r["matched_ok"]:
            assert abs(r["spend"] - r["B"]) < 1e-9 and abs(r["realized"] - r["B"]) < 1e-9
        else:
            assert np.isnan(r["sel_informed"])
