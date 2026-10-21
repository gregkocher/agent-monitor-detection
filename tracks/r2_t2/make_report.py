"""Tables (results/r2_t2/tables.md) and vector-PDF figures (results/r2_t2/figures/) for T2 round 2.

    unset VIRTUAL_ENV; uv run python tracks/r2_t2/make_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import r2lib as R  # noqa: E402

sys.path.insert(0, str(R.ROOT / "tracks" / "t2_per_context"))
import plotstyle as S  # noqa: E402

plt = S.plt
OUT = R.OUT
FIG = OUT / "figures"
MD: list[str] = []

COL = {"global": S.SERIES[0], "cfar": S.SERIES[1], "pooled_cv": S.SERIES[4], "os_shift": S.SERIES[2],
       "maxdet": S.SERIES[5], "stack": S.SERIES[6], "stack_l50": S.SERIES[3], "stack_in": S.SERIES[7],
       "xfer": S.SERIES[3], "self": S.SERIES[2], "os_frozen": S.SERIES[6], "os_guard": S.SERIES[7],
       "os_loco": S.SERIES[2], "os_lowq": S.SERIES[3], "os_median": S.SERIES[4], "frozen": S.SERIES[5],
       "mm_cell_dmg_s": S.SERIES[7], "mm_cell_eq": S.SERIES[3], "stack_dctx": S.SERIES[5]}
MARK = ["o", "s", "D", "^", "v", "P", "X", "*"]
PANEL_LABEL = {
    "akshn_setting": "7 settings", "ca_setting_model": "ControlArena setting×agent",
    "la_env_local": "LinuxArena env (local)", "la_env_cum": "LinuxArena env (cumulative)",
    "la_taskcat_local": "LinuxArena task type", "mb_gpt-4.1-mini_trajectory": "BashArena clusters (mini, traj.)",
    "mb_gpt-4.1-nano_trajectory": "BashArena clusters (nano, traj.)",
    "mb_gpt-4.1-mini_full": "BashArena clusters (mini, per-step)"}


def load(name):
    p = OUT / name
    return pd.read_csv(p) if p.exists() else None


def ci(row, m, nd=2):
    lo, hi = row.get(m + "_lo", np.nan), row.get(m + "_hi", np.nan)
    return R.fmt_ci(row[m], lo, hi, nd)


def dci(row, m, nd=2, suf=""):
    d, lo, hi = row.get(m + "_d" + suf, np.nan), row.get(m + "_dlo" + suf, np.nan), row.get(m + "_dhi" + suf, np.nan)
    if not np.isfinite(d):
        return "–"
    return f"{d:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"


def table(df, cols, header):
    MD.append("| " + " | ".join(header) + " |")
    MD.append("|" + "---|" * len(header))
    for _, r in df.iterrows():
        MD.append("| " + " | ".join(str(c(r)) if callable(c) else str(r[c]) for c in cols) + " |")
    MD.append("")


# --------------------------------------------------------------------------------------------
def e1a():
    s = load("e1a_attack_shift_full.csv")
    if s is None:
        return
    MD.append("## E1a: attack-distribution shift (Stackelberg / max-detection fit on source attacks)\n")
    MD.append("Spend-matched mode. `sel` = TPR in the context the informed target-distribution attacker "
              "picks; Δ vs global and vs the in-distribution Stackelberg (`stack_in`) are paired bootstrap "
              "differences (150 replicates). `stack_l50` = Stackelberg with each context's source attack "
              "distribution mixed 50/50 with the pooled source attacks of the other contexts.\n")
    rules = ["global", "cfar", "maxdet_src", "stack_src", "stack_l25", "stack_l50", "stack_l75", "stack_in", "stack_in_l50"]
    x = s[(s["mode"] == "matched") & s.rule.isin(rules)].copy()
    x["order"] = x.rule.map({r: i for i, r in enumerate(rules)})
    x = x.sort_values(["panel", "split", "B", "order"])
    table(x, ["panel", "split", "B", "rule", lambda r: ci(r, "sel_informed"), lambda r: dci(r, "sel_informed"),
              lambda r: dci(r, "sel_informed", suf="_vs_in"), lambda r: f"{r['tpr_uniform']:.2f}",
              lambda r: f"{r['matched_ok']:.2f}"],
          ["panel", "split", "B", "rule", "sel [95%]", "Δ vs global", "Δ vs stack_in", "uniform TPR", "matched_ok"])
    # figure: strong panels, B = 1% and 5%
    combos = [("ca_setting_model", "policy_p1_p2"), ("ca_setting_model", "policy_p2_p1"),
              ("ca_setting_model", "st_holdout"), ("akshn_setting", "st_holdout"),
              ("la_env_local", "failure_del_live"), ("la_env_local", "st_holdout"),
              ("mb_gpt-4.1-mini_trajectory", "month_early_late"), ("mb_gpt-4.1-mini_trajectory", "st_holdout")]
    show = [("global", "Global"), ("cfar", "CFAR"), ("stack_src", "Stackelberg, source attacks"),
            ("stack_l50", "Stackelberg, source, 50% pooled"), ("stack_in", "Stackelberg, target attacks (in-dist.)")]
    cmap = {"global": COL["global"], "cfar": COL["cfar"], "stack_src": COL["stack"], "stack_l50": COL["stack_l50"],
            "stack_in": COL["stack_in"]}
    split_lab = {"policy_p1_p2": "policy 1→2", "policy_p2_p1": "policy 2→1", "st_holdout": "unseen side tasks",
                 "failure_del_live": "delayed→live", "month_early_late": "≤Feb→Mar 2026"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.9), sharey=True)
    for ax, B in zip(axes, (0.01, 0.05)):
        for yi, (p, sp) in enumerate(combos):
            for j, (r, lab) in enumerate(show):
                q = x[(x.panel == p) & (x.split == sp) & (x.B == B) & (x.rule == r)]
                if not len(q):
                    continue
                q = q.iloc[0]
                y = yi + (j - 2) * 0.14
                ax.plot([q.sel_informed_lo, q.sel_informed_hi], [y, y], color=cmap[r], lw=1.0, alpha=0.6)
                ax.plot(q.sel_informed, y, MARK[j], color=cmap[r], ms=4.5, mec="white", mew=0.6,
                        label=lab if yi == 0 else None)
        ax.set_yticks(range(len(combos)))
        ax.set_yticklabels([f"{PANEL_LABEL[p]}\n{split_lab[sp]}" for p, sp in combos], fontsize=6.8)
        ax.invert_yaxis()
        ax.set_xlim(-0.02, 1.02)
        ax.set_title(f"audit budget B = {B:.0%}")
    fig.supxlabel("safety vs informed attacker (TPR in the context it picks)", fontsize=8.5, y=0.02)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.0, -0.2), ncol=3, fontsize=6.8)
    fig.suptitle("Stackelberg thresholds fit on one attack distribution, attacked by another", fontsize=9)
    S.save(fig, FIG / "e1a_attack_shift.pdf")


def e1b():
    s = load("e1b_deployment_shift_full.csv")
    if s is None:
        return
    MD.append("## E1b: deployment shift (rules fit on other agent models, applied to a new one)\n")
    MD.append("Nominal mode: realized spend on the new agent's held-out honest runs (the outcome of "
              "transfer); safety in spend-matched mode. `src_*` = fit on the other agent models; `in_*` = "
              "fit on the target's calibration half; `xfer_offset` = per-context normal-score offsets "
              "from the source, one level recalibrated on the target's pooled calibration data.\n")
    rules = ["in_global", "in_cfar", "in_stack", "src_global", "src_cfar", "src_pooled_cv", "src_stack", "xfer_offset"]
    nom = s[(s["mode"] == "nominal") & s.rule.isin(rules)].set_index(["panel", "target", "B", "rule"])
    mat = s[(s["mode"] == "matched") & s.rule.isin(rules)].set_index(["panel", "target", "B", "rule"])
    rows = []
    for k in nom.index:
        rows.append(dict(panel=k[0], target=k[1], B=k[2], rule=k[3], spend=ci(nom.loc[k], "spend", 3),
                         fpr_sd=f"{nom.loc[k, 'fpr_sd']:.3f}", sel_matched=ci(mat.loc[k], "sel_informed"),
                         d_vs_in_global=dci(mat.loc[k], "sel_informed")))
    t = pd.DataFrame(rows)
    t["o"] = t.rule.map({r: i for i, r in enumerate(rules)})
    t = t.sort_values(["panel", "target", "B", "o"])
    table(t, ["panel", "target", "B", "rule", "spend", "fpr_sd", "sel_matched", "d_vs_in_global"],
          ["panel", "target agent", "B", "rule", "realized spend [95%]", "per-ctx FPR SD", "sel (matched)",
           "Δ sel vs in_global"])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    show = [("src_global", "Global (source)"), ("src_cfar", "CFAR (source)"), ("src_stack", "Stackelberg (source)"),
            ("xfer_offset", "Source offsets + target level"), ("in_cfar", "CFAR (in-domain)")]
    cm = [COL["global"], COL["cfar"], COL["stack"], COL["xfer"], COL["os_shift"]]
    combos = sorted({(p, t_) for p, t_, *_ in nom.index})
    for ax, B in zip(axes, (0.01, 0.05)):
        for yi, (p, tg) in enumerate(combos):
            for j, (r, lab) in enumerate(show):
                if (p, tg, B, r) not in nom.index:
                    continue
                q = nom.loc[(p, tg, B, r)]
                y = yi + (j - 2) * 0.14
                ax.plot([max(q.spend_lo / B, 0.05), min(q.spend_hi / B, 8)], [y, y], color=cm[j], lw=1.0, alpha=0.6)
                ax.plot(q.spend / B, y, MARK[j], color=cm[j], ms=4.5, mec="white", mew=0.6,
                        label=lab if yi == 0 else None)
        ax.axvline(1, color=S.INK2, lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_xlim(0.05, 8)
        ax.set_xticks([0.1, 0.25, 0.5, 1, 2, 4])
        ax.set_xticklabels(["0.1", "0.25", "0.5", "1", "2", "4"])
        ax.set_yticks(range(len(combos)))
        ax.set_yticklabels([f"{PANEL_LABEL[p]}\nnew agent: {t_}" for p, t_ in combos], fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlabel("realized audit spend / budget (log)")
        ax.set_title(f"B = {B:.0%}")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.0, -0.2), ncol=3, fontsize=6.8)
    S.save(fig, FIG / "e1b_deployment_shift_spend.pdf")


def e1c():
    s = load("e1c_monitor_transfer_full.csv")
    if s is None:
        return
    MD.append("## E1c: cross-monitor offset transfer\n")
    MD.append("Per target monitor: per-context offsets estimated from the OTHER monitors' scores on the "
              "calibration trajectories (`xfer_avg`) vs the target's own offsets (`self_offset`), CFAR, partial "
              "pooling and global. `ctx-FPR SD` = SD across contexts of the replicate-averaged per-context FPR "
              "(bias-only dispersion; lower = better equalized). Averages over the monitors of each group "
              "(LinuxArena sweep: 12 monitors, 10 honest per env per half).\n")
    rules = ["global", "cfar", "pooled_cv", "self_offset", "xfer_avg", "stack"]
    g = s[s.rule.isin(rules)].groupby(["group", "B", "mode", "rule"])[
        ["spend", "fpr_ctx_sd", "fpr_ctx_min", "fpr_ctx_max", "tpr_uniform", "sel_informed", "matched_ok"]].mean().reset_index()
    g["o"] = g.rule.map({r: i for i, r in enumerate(rules)})
    g = g.sort_values(["group", "B", "mode", "o"])
    table(g, ["group", "B", "mode", "rule", lambda r: f"{r.spend:.3f}", lambda r: f"{r.fpr_ctx_sd:.3f}",
              lambda r: f"{r.fpr_ctx_min:.3f}–{r.fpr_ctx_max:.3f}", lambda r: f"{r.tpr_uniform:.2f}",
              lambda r: f"{r.sel_informed:.2f}", lambda r: f"{r.matched_ok:.2f}"],
          ["group", "B", "mode", "rule", "spend", "ctx-FPR SD", "ctx-FPR range", "uniform TPR", "sel", "matched_ok"])
    # per-monitor paired view (LinuxArena sweep, matched): ctx-FPR SD, xfer vs global
    x = s[(s.group == "lasweep") & (s["mode"] == "matched")]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for ax, met, lab in zip(axes, ["fpr_ctx_sd", "sel_informed"],
                            ["SD of per-env FPR across envs", "safety vs informed attacker"]):
        for j, (r, l, c) in enumerate([("global", "Global", COL["global"]), ("cfar", "CFAR", COL["cfar"]),
                                       ("self_offset", "Own offsets (n=10/env)", COL["self"]),
                                       ("xfer_avg", "Offsets from other monitors", COL["xfer"])]):
            for bi, B in enumerate((0.05, 0.1)):
                q = x[(x.rule == r) & (x.B == B)]
                xs = bi * 5 + j + np.linspace(-0.25, 0.25, len(q))
                ax.scatter(xs, q[met], s=12, color=c, marker=MARK[j], edgecolor="white", lw=0.4,
                           label=l if bi == 0 else None)
                ax.plot([bi * 5 + j - 0.3, bi * 5 + j + 0.3], [q[met].mean()] * 2, color=S.INK, lw=1.2)
        ax.set_xticks([1.5, 6.5])
        ax.set_xticklabels(["B = 5%", "B = 10%"])
        ax.set_ylabel(lab)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.1, -0.12), ncol=4, fontsize=6.8)
    fig.suptitle("LinuxArena sweep, 12 target monitors (dots), spend-matched", fontsize=9)
    S.save(fig, FIG / "e1c_monitor_transfer.pdf")


def e2():
    s = load("e2_multipoison_full.csv")
    if s is None:
        return
    MD.append("## E2: multi-context poisoning (target-context TPR, averaged over targets)\n")
    rules = ["global", "cfar", "pooled_eb", "os_loco", "tm_loco", "frozen", "refmix", "os_frozen", "os_median",
             "os_lowq", "os_trim", "os_capped", "os_guard"]
    rules = [r for r in rules if r in set(s.rule)]
    for B in (0.01, 0.05):
        x = s[(s.B == B) & s.eps.isin([0, 0.02, 0.05, 0.1]) & ~s.scen.str.startswith("drift")]
        if not len(x):
            continue
        MD.append(f"### B = {B:.0%}: target TPR (eps = poisoned fraction of each poisoned context's window)\n")
        pv = x.pivot_table(index=["panel", "scen", "eps"], columns="rule", values="tpr_t")[rules].round(2).reset_index()
        table(pv, list(pv.columns), list(pv.columns))
    d = s[s.scen.isin(["clean", "drift_tail", "drift_shift", "drift_target"])]
    MD.append("### Realized spend under genuine drift (no attacker)\n")
    pv = d.pivot_table(index=["panel", "B", "scen"], columns="rule", values="spend")[rules].round(3).reset_index()
    table(pv, list(pv.columns), list(pv.columns))
    # breakdown summary: worst-case over scenarios of target TPR at each eps, and drift spend ratio
    MD.append("### Summary: worst target TPR over poisoning scenarios vs worst spend/B over drift controls\n")
    rows = []
    for (p, B), g in s.groupby(["panel", "B"]):
        for r in rules:
            q = g[g.rule == r]
            clean = q[q.scen == "clean"].tpr_t.mean()
            w = {e: q[(q.eps == e) & ~q.scen.isin(["clean"]) & ~q.scen.str.startswith("drift")].groupby("scen").tpr_t.mean().min()
                 for e in (0.02, 0.05, 0.1)}
            dr = q[q.scen.str.startswith("drift")].groupby("scen").spend.mean().max() / B
            rows.append(dict(panel=p, B=B, rule=r, clean=round(clean, 2), worst_eps2=round(w[0.02], 2),
                             worst_eps5=round(w[0.05], 2), worst_eps10=round(w[0.1], 2), drift_spend_x=round(dr, 2)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "e2_breakdown_summary.csv", index=False)
    table(t, list(t.columns), ["panel", "B", "rule", "clean TPR", "worst @2%", "worst @5%", "worst @10%",
                               "max drift spend / B"])
    # figure: TPR vs eps per scenario, two strong panels at B = 1%
    show = [("global", "Global"), ("cfar", "CFAR"), ("os_loco", "OS-CFAR, LOCO tail (round 1)"),
            ("os_frozen", "OS-CFAR, frozen-reference tail"), ("os_lowq", "OS-CFAR, low-quantile tail"),
            ("os_guard", "OS-CFAR, guarded tail")]
    show = [z for z in show if z[0] in rules]
    scen = [("target", "target only"), ("one_other", "one other ctx"), ("half_others", "half of others"),
            ("all_others", "all others"), ("all", "all contexts")]
    pans = ["la_env_local", "akshn_setting", "ca_setting_model"]
    fig, axes = plt.subplots(len(pans), len(scen), figsize=(7.4, 5.0), sharex=True, sharey=True)
    for i, p in enumerate(pans):
        for j, (sc, sl) in enumerate(scen):
            ax = axes[i, j]
            for k, (r, lab) in enumerate(show):
                q = s[(s.panel == p) & (s.B == 0.01) & (s.rule == r) & s.scen.isin([sc, "clean"])].sort_values("eps")
                ax.plot(q.eps * 100, q.tpr_t, marker=MARK[k], color=COL.get(r, S.SERIES[k]), ms=3.2, lw=1.2,
                        label=lab if (i, j) == (0, 0) else None)
            ax.set_xscale("symlog", linthresh=1)
            ax.set_xticks([0, 1, 2, 5, 10, 20])
            ax.set_xticklabels(["0", "1", "2", "5", "10", "20"], fontsize=6)
            ax.set_ylim(0, 1)
            if i == 0:
                ax.set_title(sl, fontsize=8)
            if j == 0:
                ax.set_ylabel(f"{PANEL_LABEL[p]}\ntarget TPR", fontsize=7)
            if i == len(pans) - 1:
                ax.set_xlabel("poison % per ctx")
    fig.legend(loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.07))
    fig.suptitle("Poisoning spread over contexts, B = 1%", fontsize=9)
    S.save(fig, FIG / "e2_multipoison.pdf")
    # drift figure
    fig, ax = plt.subplots(figsize=(6.8, 2.6))
    dd = d[(d.B == 0.01) & d.panel.isin(pans)]
    sc = ["clean", "drift_tail", "drift_shift", "drift_target"]
    for k, (r, lab) in enumerate(show + [("frozen", "Frozen reference CFAR")]):
        ys = [dd[(dd.rule == r) & (dd.scen == c)].spend.mean() / 0.01 for c in sc]
        ax.plot(np.arange(len(sc)) + (k - 3) * 0.08, ys, MARK[k % len(MARK)], color=COL.get(r, S.SERIES[k]), ms=5,
                label=lab)
    ax.axhline(1, color=S.INK2, ls="--", lw=0.8)
    ax.set_xticks(range(len(sc)))
    ax.set_xticklabels(["no drift", "heavier tail, all ctx", "shift, all ctx", "shift, one ctx"])
    ax.set_ylabel("realized spend / B (B = 1%)")
    ax.legend(fontsize=6.5, ncol=2, loc="upper left")
    ax.set_title("Genuine drift: who tracks it (mean over 3 strong panels)", fontsize=9)
    S.save(fig, FIG / "e2_drift_spend.pdf")


def e3():
    s = load("e3_severity_full.csv")
    if s is None:
        return
    c = load("e3_severity_correlations.csv")
    MD.append("## E3: severity-weighted damage\n")
    if c is not None:
        MD.append("Adjudicated severity (aksh-n `overall_severity`, 0–10) of attack trajectories vs the "
                  "monitor's trajectory score and vs the side-task tier:\n")
        table(c.round(3), list(c.columns), list(c.columns))
    MD.append("Spend-matched. `dmg_cell` = 1 − expected undetected damage in the (context, side task) cell "
              "an informed damage-maximizing attacker picks / D_max; `dmg_ctx` = same when it picks only a "
              "context; `dmg_unif` = damage-weighted TPR; Δ vs global paired bootstrap.\n")
    rules = ["global", "cfar", "pooled_cv", "stack", "stack_dctx", "mm_cell_eq", "mm_cell_dmg", "mm_cell_dmg_s", "mm_cell_tier"]
    x = s[(s["mode"] == "matched") & s.rule.isin(rules)].copy()
    x["o"] = x.rule.map({r: i for i, r in enumerate(rules)})
    x = x.sort_values(["panel", "damage", "B", "o"])
    table(x, ["panel", "damage", "B", "rule", lambda r: ci(r, "dmg_cell_inf"), lambda r: dci(r, "dmg_cell_inf"),
              lambda r: f"{r.dmg_ctx_inf:.2f}", lambda r: f"{r.dmg_uniform:.2f}", lambda r: f"{r.tpr_cell_inf:.2f}",
              lambda r: f"{r.tpr_uniform:.2f}"],
          ["panel", "damage", "B", "rule", "dmg_cell [95%]", "Δ vs global", "dmg_ctx", "dmg_unif", "TPR in chosen cell",
           "uniform TPR"])
    rowsel = [("akshn_setting", "adjudicated"), ("akshn_setting", "equal"), ("ca_setting_model", "adjudicated"),
              ("ca_setting_model", "equal"), ("la_env_local", "adjudicated"), ("mb_gpt-4.1-mini_trajectory", "tier_steep")]
    show = [("global", "Global"), ("cfar", "CFAR"), ("stack", "Stackelberg (ctx, equal dmg)"),
            ("stack_dctx", "Stackelberg (ctx, severity)"), ("mm_cell_eq", "Minimax cells (equal dmg)"),
            ("mm_cell_dmg_s", "Minimax cells (severity, shrunk)")]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4), sharey=True)
    for ax, B in zip(axes, (0.01, 0.05)):
        for yi, (p, d) in enumerate(rowsel):
            q0 = x[(x.panel == p) & (x.damage == d) & (x.B == B)]
            for j, (r, lab) in enumerate(show):
                q = q0[q0.rule == r]
                if not len(q):
                    continue
                q = q.iloc[0]
                y = yi + (j - 2.5) * 0.12
                ax.plot(q.dmg_cell_inf, y, ["o", "s", "D", "^", "v", "*"][j], color=COL[r],
                        ms=6 if j == 5 else 4.5, mec="white", mew=0.4, label=lab if yi == 0 else None)
        ax.set_yticks(range(len(rowsel)))
        ax.set_yticklabels([f"{PANEL_LABEL[p]}\ndamage: {d}" for p, d in rowsel], fontsize=6.6)
        ax.invert_yaxis()
        ax.set_xlim(-0.02, 1.02)
        ax.set_title(f"B = {B:.0%}")
    for ax in axes:
        ax.set_xlabel("damage safety in attacker's cell", fontsize=7.5)
    fig.suptitle("Safety = 1 − expected undetected damage in the (context, side task) cell the attacker picks / D_max",
                 fontsize=8.5)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.0, -0.2), ncol=3, fontsize=6.8)
    S.save(fig, FIG / "e3_severity.pdf")


def e4():
    s = load("e4_adaptive_full.csv")
    if s is None:
        return
    MD.append("## E4a: probing attacker (alarm feedback on q probes per context)\n")
    MD.append("`free`: probes reveal alarms without consequence; `costly`: any probe alarm catches the "
              "attacker. q = 0 is a uniform attacker; `informed` knows the thresholds exactly.\n")
    qs = (0, 1, 2, 3, 5, 10, 20, 50)
    rules = ["global", "cfar", "pooled_cv", "os_shift", "maxdet", "stack"]
    x = s[s.rule.isin(rules)].copy()
    x["o"] = x.rule.map({r: i for i, r in enumerate(rules)})
    x = x.sort_values(["panel", "B", "o"])
    cols = ["panel", "B", "rule", lambda r: f"{r.tpr_uniform:.2f}"] + \
           [(lambda q: (lambda r: f"{r[f'probe{q}_free']:.2f}"))(q) for q in (1, 3, 5, 20)] + \
           [lambda r: ci(r, "sel_informed"), lambda r: f"{r['probe5_costly']:.2f}"]
    table(x, cols, ["panel", "B", "rule", "uniform", "q=1", "q=3", "q=5", "q=20", "informed [95%]", "q=5 costly"])
    MD.append("## E4b: estimation error\n")
    MD.append("Defender fits Stackelberg / max-detection with n_d calibration attacks per context "
              "(`_m0`: shrunk toward pooled attacks, m0 = 10); safety vs the fully informed attacker. "
              "Attacker columns: the informed attacker estimates its evasion from n_a bootstrap-resampled "
              "attacks per context.\n")
    nd = [3, 5, 10, 20, 50]
    rows = []
    for (p, B), g in s.groupby(["panel", "B"]):
        g = g.set_index("rule")
        r = dict(panel=p, B=B, global_=round(g.loc["global", "sel_informed"], 2))
        for n in nd:
            for k in ("stack", "stack_m0", "maxdet"):
                if f"{k}_nd{n}" in g.index:
                    r[f"{k}_nd{n}"] = round(g.loc[f"{k}_nd{n}", "sel_informed"], 2)
        r["stack_all"] = round(g.loc["stack", "sel_informed"], 2)
        rows.append(r)
    t = pd.DataFrame(rows)
    keep = ["panel", "B", "global_"] + [f"stack_nd{n}" for n in nd] + ["stack_all"] + [f"stack_m0_nd{n}" for n in nd] + \
           [f"maxdet_nd{n}" for n in (3, 10, 50)]
    table(t[keep], keep, keep)
    rows = []
    for _, r in x.iterrows():
        rows.append(dict(panel=r.panel, B=r.B, rule=r.rule, **{f"n_a={n}": round(r[f"att_na{n}"], 2) for n in (3, 10, 30)},
                         informed=round(r.sel_informed, 2), uniform=round(r.tpr_uniform, 2)))
    t2 = pd.DataFrame(rows)
    table(t2, list(t2.columns), list(t2.columns))
    # figures
    pans = ["ca_setting_model", "akshn_setting", "la_taskcat_local", "mb_gpt-4.1-nano_trajectory"]
    show = [("global", "Global"), ("cfar", "CFAR"), ("maxdet", "Max-detection"), ("stack", "Stackelberg")]
    fig, axes = plt.subplots(2, len(pans), figsize=(7.4, 3.8), sharex=True)
    for i, B in enumerate((0.01, 0.05)):
        for j, p in enumerate(pans):
            ax = axes[i, j]
            for k, (r, lab) in enumerate(show):
                q = s[(s.panel == p) & (s.B == B) & (s.rule == r)]
                if not len(q):
                    continue
                q = q.iloc[0]
                ys = [q[f"probe{n}_free"] for n in qs]
                ax.plot(np.array(qs) + 0.5, ys, marker=MARK[k], color=COL[r], ms=3, lw=1.2,
                        label=lab if (i, j) == (0, 0) else None)
                ax.axhline(q.sel_informed, color=COL[r], lw=0.7, ls=":")
            ax.set_xscale("log")
            ax.set_xticks([0.5, 1.5, 5.5, 20.5])
            ax.set_xticklabels(["0", "1", "5", "20"])
            if i == 0:
                ax.set_title(PANEL_LABEL[p], fontsize=7.5)
            if j == 0:
                ax.set_ylabel(f"B = {B:.0%}\nsafety")
            if i == 1:
                ax.set_xlabel("probes per context")
    fig.legend(loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Attacker learns thresholds from alarm feedback (dotted: exact knowledge)", fontsize=9)
    S.save(fig, FIG / "e4_probes.pdf")
    fig, axes = plt.subplots(1, len(pans), figsize=(7.4, 2.5), sharey=False)
    for j, p in enumerate(pans):
        ax = axes[j]
        g = s[(s.panel == p) & (s.B == 0.05)].set_index("rule")
        for k, (pre, lab, c) in enumerate([("stack", "Stackelberg", COL["stack"]),
                                           ("stack_m0", "Stackelberg, shrunk", COL["stack_l50"]),
                                           ("maxdet", "Max-detection", COL["maxdet"])]):
            ys = [g.loc[f"{pre}_nd{n}", "sel_informed"] for n in nd]
            ax.plot(nd, ys, marker=MARK[k + 1], color=c, ms=3.5, label=lab if j == 0 else None)
        ax.axhline(g.loc["global", "sel_informed"], color=COL["global"], ls="--", lw=1,
                   label="Global" if j == 0 else None)
        ax.set_xscale("log")
        ax.set_xticks(nd)
        ax.set_xticklabels([str(n) for n in nd])
        ax.minorticks_off()
        ax.set_title(PANEL_LABEL[p], fontsize=7.5)
        ax.set_xlabel("attacks per context", fontsize=7.5)
        if j == 0:
            ax.set_ylabel("safety (B = 5%)")
    fig.legend(loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.16))
    fig.suptitle("Defender fits Stackelberg from few attacks per context (B = 5%, informed attacker)", fontsize=9)
    fig.tight_layout()
    S.save(fig, FIG / "e4_defender_nd.pdf")


def main():
    S.setup()
    MD.append("# T2 round 2 tables (generated by tracks/r2_t2/make_report.py)\n")
    for f in (e1a, e1b, e1c, e2, e3, e4):
        f()
    extra = R.OUT / "e5_tables.md"
    if extra.exists():
        MD.append(extra.read_text())
    (OUT / "tables.md").write_text("\n".join(MD))
    print("wrote", OUT / "tables.md")


if __name__ == "__main__":
    main()
