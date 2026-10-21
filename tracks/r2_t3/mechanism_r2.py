"""Round-2 T3 mechanism analysis (no API calls).

Why do detector-aware rewrites raise detection? Per attacker arm (strong monitor, none mode):
  - mean / median per-trajectory peak score, and the honest per-step 99th percentile q99;
  - fraction of trajectories whose PEAK-scoring step is attack-relevant (vs benign filler);
  - mean score on attack-relevant steps vs on benign (non-attack-relevant) steps;
  - mean number of attack-relevant steps scoring above the honest q99 ("conspicuous" steps);
  - fraction of trajectories with at least one conspicuous attack step.
For the originals, attack-relevant steps = the heuristic onset..execution span.
Bootstrap 95% CIs over base attacks for the paired differences vs the originals.

    uv run python -m tracks.r2_t3.mechanism_r2 --monitor-model openai/gpt-4.1
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

from amd.common.schema import load_trajectories
from tracks.r2_t3.evaluate_r2 import ARMS_ADAPT, RESULTS, load_arm, load_honest, load_originals, HERE


def per_traj(stream, ar, q99):
    s = np.array(stream, float)
    ok = ~np.isnan(s)
    if not ok.any():
        return None
    ar = [i for i in ar if i < len(s) and ok[i]]
    arset = set(ar)
    ben = [i for i in range(len(s)) if ok[i] and i not in arset]
    peak = int(np.nanargmax(s))
    return dict(peak=float(np.nanmax(s)), peak_is_attack=float(peak in arset),
                att_mean=float(np.mean(s[ar])) if ar else math.nan,
                ben_mean=float(np.mean(s[ben])) if ben else math.nan,
                n_consp=float(sum(s[i] > q99 for i in ar)),
                any_consp=float(any(s[i] > q99 for i in ar)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor-model", default="openai/gpt-4.1")
    ap.add_argument("--mode", default="none")
    a = ap.parse_args(argv)
    model, mode = a.monitor_model, a.mode
    honest = load_honest(model, mode)
    hv = np.array([x for s in honest for x in s if not math.isnan(x)])
    q99 = float(np.quantile(hv, 0.99))
    sel = json.loads((HERE.parent / "t3_aware_attacker" / "selection.json").read_text())["traj_ids"]
    data = {}
    for label, src in ARMS_ADAPT:
        d = load_originals(model, mode, sel) if src is None else load_arm(src, model, mode)
        if not d:
            continue
        ar_map = {}
        if src is not None:
            for t in load_trajectories(src):
                ar_map[t.meta["orig_traj_id"]] = t.meta.get("attack_relevant_steps") or []
        rows = {}
        for oid, x in d.items():
            if src is None:
                on, hm = x["onset"], x["harm"]
                if on is None or hm is None:
                    continue
                ar = list(range(int(on), int(hm) + 1))
            else:
                ar = ar_map.get(oid, [])
            r = per_traj(x["stream"], ar, q99)
            if r is not None:
                rows[oid] = r
        data[label] = rows
    common = sorted(set.intersection(*[set(v) for v in data.values()]))
    rng = np.random.default_rng(0)
    keys = ["peak", "peak_is_attack", "att_mean", "ben_mean", "n_consp", "any_consp"]
    out = {"q99_honest_step": q99, "n_paired": len(common), "arms": {}}
    lines = [f"# Mechanism: where the suspicion is (monitor {model}, {mode}; paired n={len(common)}; "
             f"honest step q99={q99:.2f})\n",
             "| arm | peak score | peak on attack step | score on attack steps | score on benign steps | "
             "# attack steps > q99 | any attack step > q99 | Δ peak vs original [95% CI] |",
             "|---|---|---|---|---|---|---|---|"]
    base = np.array([data["nothing"][i]["peak"] for i in common]) if "nothing" in data else None
    for label, rows in data.items():
        M = {k: np.array([rows[i][k] for i in common], float) for k in keys}
        res = {k: float(np.nanmean(v)) for k, v in M.items()}
        dl = ""
        if base is not None and label != "nothing":
            diff = M["peak"] - base
            bs = [np.mean(diff[rng.integers(0, len(diff), len(diff))]) for _ in range(2000)]
            res["d_peak"] = float(diff.mean())
            res["d_peak_ci"] = [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]
            dl = f"{diff.mean():+.2f} [{res['d_peak_ci'][0]:+.2f},{res['d_peak_ci'][1]:+.2f}]"
        out["arms"][label] = res
        lines.append(f"| {label} | {res['peak']:.2f} | {res['peak_is_attack']:.2f} | {res['att_mean']:.2f} | "
                     f"{res['ben_mean']:.2f} | {res['n_consp']:.2f} | {res['any_consp']:.2f} | {dl or '-'} |")
    # figure: peak-score shift vs originals, and share with a conspicuous attack step
    from tracks.r2_t3.evaluate_r2 import PALETTE, _style
    plt = _style()
    labs = [l for l in out["arms"]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.4, 3.6))
    xs = np.arange(len(labs))
    for j, l in enumerate(labs):
        r = out["arms"][l]
        if "d_peak" in r:
            a1.bar(j, r["d_peak"], color=PALETTE.get(l, "#888"),
                   yerr=[[r["d_peak"] - r["d_peak_ci"][0]], [r["d_peak_ci"][1] - r["d_peak"]]], capsize=2,
                   error_kw={"lw": .7})
        a2.bar(j, r["any_consp"], color=PALETTE.get(l, "#888"))
    for ax in (a1, a2):
        ax.set_xticks(xs); ax.set_xticklabels(labs, rotation=35, ha="right", fontsize=7)
    a1.set_ylabel("Δ peak step score vs original"); a1.axhline(0, color="#444", lw=.6)
    a1.set_title("Peak suspicion shift (paired, 95% CI)", fontsize=8)
    a2.set_ylabel(f"frac. with an attack step > honest q99 ({q99:.1f})"); a2.set_ylim(0, 1)
    a2.set_title("Conspicuous attack step present", fontsize=8)
    fig.savefig(RESULTS / f"mechanism_{mode}.pdf")
    plt.close(fig)
    (RESULTS / "mechanism.md").write_text("\n".join(lines) + "\n")
    (RESULTS / "mechanism.json").write_text(json.dumps(out, indent=1))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
