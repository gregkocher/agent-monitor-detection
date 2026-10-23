"""Audit pass 3 (track r4_cs): is the MOLE random-effects interval valid when the 4 corpora share accounts?

    unset VIRTUAL_ENV; uv run python tracks/audit3/cs_mole_joint.py [--boot 2000]

mole_r4_analysis.py pools the 4 single-day corpora with a DerSimonian-Laird interval that treats corpora as
independent ("corpora are independent"). They are not: all 4 corpora contain the SAME 142 accounts (same 30 solo
insiders, 112 of ~116 attack days identical); only the agent model that generated the activity differs.
This script recomputes the committed per-corpus contrasts with the committed pipeline (load / make_set /
run_matched / paired_contrast_bootstrap, same seeds) but keeps the bootstrap replicates, checks that the
account order is identical across corpora (so replicate b re-weights the same accounts in every corpus), and
forms the RE-weighted pooled contrast per replicate (weights fixed at the committed DL values): a joint,
account-clustered pooled interval. Also: realized FPR per rule.
Outputs: results/audit3/cs_mole_joint.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
R4 = HERE.parent / "r4_cs"
for p in (R4, HERE.parent / "r2_t1", HERE.parent / "r3_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from mole_r3_analysis import make_set  # noqa: E402
from mole_r4_analysis import dets, load  # noqa: E402
from r4lib import re_pool  # noqa: E402
from t1lib import run_matched  # noqa: E402

from amd.common.schema import REPO  # noqa: E402
from amd.evaluation.paired import paired_contrast_bootstrap  # noqa: E402

CORPORA = ["gpt53_single_day", "deepseek_v4_flash_single_day", "qwen36_27b_single_day", "kimi_k26_single_day"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--splits", type=int, default=50)
    a = ap.parse_args()
    rows, B, orders = [], {}, {}
    for corpus in CORPORA:
        D = load(corpus)
        for mon in ("luna", "qwen_int"):
            D[mon] = D[mon].fillna(D[mon].median())
            for drop in (False, True):
                ss = make_set(D, corpus, mon, drop_attack=drop)
                orders[(corpus, mon, drop)] = (tuple(ss.honest_ids), tuple(ss.attack_ids))
                _, raw = run_matched(ss, detectors=dets(), alphas=(0.10, 0.05), n_splits=a.splits, n_boot=300,
                                     return_raw=True, seed=0)
                for al in (0.10, 0.05):
                    for d in ("kth3", "top3sum"):
                        r = paired_contrast_bootstrap([(1, raw, d), (-1, raw, "max")], n_honest=ss.n_h,
                                                      n_attack=ss.n_a, alpha=al, n_boot=a.boot, seed=21,
                                                      return_boot=True)
                        B[(corpus, mon, drop, al, d)] = r.pop("boot")
                        rows.append(dict(corpus=corpus, monitor=mon, drop_attack_days=drop, alpha=al, detector=d, **r))
            print(f"  {corpus}:{mon} done", flush=True)
    G = pd.DataFrame(rows)
    same = all(orders[(c, m, dr)] == orders[(CORPORA[0], m, dr)] for c in CORPORA for m in ("luna", "qwen_int")
               for dr in (False, True))
    print("identical account order across corpora:", same, flush=True)
    out = []
    for mon in ("luna", "qwen_int"):
        for drop in (False, True):
            for al in (0.10, 0.05):
                for d in ("kth3", "top3sum"):
                    s = G[(G.monitor == mon) & (G.drop_attack_days == drop) & (G.alpha == al) & (G.detector == d)]
                    s = s.set_index("corpus").loc[CORPORA]
                    re_ = re_pool(s.est.to_numpy(), np.maximum(s.se.to_numpy(), 1e-3))
                    Bm = np.vstack([B[(c, mon, drop, al, d)] for c in CORPORA])
                    pb = re_["w"] @ Bm
                    cor = np.corrcoef(Bm)
                    out.append(dict(monitor=mon, drop_attack_days=drop, alpha=al, detector=d, re_mu=re_["mu"],
                                    dl_independent_lo=re_["lo"], dl_independent_hi=re_["hi"],
                                    joint_account_lo=np.quantile(pb, .025), joint_account_hi=np.quantile(pb, .975),
                                    joint_p_le0=float((pb <= 0).mean()), tau2=re_["tau2"],
                                    mean_between_corpus_boot_corr=float(cor[np.triu_indices(4, 1)].mean()),
                                    per_corpus=" ".join(f"{e:+.3f}" for e in s.est)))
    O = pd.DataFrame(out)
    O.to_csv(REPO / "results" / "audit3" / "cs_mole_joint.csv", index=False)
    print(O.round(3).to_string())


if __name__ == "__main__":
    main()
