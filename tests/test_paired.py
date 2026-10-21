"""Tests for amd.evaluation.paired: joint (shared-across-splits) paired bootstrap with calibration noise."""
import numpy as np
from scipy.stats import norm

from amd.evaluation import matched_budget_eval, paired_did_bootstrap, paired_gain_bootstrap
from amd.detectors import Max, Mean


def _raw(rng, n_h=400, n_a=200, n_splits=5, rho=0.5, mu=(1.2, 1.0), dup=False):
    """Scalar statistics for two detectors 'a', 'b' (bivariate normal); raw in matched_budget_eval format."""
    cov = [[1, rho], [rho, 1]]
    H = rng.multivariate_normal([0, 0], cov, size=n_h)
    A = rng.multivariate_normal(list(mu), cov, size=n_a)
    raw = []
    first = None
    for sp in range(n_splits):
        cal_idx = np.sort(rng.permutation(n_h)[: n_h // 2]) if (first is None or not dup) else first
        first = cal_idx
        for j, d in enumerate("ab"):
            raw.append(dict(split=sp, detector=d, cal=H[cal_idx, j], test=np.array([]), attack=A[:, j],
                            cal_idx=cal_idx, test_idx=np.array([], int), attack_idx=np.arange(n_a)))
    return raw


def test_identical_detectors_give_zero():
    rng = np.random.default_rng(0)
    raw = _raw(rng)
    raw = [dict(r, detector="a") if r["detector"] == "b" else r for r in raw if r["detector"] == "a"]
    raw += [dict(r, detector="b") for r in raw]
    out = paired_gain_bootstrap(raw, 0.05, "a", "b", n_honest=400, n_attack=200, n_boot=200)
    assert out["est"] == 0 and out["lo"] == 0 and out["hi"] == 0


def test_duplicated_splits_do_not_shrink_the_interval():
    """The old helpers averaged independent replicates over splits, so S copies of one split gave a CI
    sqrt(S) narrower. With one joint resample per replicate, S identical splits give the same interval."""
    raw1 = _raw(np.random.default_rng(1), n_splits=1)
    raw10 = []
    for sp in range(10):
        raw10 += [dict(r, split=sp) for r in raw1]
    kw = dict(n_honest=400, n_attack=200, n_boot=400, seed=3)
    o1 = paired_gain_bootstrap(raw1, 0.05, "a", "b", **kw)
    o10 = paired_gain_bootstrap(raw10, 0.05, "a", "b", **kw)
    assert np.isclose(o1["lo"], o10["lo"]) and np.isclose(o1["hi"], o10["hi"])


def test_calibration_noise_widens_and_coverage_is_near_nominal():
    alpha, mu = 0.05, (1.2, 1.0)
    z = norm.ppf(1 - alpha)
    truth = norm.sf(z - mu[0]) - norm.sf(z - mu[1])
    cover, cover_att, w_full, w_att = [], [], [], []
    for rep in range(60):
        raw = _raw(np.random.default_rng(100 + rep), mu=mu)
        kw = dict(n_honest=400, n_attack=200, n_boot=300, seed=rep)
        f = paired_gain_bootstrap(raw, alpha, "a", "b", **kw)
        o = paired_gain_bootstrap(raw, alpha, "a", "b", calibration_noise=False, **kw)
        cover.append(f["lo"] <= truth <= f["hi"]); cover_att.append(o["lo"] <= truth <= o["hi"])
        w_full.append(f["hi"] - f["lo"]); w_att.append(o["hi"] - o["lo"])
    assert np.mean(w_full) > np.mean(w_att)
    assert np.mean(cover) >= 0.85


def test_did_and_subgroup_on_matched_eval_output():
    rng = np.random.default_rng(5)
    h = [rng.normal(size=rng.integers(5, 20)) for _ in range(300)]
    a = [np.r_[rng.normal(size=8), rng.normal(2.5, 1, size=2)] for _ in range(120)]
    dets = {"max": Max(), "mean": Mean()}
    _, raw1 = matched_budget_eval(dets, h, a, alphas=[0.05], n_splits=3, n_boot=10, method="randomized",
                                  return_raw=True, seed=0)
    _, raw2 = matched_budget_eval(dets, h, a, alphas=[0.05], n_splits=3, n_boot=10, method="randomized",
                                  return_raw=True, seed=0)
    out = paired_did_bootstrap(raw1, raw2, 0.05, "mean", n_honest=300, n_attack=120, n_boot=100)
    assert abs(out["est"]) < 1e-12 and out["n_splits"] == 3
    mask = np.zeros(120, bool); mask[:60] = True
    g = paired_gain_bootstrap(raw1, 0.05, "mean", n_honest=300, n_attack=120, n_boot=100, attack_mask=mask,
                              honest_groups=np.arange(300) % 30, attack_groups=np.arange(120) % 40)
    assert g["lo"] <= g["est"] <= g["hi"]
