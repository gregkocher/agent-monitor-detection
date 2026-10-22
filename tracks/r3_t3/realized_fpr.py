"""Held-out realized trajectory FPR per deployed detector (nominal vs achieved).

Over S random 50/50 splits of the honest set: calibrate a randomized threshold on one half and
measure the alarm rate on the other. Reports mean and 2.5/97.5 percentiles across splits, for the
with-output (550 honest) and no-output (250 honest) gpt-4.1 none-mode monitors.

    uv run python -m tracks.r3_t3.realized_fpr
"""
from __future__ import annotations

import json

import numpy as np

from amd.evaluation import calibrate
from tracks.r3_t3.compare_rewriters import DEPLOYED, RESULTS, det, load_honest

ALPHAS = (0.05, 0.01, 0.003)


def main(S: int = 200):
    rng = np.random.default_rng(0)
    lines = ["# Realized held-out trajectory FPR", "",
             "Mean over 200 random 50/50 honest splits; brackets are the 2.5/97.5 percentiles.", "",
             "| monitor | n_honest | detector | alpha | realized FPR |", "|---|---|---|---|---|"]
    out = {}
    for tag, noout in (("with-output", False), ("no-output", True)):
        H = load_honest(noout)
        n = len(H)
        for dn in DEPLOYED:
            for al in ALPHAS:
                vals = []
                for _ in range(S):
                    p = rng.permutation(n)
                    cal = [H[i] for i in p[: n // 2]]
                    tst = [H[i] for i in p[n // 2:]]
                    d = det(dn).fit(cal)
                    thr = calibrate(d.stats(cal), al, "randomized")
                    vals.append(float(thr.alarm_prob(d.stats(tst)).mean()))
                v = np.array(vals)
                out[f"{tag}|{dn}|{al}"] = [float(v.mean()), float(np.quantile(v, .025)), float(np.quantile(v, .975))]
                lines.append(f"| {tag} | {n} | {dn} | {al} | {v.mean():.4f} [{np.quantile(v,.025):.4f},{np.quantile(v,.975):.4f}] |")
    (RESULTS / "realized_fpr.md").write_text("\n".join(lines) + "\n")
    (RESULTS / "realized_fpr.json").write_text(json.dumps(out, indent=1))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
