"""r3_t1 mechanism claim: 'across 64 corpus x monitor cells the gain tracks repeat-spike informativeness:
Spearman +0.30 (p = 0.017) for top-3 sum'. The 64 cells are not independent (8 corpora x up to 10 monitor
variants, incl. account-centered copies of the same scores), and rep_lr is computed from the same insider streams
that define the gain (audit M7). Re-test with (i) a corpus-cluster permutation (shuffle rep_lr across corpora
within each monitor variant) and (ii) a corpus-cluster bootstrap CI for Spearman.

    unset VIRTUAL_ENV; uv run python -m tracks.audit2.mole_mechanism_check
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

DET = {"top3sum": "top-3 sum", "kth3": "3rd-max"}


def main(B=5000, seed=0):
    F = pd.read_csv("results/r3_t1/mole_features.csv")
    G = pd.read_csv("results/r3_t1/mole_gains.csv")
    G = G[(G.alpha == 0.1) & (G["set"] == "mole:" + G.corpus + ":" + G.monitor)]
    rng = np.random.default_rng(seed)
    rows = []
    for det in DET:
        x = F.merge(G[G.detector == det][["corpus", "monitor", "gain_vs_max"]], on=["corpus", "monitor"])
        rho = spearmanr(x.rep_lr, x.gain_vs_max).statistic
        # naive p (as reported)
        p_naive = spearmanr(x.rep_lr, x.gain_vs_max).pvalue
        # permutation within monitor across corpora (keeps the monitor-variant structure)
        perm = []
        for _ in range(B):
            y = x.copy()
            y["rep_lr"] = y.groupby("monitor").rep_lr.transform(lambda s: rng.permutation(s.values))
            perm.append(spearmanr(y.rep_lr, y.gain_vs_max).statistic)
        p_perm = float((np.abs(perm) >= abs(rho)).mean())
        # corpus-cluster bootstrap
        cs = x.corpus.unique()
        bs = []
        for _ in range(2000):
            pick = rng.choice(cs, len(cs))
            y = pd.concat([x[x.corpus == c] for c in pick])
            bs.append(spearmanr(y.rep_lr, y.gain_vs_max).statistic)
        # primary (non-derived) monitors only: drop centered copies and the activity baseline
        prim = x[~x.monitor.str.endswith("_c") & (x.monitor != "activity_only")]
        r2 = spearmanr(prim.rep_lr, prim.gain_vs_max)
        rows.append(dict(detector=det, n_cells=len(x), rho=rho, p_naive=p_naive, p_within_monitor_perm=p_perm,
                         rho_corpus_boot_lo=np.nanquantile(bs, .025), rho_corpus_boot_hi=np.nanquantile(bs, .975),
                         n_primary=len(prim), rho_primary=r2.statistic, p_primary_naive=r2.pvalue))
        print(rows[-1])
    pd.DataFrame(rows).to_csv("results/audit2/mole_mechanism_check.csv", index=False)


if __name__ == "__main__":
    main()
