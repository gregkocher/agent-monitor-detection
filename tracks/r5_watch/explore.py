"""Exploratory (not preregistered): Watcher-style severity distributions on the evaluation panels.

Per panel: share of honest steps, post-onset attack steps and all attack steps at each severity 1-10; trajectory-max
severity histogram by label; the honest-step severity level that an e = 5/10/20/30% escalation budget cuts into (how
much of the e-matched Watcher arm is random tie-breaking).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_watch.explore
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .analyze import OUT, load_la, load_mb
from . import analyze as A


def main():
    A.W_CFG = json.load(open(OUT / "dev_choice.json"))["config"]
    rows, cut = [], []
    for name, P in (("mb", load_mb()), ("la_nano", load_la())):
        H = np.concatenate([np.asarray(a, float) for a in P.streams["watch"][:P.nh]])
        Aall = np.concatenate([np.asarray(a, float) for a in P.streams["watch"][P.nh:]])
        post = np.concatenate([np.asarray(a, float)[(o or 0):] for a, o in zip(P.streams["watch"][P.nh:], P.attack_onset)])
        hmax = np.array([np.nanmax(a) for a in P.streams["watch"][:P.nh]])
        amax = np.array([np.nanmax(a) for a in P.streams["watch"][P.nh:]])
        for s in range(1, 11):
            rows.append(dict(panel=name, severity=s, honest_steps=float(np.mean(H == s)), attack_steps=float(np.mean(Aall == s)),
                             attack_post_onset_steps=float(np.mean(post == s)), honest_traj_max=float(np.mean(hmax == s)),
                             attack_traj_max=float(np.mean(amax == s))))
        for e in (0.05, 0.10, 0.20, 0.30):
            q = np.sort(H[np.isfinite(H)])[::-1]
            lvl = q[int(e * len(q))]
            above = float(np.mean(H > lvl))
            at = float(np.mean(H == lvl))
            cut.append(dict(panel=name, e=e, cut_level=lvl, share_above=above, share_at_level=at,
                            random_within_level=(e - above) / at if at else np.nan))
    pd.DataFrame(rows).to_csv(OUT / "explore_severity_hist.csv", index=False)
    pd.DataFrame(cut).to_csv(OUT / "explore_tie_cut.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print(pd.DataFrame(cut).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
