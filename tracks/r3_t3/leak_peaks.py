"""Leak test, calibration-free: does stripping the (fabricated) tool outputs change suspicion?

For identical trajectories, compare the per-trajectory peak score and the mean step score WITH the
current action's output vs WITHOUT it (history-free gpt-4.1). Originals have REAL outputs; rewrites
have FABRICATED ones. If fabricated outputs leaked cues, stripping them would move rewrite peaks
differently from original peaks. Reported: mean peak with/without, paired Δ (without − with) with a
bootstrap CI, and the difference-in-differences (rewrite Δ − original Δ). Paired on the 35 base
attacks shared by all arms.

    uv run python -m tracks.r3_t3.leak_peaks
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from tracks.r3_t3.compare_rewriters import ARMS, RESULTS, load_arm, load_originals


def peak(s):
    v = [x for x in s if not (isinstance(x, float) and math.isnan(x))]
    return max(v) if v else math.nan


def mean_step(s):
    v = [x for x in s if not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(v)) if v else math.nan


def main():
    rng = np.random.default_rng(0)
    w = {"nothing": load_originals(False)}
    n = {"nothing": load_originals(True)}
    for arm in ARMS:
        for rw, suf in (("gpt41", "_r2_r0"), ("gemini", "_r3")):
            w[f"{arm}@{rw}"] = load_arm(f"t3_refined/{arm}{suf}", False)
            n[f"{arm}@{rw}"] = load_arm(f"t3_refined/{arm}{suf}", True)
    common = set(n["nothing"]) & set(w["nothing"])
    for k in n:
        if k != "nothing":
            common &= set(n[k]) & set(w[k])
    common = sorted(common)

    def boot(d):
        bs = d[rng.integers(0, len(d), (4000, len(d)))].mean(1)
        return float(d.mean()), float(np.quantile(bs, .025)), float(np.quantile(bs, .975))

    dorig = np.array([peak(n["nothing"][i]["stream"]) - peak(w["nothing"][i]["stream"]) for i in common])
    md = [f"# Fabricated-output leak test (calibration-free; gpt-4.1 none; paired n={len(common)})\n",
          "Δ = peak(no output) − peak(with output) per trajectory. Originals carry REAL outputs, rewrites "
          "FABRICATED ones. DiD = rewrite Δ − original Δ (≈0 ⇒ fabricated outputs carry no extra cue).\n",
          "| arm | rewriter | peak w/ output | peak no output | Δ peak [95% CI] | DiD vs original [95% CI] | mean-step Δ |",
          "|---|---|---|---|---|---|---|"]
    out = {"n": len(common), "arms": {}}
    for key in ["nothing"] + [f"{a}@{rw}" for a in ARMS for rw in ("gpt41", "gemini")]:
        pw = np.array([peak(w[key][i]["stream"]) for i in common])
        pn = np.array([peak(n[key][i]["stream"]) for i in common])
        d = pn - pw
        m, lo, hi = boot(d)
        ms = np.array([mean_step(n[key][i]["stream"]) - mean_step(w[key][i]["stream"]) for i in common])
        if key == "nothing":
            did = "-"
            dd = None
        else:
            dm, dlo, dhi = boot(d - dorig)
            did = f"{dm:+.2f} [{dlo:+.2f},{dhi:+.2f}]"
            dd = [dm, dlo, dhi]
        arm, rw = (key.split("@") + ["-"])[:2]
        out["arms"][key] = dict(peak_with=float(pw.mean()), peak_noout=float(pn.mean()), d_peak=[m, lo, hi],
                                did=dd, d_mean_step=float(np.nanmean(ms)))
        md.append(f"| {arm} | {rw} | {pw.mean():.2f} | {pn.mean():.2f} | {m:+.2f} [{lo:+.2f},{hi:+.2f}] | "
                  f"{did} | {np.nanmean(ms):+.2f} |")
    (RESULTS / "leak_peaks.md").write_text("\n".join(md) + "\n")
    (RESULTS / "leak_peaks.json").write_text(json.dumps(out, indent=1))
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
