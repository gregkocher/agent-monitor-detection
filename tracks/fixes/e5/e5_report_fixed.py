"""Corrected E5 tables, figures and the r2_t2 corrections CSV (audit issues C1, M5).

Reads the outputs of e5_allocation_fixed.py and e5_auroc_fixed.py plus the original
results/r2_t2/e5_allocation.csv, and writes to results/fixes/r2_t2/:
  e5_tables_corrected.md          corrected E5 tables (spend, share matched, floors in every table)
  e5_spend_floor.csv              per-rule realized test spend at level 0 (floor) over replicates,
                                  plus the analytic approximation sum_c w_c / (n_c^cal + 1)
  e5_equal_spend_1pct.csv         per-context rules at their nominal-1% realized spend vs global
                                  evaluated at the SAME realized spend (plain splits, from the curves)
  e5_claim_counts.csv             'rule >= global' counts by design / B / mode
  fig_e5_tpr_vs_spend.pdf         uniform TPR vs realized test spend per rule (key signals)
  fig_e5_spend_floor.pdf          distribution of the per-replicate spend floor per rule
  corrections_r2_t2.csv           issue_id,track,original_claim,corrected_claim,numbers_before,
                                  numbers_after,verdict

    unset VIRTUAL_ENV; uv run python tracks/fixes/e5/e5_report_fixed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e5fix_lib as F  # noqa: E402

OUT = F.OUT
ROOT = F.ROOT
MIN_SHARE = 0.8   # matched estimates with matched share < 0.8 of plain splits are 'not estimable'
COLORS = dict(global_="#2a78d6", cfar="#eb6834", stack="#1baf7a", maxdet="#eda100", pooled_cv="#e87ba4",
              stack_m0="#4a3aa7")
MARK = dict(global_="o", cfar="s", stack="^", maxdet="D", pooled_cv="v", stack_m0="P")
KEY = ["wb_dec_full", "wb_fibs_fu_full", "llm_gpt-4.1_none", "wb_sab_full"]
FAB = ("**Confound:** 508 of 541 attacks (94%) are T3 refined rewrites whose tool outputs were fabricated by the "
       "refiner LLM; honest outputs and the 33 MonitoringBench originals' outputs are real. A signal can partly "
       "separate honest from refined attacks by keying on fabricated outputs or rewrite artifacts.")


def c(rule):
    return COLORS.get(rule if rule != "global" else "global_")


def m(rule):
    return MARK.get(rule if rule != "global" else "global_")


def f2(x, nd=2):
    return "–" if x is None or not np.isfinite(x) else f"{x:.{nd}f}"


def ci(x, lo, hi, nd=2, sign=False):
    if not np.isfinite(x):
        return "–"
    fmt = f"{{:+.{nd}f}}" if sign else f"{{:.{nd}f}}"
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return fmt.format(x)
    return f"{fmt.format(x)} [{fmt.format(lo)}, {fmt.format(hi)}]"


def pct(x, nd=1):
    return "–" if not np.isfinite(x) else f"{100 * x:.{nd}f}%"


# --------------------------------------------------------------------------------------------


def spend_floor(raw, frames):
    r = raw[(raw["mode"] == "nominal") & (raw.B == 0.01) & (raw.kind == "plain")]
    g = r.groupby(["design", "rule"]).floor
    out = pd.DataFrame(dict(floor_mean=g.mean(), floor_q05=g.quantile(0.05), floor_median=g.median(),
                            floor_q95=g.quantile(0.95), share_floor_le_1pct=g.apply(lambda x: float((x <= 0.01).mean()))))
    da = frames[next(iter(frames))][1]
    h = da[da.label == "honest"].groupby("ctx").size()
    w = h / h.sum()
    ncal = np.round(0.5 * h)
    out["analytic_sum_w_over_ncal_plus1"] = float((w / (ncal + 1)).sum())
    return out.reset_index()


def equal_spend(raw, cur):
    """Per plain split: rule's nominal-1% realized spend s; global evaluated at s by interpolating its
    level sweep (B = 1% and 5% sweeps pooled: the global fit at a level does not depend on B); NaN if s
    is outside the global sweep's realized-spend range."""
    rows = []
    nom = raw[(raw["mode"] == "nominal") & (raw.B == 0.01) & (raw.kind == "plain")]
    gl = cur[cur.rule == "global"]
    glg = {k: v for k, v in gl.groupby(["signal", "design", "rep"])}
    for (sig, des, rep, rule), r in nom.groupby(["signal", "design", "rep", "rule"]):
        if rule == "global":
            continue
        s = float(r.spend.iloc[0])
        g = glg[(sig, des, rep)].sort_values("spend", kind="stable")
        sp = g.spend.values
        ok = sp.min() <= s <= sp.max()
        row = dict(signal=sig, design=des, rep=rep, rule=rule, spend=s, ok=ok)
        for k in ("tpr_uniform", "sel_informed"):
            row[k] = float(r[k].iloc[0])
            row[f"global_{k}"] = float(np.interp(s, sp, g[k].values)) if ok else np.nan
            row[f"d_{k}"] = row[k] - row[f"global_{k}"]
        rows.append(row)
    d = pd.DataFrame(rows)
    agg = d.groupby(["signal", "design", "rule"]).agg(
        spend=("spend", "mean"), share_ok=("ok", "mean"),
        tpr_uniform=("tpr_uniform", "mean"), global_tpr_uniform=("global_tpr_uniform", "mean"),
        d_tpr_uniform=("d_tpr_uniform", "mean"),
        d_tpr_uniform_q025=("d_tpr_uniform", lambda x: x.quantile(0.025)),
        d_tpr_uniform_q975=("d_tpr_uniform", lambda x: x.quantile(0.975)),
        sel_informed=("sel_informed", "mean"), global_sel_informed=("global_sel_informed", "mean"),
        d_sel_informed=("d_sel_informed", "mean"),
        d_sel_informed_q025=("d_sel_informed", lambda x: x.quantile(0.025)),
        d_sel_informed_q975=("d_sel_informed", lambda x: x.quantile(0.975)))
    return agg.reset_index()


def counts(S, O):
    rows = []
    srcs = [("E5 original (clamped matching, iid split)", O)] + \
        [(f"corrected {d}", S[S.design == d]) for d in ("iid", "grouped")]
    for name, df in srcs:
        for B in (0.01, 0.05):
            for mode in ("matched", "nominal"):
                a = df[(df.B == B) & (df["mode"] == mode)]
                for rule, met in (("stack", "sel_informed"), ("cfar", "tpr_uniform"), ("cfar", "sel_informed"),
                                  ("maxdet", "tpr_uniform")):
                    p = a.pivot_table(index="signal", columns="rule", values=met)
                    d = a[a.rule == rule].set_index("signal")
                    est = d.index if "share_matched_plain" not in d or mode == "nominal" else \
                        d.index[d.share_matched_plain >= MIN_SHARE]
                    pe = p.loc[p.index.intersection(est)]
                    rows.append(dict(source=name, B=B, mode=mode, rule=rule, metric=met,
                                     n_estimable=len(pe), n_ge_global=int((pe[rule] >= pe["global"]).sum()),
                                     n_ci_above_0=int((d.loc[pe.index, met + "_dlo"] > 0).sum()),
                                     n_ci_below_0=int((d.loc[pe.index, met + "_dhi"] < 0).sum()),
                                     mean_spend=float(d.spend.mean())))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------


def fig_curves(cur, raw):
    fig, axes = plt.subplots(1, len(KEY), figsize=(4.0 * len(KEY), 3.6), sharey=False)
    g = cur[(cur.design == "grouped")]
    for ax, sig in zip(axes, KEY):
        for rule in ("global", "pooled_cv", "cfar", "stack", "maxdet"):
            x = g[(g.signal == sig) & (g.rule == rule)]
            # pool the 1% and 5% sweeps for rules whose fit does not depend on B; otherwise use B = 5%
            if rule == "pooled_cv":
                x = x[x.B == 0.05]
            x = x.assign(level=x.B * x["mult"]).groupby("level")[["spend", "tpr_uniform"]].mean().reset_index()
            x = x[x.level <= 0.15].sort_values("level")
            ax.plot(np.maximum(x.spend, 1e-4), x.tpr_uniform, color=c(rule), lw=2, marker=m(rule), ms=4,
                    markevery=6, label=rule)
            fl = x.iloc[0]
            ax.plot(max(fl.spend, 1e-4), fl.tpr_uniform, marker=m(rule), ms=9, color=c(rule), mec="white", mew=1.5)
        for B in (0.01, 0.05):
            ax.axvline(B, color="#888", lw=1, ls="--", zorder=0)
        ax.set_xscale("log")
        ax.set_xlim(1.5e-3, 0.2)
        ax.set_ylim(0, 1)
        ax.set_title(sig, fontsize=10)
        ax.set_xlabel("realized test spend (mean over 30 splits)")
        ax.grid(alpha=0.25, lw=0.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("uniform TPR (all 536 attacks)")
    axes[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle("E5, grouped split: uniform TPR vs realized spend. Large marker = level 0 (spend floor); "
                 "dashed = 1% / 5%. Per-context rules cannot reach 1%.", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_e5_tpr_vs_spend.pdf")
    plt.close(fig)


def fig_floor(raw):
    r = raw[(raw["mode"] == "nominal") & (raw.B == 0.01) & (raw.design == "grouped") & (raw.kind == "plain")]
    rules = ["global", "pooled_cv", "cfar", "stack", "maxdet"]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    data = [100 * r[r.rule == x].floor.values for x in rules]
    bp = ax.boxplot(data, orientation="horizontal", widths=0.55, patch_artist=True, showfliers=True,
                    flierprops=dict(ms=2, alpha=0.4), medianprops=dict(color="#0b0b0b", lw=1.5))
    for p, x in zip(bp["boxes"], rules):
        p.set_facecolor(c(x))
        p.set_alpha(0.6)
    ax.set_yticks(range(1, len(rules) + 1), rules)
    ax.axvline(1.0, color="#444", ls="--", lw=1)
    ax.text(1.03, len(rules) + 0.35, "B = 1%", fontsize=8)
    ax.set_xlabel("realized test spend at level 0 (%), 17 signals x 30 plain splits")
    ax.set_title("Spend floor per rule (E5, grouped split)", fontsize=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig_e5_spend_floor.pdf")
    plt.close(fig)


# --------------------------------------------------------------------------------------------


def alloc_table(S, design, signals, B_list=(0.01, 0.05)):
    md = ["| signal | B | rule | nominal spend | nominal uniform TPR | matched in (share of splits) | matched uniform TPR "
          "[95%] | Δ uniform vs global [95%] | matched selection [95%] | Δ selection vs global [95%] |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    s = S[S.design == design]
    for sig in signals:
        for B in B_list:
            for rule in ("global", "cfar", "pooled_cv", "maxdet", "stack", "stack_m0"):
                n = s[(s.signal == sig) & (s.B == B) & (s["mode"] == "nominal") & (s.rule == rule)].iloc[0]
                mt = s[(s.signal == sig) & (s.B == B) & (s["mode"] == "matched") & (s.rule == rule)].iloc[0]
                sh = mt.share_matched_plain
                head = f"| {sig} | {B:g} | {rule} | {pct(n.spend, 2)} | {f2(n.tpr_uniform)} | {sh:.2f} |"
                if sh < MIN_SHARE:
                    md.append(head + f" not estimable (floor {pct(mt.floor, 1)}) | – | – | – |")
                    continue
                md.append(head + f" {ci(mt.tpr_uniform, mt.tpr_uniform_lo, mt.tpr_uniform_hi)} | "
                          f"{ci(mt.tpr_uniform_d, mt.tpr_uniform_dlo, mt.tpr_uniform_dhi, sign=True)} | "
                          f"{ci(mt.sel_informed, mt.sel_informed_lo, mt.sel_informed_hi)} | "
                          f"{ci(mt.sel_informed_d, mt.sel_informed_dlo, mt.sel_informed_dhi, sign=True)} |")
    return md


def main():
    S = pd.read_csv(OUT / "e5_allocation_fixed.csv")
    O = pd.read_csv(ROOT / "results" / "r2_t2" / "e5_allocation.csv")
    raw = pd.read_parquet(OUT / "raw" / "e5_fixed_raw.parquet")
    cur = pd.read_parquet(OUT / "raw" / "e5_fixed_curves.parquet")
    A = pd.read_csv(OUT / "e5_auroc_by_provenance.csv")
    OH = pd.read_csv(OUT / "e5_originals_honest_rules.csv")
    frames, sdf, base, meta, kept, st = F.load_panel()

    FL = spend_floor(raw, frames)
    FL.to_csv(OUT / "e5_spend_floor.csv", index=False, float_format="%.4g")
    EQ = equal_spend(raw, cur)
    EQ.to_csv(OUT / "e5_equal_spend_1pct.csv", index=False, float_format="%.4g")
    CN = counts(S, O)
    CN.to_csv(OUT / "e5_claim_counts.csv", index=False, float_format="%.4g")
    fig_curves(cur, raw)
    fig_floor(raw)

    da = frames[next(iter(frames))][1]
    bm = meta.set_index("traj_id")
    att = da[da.label == "attack"].assign(base=lambda x: x.traj_id.map(bm.base))
    nb = att.groupby("ctx").base.nunique()
    na = att.groupby("ctx").size()
    nh = da[da.label == "honest"].groupby("ctx").size()
    signals = list(A.sort_values("auroc_all", ascending=False).signal)

    md = ["# E5 corrected (audit issues C1, M5)\n",
          "Generated by tracks/fixes/e5/e5_report_fixed.py from e5_allocation_fixed.py / e5_auroc_fixed.py. "
          "Same 17 signals, 7 clusters, rules and 30 plain + 60 bootstrap splits as tracks/r2_t2/e5_new_streams.py.\n",
          "**What changed.** (C1) Spend matching sweeps the level over B × {0, 0.01–3 log-spaced, 1} and "
          "interpolates at realized test spend = B only when B lies inside that split's realized-spend range; "
          "otherwise the split is unmatched (no clamping). Point estimates average matched plain splits; rows "
          f"matched in < {MIN_SHARE:.0%} of plain splits are reported as not estimable, because averaging only the "
          "splits that happen to reach B is a selected sample. (M5) Attacks are deduplicated by content hash, and the "
          "attack split is grouped by base attack (orig_traj_id; originals map to themselves) with a cluster "
          "bootstrap over base attacks. Selection safety uses the calibration attacks as attacker information, "
          "as in E5.\n",
          f"> {FAB}\n",
          "## Data and duplicates\n",
          f"- Attack set: {st['n_in']} attacks (33 originals + 508 refined) from {meta.base.nunique()} base attacks. "
          f"Identical-content groups in the E5 set: {st['n_dup_groups']} (removed {st['n_removed']}). The audit's "
          "'329 of 419 adaptive refined trajectories byte-identical to r0' is correct for the files "
          "(data/processed/t3_refined/<arm>/ re-lists the r0 trajectory under the same traj_id when the adaptive "
          "loop stopped at round 0), but E5 keys signals by traj_id, so those copies were already merged. The "
          "real leak was correlated variants (original, r0 under 3 arms, r1/r2) of one base attack falling on "
          "both sides of the split.",
          "- Allocation clusters (honest / attacks / base attacks): " +
          ", ".join(f"{k} ({nh[k]} / {na[k]} / {nb[k]})" for k in nh.index) + ".",
          "- Originals in the allocation clusters: " +
          ", ".join(f"{k} {v}" for k, v in da[da.traj_id.isin(set(meta.traj_id[meta.is_orig]))]
                    .groupby("ctx").size().items()) +
          ". Too few for attack-fitted allocation (stack, maxdet), so originals-only results are AUROC and "
          "honest-only rules.\n",
          "## Spend floor of per-context rules (C1)\n",
          "Plug-in per-context thresholds at level 0 sit at each cluster's calibration maximum, so test honest runs "
          "above it still alarm. The realized test spend therefore has a floor of about Σ_c w_c / (n_c^cal + 1) "
          f"= {pct(FL.analytic_sum_w_over_ncal_plus1.iloc[0], 2)} with 15–106 calibration honest runs per cluster. "
          "Below the floor, 1% cannot be reached, so **1% spend-matched estimates are not estimable for cfar, stack, "
          "stack_m0 and maxdet**.\n",
          "Per-replicate floor over 17 signals × 30 plain splits:\n", "| design | rule | floor mean | floor 5–95% | share of splits with floor ≤ 1% |", "|---|---|---|---|---|"]
    for _, r in FL.iterrows():
        md.append(f"| {r.design} | {r.rule} | {pct(r.floor_mean, 2)} | {pct(r.floor_q05, 2)}–{pct(r.floor_q95, 2)} | "
                  f"{r.share_floor_le_1pct:.2f} |")
    md += ["", "Nominal-mode realized test spend (mean over plain splits, grouped design): " +
           "; ".join(f"{rule} {pct(S[(S.design == 'grouped') & (S['mode'] == 'nominal') & (S.B == B) & (S.rule == rule)].spend.mean(), 2)} at {B:g}"
                     for B in (0.01, 0.05) for rule in ("global", "cfar", "pooled_cv", "maxdet", "stack")) +
           ". Per-context rules overspend out of sample at both budgets (stack and maxdet ~1.6–1.7× at 5%).\n"]

    # equal-spend comparison at 1%
    md += ["## 1% budget: per-context rules vs global at the same realized spend\n",
           "1% is not reachable for per-context rules, so the closest valid comparison evaluates global at the "
           "spend each per-context rule actually realizes at nominal 1% (about 2.6–4.2%). Global is interpolated "
           "within its own level sweep on the same split. Interval = 2.5–97.5% over the 30 plain splits (split "
           "variability only, not a bootstrap). Grouped design.\n",
           "| signal | rule | realized spend | rule uniform TPR | global uniform TPR @ same spend | Δ [split 95%] | "
           "rule selection | global selection @ same spend | Δ [split 95%] |",
           "|---|---|---|---|---|---|---|---|---|"]
    eq = EQ[EQ.design == "grouped"]
    for sig in signals:
        for rule in ("cfar", "stack", "maxdet"):
            r = eq[(eq.signal == sig) & (eq.rule == rule)].iloc[0]
            md.append(f"| {sig} | {rule} | {pct(r.spend, 2)} | {f2(r.tpr_uniform)} | {f2(r.global_tpr_uniform)} | "
                      f"{ci(r.d_tpr_uniform, r.d_tpr_uniform_q025, r.d_tpr_uniform_q975, sign=True)} | "
                      f"{f2(r.sel_informed)} | {f2(r.global_sel_informed)} | "
                      f"{ci(r.d_sel_informed, r.d_sel_informed_q025, r.d_sel_informed_q975, sign=True)} |")

    md += ["", "## Claim counts\n",
           "Number of signals (of those estimable) where the rule's point estimate is ≥ global, and where the "
           "paired bootstrap interval of the difference excludes 0. Estimable = matched in ≥ 80% of plain splits "
           "(the original E5 CSV has no share column, so all its rows count).\n",
           "| source | B | mode | rule | metric | estimable | ≥ global | CI > 0 | CI < 0 | mean spend |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in CN.iterrows():
        md.append(f"| {r.source} | {r.B:g} | {r['mode']} | {r.rule} | {r.metric} | {r.n_estimable} | {r.n_ge_global} | "
                  f"{r.n_ci_above_0} | {r.n_ci_below_0} | {pct(r.mean_spend, 2)} |")

    md += ["", "## Allocation, grouped split (corrected design)\n", f"> {FAB}\n",
           "Point = mean over plain splits that matched; [95%] = bootstrap percentile (cluster bootstrap over base "
           "attacks); Δ = paired bootstrap difference vs global. 'matched in' = share of plain splits whose "
           "realized-spend range contains B.\n"]
    md += alloc_table(S, "grouped", signals)
    md += ["", "## Allocation, iid split with fixed matching (isolates C1)\n", f"> {FAB}\n"]
    md += alloc_table(S, "iid", signals)

    md += ["", "## AUROC by attack provenance (M5)\n", f"> {FAB}\n",
           "AUROC vs Honest-550 (trajectory max; orientation as in E5). [95%] from 2000 bootstrap draws "
           "resampling honest runs and base attacks. 'refined, same bases' = refined variants of the 33 originals' "
           "base attacks (120 trajectories), which controls the base-attack mix. Originals: n = 33.\n",
           "| signal | all (541) | originals (33) | refined (508) | refined, same bases (120) | Δ same-base refined − originals [95%] |",
           "|---|---|---|---|---|---|"]
    for _, r in A.sort_values("auroc_all", ascending=False).iterrows():
        md.append(f"| {r.signal} | {ci(r.auroc_all, r.auroc_all_lo, r.auroc_all_hi, 3)} | "
                  f"{ci(r.auroc_originals, r.auroc_originals_lo, r.auroc_originals_hi, 3)} | "
                  f"{ci(r.auroc_refined, r.auroc_refined_lo, r.auroc_refined_hi, 3)} | "
                  f"{ci(r.auroc_refined_same_base, r.auroc_refined_same_base_lo, r.auroc_refined_same_base_hi, 3)} | "
                  f"{ci(r.d_samebase_minus_orig, r.d_sb_lo, r.d_sb_hi, 3, sign=True)} |")
    md += ["", "## Originals only: honest-only rules (global vs CFAR)\n",
           "Global and CFAR are fit on honest calibration runs only, so all 32 originals in the 7 clusters are test "
           "data. Uniform TPR = mean over clusters (1–15 originals each: very noisy); pooled = per original. 30 plain "
           "+ 60 bootstrap splits (honest split, originals resampled). No fabrication confound.\n",
           "| signal | B | rule | mode | spend | matched in | uniform TPR [95%] | Δ uniform vs global [95%] | pooled TPR [95%] |",
           "|---|---|---|---|---|---|---|---|---|"]
    for sig in signals:
        for B in (0.01, 0.05):
            for rule in ("global", "cfar"):
                for mode in ("nominal", "matched"):
                    r = OH[(OH.signal == sig) & (OH.B == B) & (OH.rule == rule) & (OH["mode"] == mode)].iloc[0]
                    sh = r.share_matched_plain if mode == "matched" else 1.0
                    if mode == "matched" and sh < MIN_SHARE:
                        md.append(f"| {sig} | {B:g} | {rule} | {mode} | – | {sh:.2f} | not estimable (floor "
                                  f"{pct(r.floor, 1)}) | – | – |")
                        continue
                    md.append(f"| {sig} | {B:g} | {rule} | {mode} | {pct(r.spend, 2)} | {sh:.2f} | "
                              f"{ci(r.tpr_uniform, r.tpr_uniform_lo, r.tpr_uniform_hi)} | "
                              f"{ci(r.tpr_uniform_d, r.tpr_uniform_dlo, r.tpr_uniform_dhi, sign=True)} | "
                              f"{ci(r.tpr_pooled, r.tpr_pooled_lo, r.tpr_pooled_hi)} |")
    md += ["", "Figures: fig_e5_tpr_vs_spend.pdf, fig_e5_spend_floor.pdf.\n"]
    (OUT / "e5_tables_corrected.md").write_text("\n".join(md) + "\n")
    print("wrote", OUT / "e5_tables_corrected.md")


if __name__ == "__main__":
    main()
