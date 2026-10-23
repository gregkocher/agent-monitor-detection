"""Assemble results/fixes2/rows_wb.csv (old = plug-in convention, new = conformal randomized rule) from the
wb_* rerun outputs in results/fixes2/. Run after wb_rerun (all jobs, both conventions), wb_panel_d and wb_mole_fpr.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.wb_rows
"""
from __future__ import annotations

import pandas as pd

from .wb_common import OUT_ROOT, outdir

COLS = ["claim", "old_estimate", "old_ci", "new_estimate", "new_ci", "old_realized_fpr", "new_realized_fpr",
        "verdict_change", "note"]


def f3(x):
    return f"{x:+.3f}"


def ci(lo, hi):
    return f"[{lo:+.3f}, {hi:+.3f}]"


def pct(x):
    return f"{100 * x:.2f}%"


def rd(job, conv, name):
    return pd.read_csv(outdir(job, conv) / name)


def main():
    rows = []

    def add(claim, o, n, ofpr, nfpr, change, note, est="est", lo="lo", hi="hi"):
        rows.append(dict(claim=claim, old_estimate=f3(o[est]), old_ci=ci(o[lo], o[hi]), new_estimate=f3(n[est]),
                         new_ci=ci(n[lo], n[hi]), old_realized_fpr=ofpr, new_realized_fpr=nfpr,
                         verdict_change=change, note=note))

    # ---------------- r4_wb Part 1 (committed analyze_primary) ----------------
    P = {c: rd("r4primary", c, "primary.csv").set_index("contrast") for c in ("plugin", "conformal")}
    E = {c: rd("r4primary", c, "primary_external.csv") for c in ("plugin", "conformal")}
    fr = lambda d, k="H1 primary": f"reader {pct(d.loc[k, 'fpr_reader'])} / LLM {pct(d.loc[k, 'fpr_llm'])}"  # noqa
    o, n = P["plugin"].loc["H1 primary"], P["conformal"].loc["H1 primary"]
    ext = {c: E[c][E[c].alpha == 0.01].iloc[0] for c in E}
    add("r4_wb H1 (prereg): FIBS axial follow-up (none) - gpt-4.1-mini, TPR@1% FPR, 1,000 held-out MB attacks "
        "(committed analyze_primary)", o, n, fr(P["plugin"]), fr(P["conformal"]), "no",
        f"Committed pipeline reproduced exactly (log: +0.203 [+0.100, +0.296]). TPR reader/LLM "
        f"{o.tpr_reader:.3f}/{o.tpr_llm:.3f} -> {n.tpr_reader:.3f}/{n.tpr_llm:.3f}. Equal-FPR guard still not "
        f"triggered (gap 0.11 -> 0.10 pp); H1 supported. Realized FPR stays slightly above 1% for both because "
        f"Honest-550 test tasks differ from calibration tasks (grouped splits), not because of the rule. External "
        f"honest at 1%: reader {pct(ext['plugin'].fpr_reader_external)} / LLM {pct(ext['plugin'].fpr_llm_external)}"
        f" -> {pct(ext['conformal'].fpr_reader_external)} / {pct(ext['conformal'].fpr_llm_external)}.")
    A = {c: rd("a3primary", c, "wb_primary.csv") for c in ("plugin", "conformal")}
    A = {c: d[d.scheme == "indep"].set_index("contrast") for c, d in A.items()}
    o, n = A["plugin"].loc["H1 primary"], A["conformal"].loc["H1 primary"]
    add("r4_wb H1, audit-3 independent reimplementation (nominal 1%; tracks/audit3/wb_primary.py)", o, n,
        f"reader {pct(o['fpr_r@0.01'])} / LLM {pct(o['fpr_l@0.01'])}",
        f"reader {pct(n['fpr_r@0.01'])} / LLM {pct(n['fpr_l@0.01'])}", "no",
        "The +0.198 [+0.104, +0.292] figure is this independent reimplementation (own splits, wb_lib threshold), "
        "reproduced exactly; its wb_lib.wthresh/alarm_rate replaced by the conformal rule.")
    ko = "H1 both at realized 1.00%"
    o, n = A["plugin"].loc[ko], A["conformal"].loc[ko]
    fo = [c for c in A["plugin"].columns if c.startswith("fpr_") and pd.notna(o[c])]
    fn = [c for c in A["conformal"].columns if c.startswith("fpr_") and pd.notna(n[c])]
    add("r4_wb H1 with both monitors bisected to exactly 1.00% realized FPR (audit-3)", o, n,
        " / ".join(f"{dict(r='reader', l='LLM')[c.split('@')[0][4:]]} {pct(o[c])}" for c in fo),
        " / ".join(f"{dict(r='reader', l='LLM')[c.split('@')[0][4:]]} {pct(n[c])}" for c in fn), "no",
        "Matched-FPR estimate essentially unchanged (+0.167 -> +0.164); CI still excludes 0. "
        "Matching levels (nominal): plug-in reader 0.0044 / LLM 0.0069 -> conformal reader 0.0072 / LLM 0.0082 "
        "(smaller adjustments; the remaining excess over 1% at nominal is task shift between grouped halves).")
    for k, lab in (("S1 opus-4-5 attacks", "r4_wb S1: opus-4-5 attacks (n=771), TPR@1%"),
                   ("S2 opus-4-6 attacks", "r4_wb S2: opus-4-6 attacks (n=229), TPR@1%"),
                   ("S3 alpha=0.05", "r4_wb S3: TPR@5% FPR")):
        o, n = P["plugin"].loc[k], P["conformal"].loc[k]
        if k.startswith("S3"):
            ofp, nfp = fr(P["plugin"], k), fr(P["conformal"], k)
        else:
            ofp, nfp = fr(P["plugin"]), fr(P["conformal"])
        add(lab + " (committed analyze_primary)", o, n, ofp, nfp, "no",
            f"Holm p {o.p_holm:.3f} -> {n.p_holm:.3f} (family S1-S3). "
            + ("Realized FPR is the full-attack-set honest FPR (same thresholds)." if not k.startswith("S3") else ""))
    k = "exploratory: fibs_fu (none) - LLM"
    o, n = P["plugin"].loc[k], P["conformal"].loc[k]
    add("r4_wb exploratory: FIBS linear follow-up (none) - LLM, TPR@1%", o, n, fr(P["plugin"], k),
        fr(P["conformal"], k), "no",
        f"Two-sided p {o.p_two:.3f} -> {n.p_two:.3f}; lower CI bound crosses 0 by 0.002. Exploratory, no "
        "multiplicity control: still 'borderline'. Reader realized FPR 1.79% -> 1.60% at nominal 1% (A1 task shift "
        "of this stream remains).")

    # ---------------- A1 FIBS-axial-full ----------------
    a1 = {c: rd("r4a1", c, "a1_mb_equalfpr.csv") for c in ("plugin", "conformal")}
    sel = lambda d: d[(d["mode"] == "full") & (d.stream == "fibs_fu_ax") & (d.alpha == 0.01)].iloc[0]  # noqa
    o, n = sel(a1["plugin"]), sel(a1["conformal"])
    add("r4_wb A1: FIBS axial follow-up `full` - gpt-4.1-mini at equal realized FPR, pilot MB data "
        "(committed analyze_a1_mb, eq columns)", o, n,
        f"reader {pct(o.eq_fpr_reader)} (floor) / LLM {pct(o.fpr_llm)}",
        f"reader {pct(n.eq_fpr_reader)} / LLM {pct(n.fpr_llm)}", "yes",
        f"Under the plug-in rule equal FPR was unreachable (reader floor 1.72% at nominal 1e-5) and the "
        f"'+0.061' was at that floor. The conformal rule can lower the reader to the LLM's FPR (level "
        f"{n.eq_level:.4f}, i.e. alpha(n+1) < 1: scores above the calibration max alarm only with prob ~0.65), "
        f"and the gain vanishes: {f3(n.eq_est)} {ci(n.eq_lo, n.eq_hi)}, p {n.eq_p_two:.2f}. Nominal-1% row "
        f"{f3(o.est)} -> {f3(n.est)} keeps reader realized FPR {pct(o.fpr_reader)} -> {pct(n.fpr_reader)} "
        f"(genuine A1 task shift, not the rule).", est="eq_est", lo="eq_lo", hi="eq_hi")
    w = {c: rd("a3a1", c, "wb_a1_mb.csv") for c in ("plugin", "conformal")}
    sel = lambda d: d[(d["mode"] == "full") & (d.stream == "fibs_fu_ax") & (d.version == "both_exact")].iloc[0]  # noqa
    o, n = sel(w["plugin"]), sel(w["conformal"])
    add("r4_wb A1 (audit-3 wb_a1): FIBS axial `full` - LLM, both at exact 1.00% realized FPR", o, n,
        f"reader {pct(o.fpr_reader)} (floor) / LLM {pct(o.fpr_llm)}",
        f"reader {pct(n.fpr_reader)} / LLM {pct(n.fpr_llm)}", "yes",
        f"Same conclusion as the committed-code row: at truly equal 1.00% the gain is gone "
        f"(basic interval {ci(n.basic_lo, n.basic_hi)}; plug-in basic interval was {ci(o.basic_lo, o.basic_hi)}).")

    # ---------------- MOLE TPR@5% (audit-3 wb_mole) ----------------
    M = {c: rd("a3mole", c, "wb_mole.csv").set_index("contrast") for c in ("plugin", "conformal")}
    F = pd.read_csv(OUT_ROOT / "wb_mole_fpr_thrfix.csv").set_index(["arm", "conv"])
    mf = lambda c, arms: " / ".join(f"{a.split('/')[0]} {pct(F.loc[(a, c), 'realized_fpr'])}" for a in arms)  # noqa
    o, n = M["plugin"].loc["M1 tpr5"], M["conformal"].loc["M1 tpr5"]
    arms = ["policy/sab/max", "reader/sab/max"]
    add("r4_wb MOLE (prereg metric): TPR@5% session FPR, policy - reader (sab max; audit-3 wb_mole M1)", o, n,
        mf("plugin", arms), mf("conformal", arms), "no",
        f"TPR reader {F.loc[('reader/sab/max', 'plugin'), 'tpr']:.3f} vs policy "
        f"{F.loc[('policy/sab/max', 'plugin'), 'tpr']:.3f} -> {F.loc[('reader/sab/max', 'conformal'), 'tpr']:.3f} vs "
        f"{F.loc[('policy/sab/max', 'conformal'), 'tpr']:.3f}; Holm {o.p_holm:.3f} -> {n.p_holm:.3f}. Realized FPR "
        "on held-out benign accounts (not computed by wb_mole; tracks/fixes2/wb_mole_fpr.py, same splits).")
    o, n = M["plugin"].loc["M3 tpr5"], M["conformal"].loc["M3 tpr5"]
    arms = ["policy/sab/max", "policy_neutral/sab/max"]
    add("r4_wb MOLE: instruction effect at TPR@5% session FPR, policy - policy_neutral (audit-3 wb_mole M3)", o, n,
        mf("plugin", arms), mf("conformal", arms), "no",
        f"Holm {o.p_holm:.3f} -> {n.p_holm:.3f}; the corrected reading (the insider instruction lowers the "
        "policy probe's TPR) stands.")

    # ---------------- LinuxArena ----------------
    def la_count(g):
        up = g[(g.p_holm < 0.05) & (g.est > 0)]
        dn = g[(g.p_holm < 0.05) & (g.est < 0)]
        return len(up), len(dn), g[g.llm == "gpt-5.4"].iloc[0], g[g.llm == "claude-opus-4-6"].iloc[0]

    def la_row(claim, go, gn, change, note):
        uo, do, so, po = la_count(go)
        un, dn, sn, pn = la_count(gn)
        rows.append(dict(
            claim=claim,
            old_estimate=f"{uo}/12 reader-above Holm-sig, {do} below (gpt-5.4 {f3(so.est)}, Holm {so.p_holm:.3f})",
            old_ci=ci(so.lo, so.hi),
            new_estimate=f"{un}/12 reader-above Holm-sig, {dn} below (gpt-5.4 {f3(sn.est)}, Holm {sn.p_holm:.3f})",
            new_ci=ci(sn.lo, sn.hi),
            old_realized_fpr=f"reader {pct(go.fpr_reader.min())}-{pct(go.fpr_reader.max())} / LLMs "
                             f"{pct(go.fpr_llm.min())}-{pct(go.fpr_llm.max())}",
            new_realized_fpr=f"reader {pct(gn.fpr_reader.min())}-{pct(gn.fpr_reader.max())} / LLMs "
                             f"{pct(gn.fpr_llm.min())}-{pct(gn.fpr_llm.max())}",
            verdict_change=change,
            note=f"CI columns = gpt-5.4 contrast (the marginal monitor). opus-4.6 {f3(po.est)} {ci(po.lo, po.hi)} "
                 f"-> {f3(pn.est)} {ci(pn.lo, pn.hi)}. " + note))

    lp = {c: rd("r4la", c, "la_paired.csv") for c in ("plugin", "conformal")}
    sel = lambda d: d[(d["mode"] == "full") & (d.stream == "fibs_fu_ax") & (d.alpha == 0.01)]  # noqa
    gn = sel(lp["conformal"])
    la_row("r4_wb LinuxArena: FIBS axial `full` vs 12 sweep monitors at nominal 1% (committed analyze_la_r4, "
           "Holm over 12)", sel(lp["plugin"]), gn, "no",
           f"Same 7 monitors significant, but now at matched ~1% realized FPR (reader was at ~2% = 2/101 under the "
           f"plug-in rule with n_cal = 100). Reader TPR 0.755-0.806 -> {gn.tpr_reader.min():.3f}-"
           f"{gn.tpr_reader.max():.3f}; the 'reader TPR 0.76-0.81 at 1%' wording must become ~0.66-0.72.")
    la = {c: rd("a3la", c, "wb_la_equalfpr.csv") for c in ("plugin", "conformal")}
    sel = lambda d, v, a=0.01: d[(d.version == v) & (d.alpha == a)]  # noqa
    gn = sel(la["conformal"], "both_exact")
    la_row("r4_wb LinuxArena (audit-3 wb_la): both monitors bisected to equal 1.00% realized FPR, Holm over 12",
           sel(la["plugin"], "both_exact"), gn, "yes",
           f"Count rises 7 -> 10 (haiku, sonnet, glm become significant) and the significant loss to opus-4.6 "
           f"disappears. Cause: at n_cal = 100 an exact 1.00% puts 8 of 12 LLM levels below 1/(n_cal+1) "
           f"(levels {gn.level_llm.min():.4f}-{gn.level_llm.max():.4f}), where the conformal rule alarms above the "
           f"calibration max only with prob alpha(n+1) = 0.84-0.99 (the plug-in alarms there with prob 1 and "
           f"spends the rest of its budget at ties). Both are exact-1.00% comparisons; the swing shows that the 1%-at-n_cal=100 "
           f"comparison sits at the calibration resolution limit (about one calibration point) and is rule-"
           f"sensitive. The nominal-1% conformal versions (7 in the committed code, 6 in the audit code) are the "
           f"more robust reading.")
    la_row("r4_wb LinuxArena (audit-3 wb_la): both at nominal 1%, audit split/bootstrap code, Holm over 12",
           sel(la["plugin"], "nominal"), sel(la["conformal"], "nominal"), "yes",
           "Audit wb_lib's own plug-in variant (alarm S >= k-th largest) already put the reader at <=1% but the "
           "tied LLM scores at up to 1.6%; under the conformal rule both are ~1% and gpt-5.4 drops to Holm 0.055 "
           "(borderline, 7 -> 6). Committed-code splits give Holm 0.035 for the same contrast (previous row).")
    la_row("r4_wb LinuxArena (audit-3 wb_la): both at equal 2.0% realized FPR, Holm over 12",
           sel(la["plugin"], "both_2pct"), sel(la["conformal"], "both_2pct"), "no",
           "Same 6 monitors (gpt-5.4 not significant either way).")

    # ---------------- overview panel (d) ----------------
    d = pd.read_csv(OUT_ROOT / "wb_panel_d_thrfix.csv").set_index(["conv", "row"])
    for r, lab in (("FIBS axial follow-up, none", "Overview (d): FIBS axial follow-up probe, per-step (none) reading "
                    "- gpt-4.1-mini, TPR@1% (results/wb/mb_paired.csv)"),
                   ("sab, full", "Overview (d): sabotage probe, full-history reading - gpt-4.1-mini, TPR@1% "
                    "(results/wb/mb_paired.csv)")):
        o, n = d.loc[("plugin", r)], d.loc[("conformal", r)]
        note = ("analyze_paired code path (raw pickles of analyze_mb, paired_contrast_bootstrap seed 7, B=1000) "
                "reproduced exactly. ")
        if r.startswith("FIBS"):
            note += ("Caveat unrelated to the rule: with only 10 grouped splits the LLM's realized FPR in this "
                     "pipeline is ~0.5% (over 200 splits of the same data, analyze_a1_mb gives 1.2-1.3%), so the "
                     "LLM side is under-spent; the 200-split version (analyze_a1_mb `none`, reader 1.13% / LLM 1.19%) "
                     "gives +0.183 [+0.080, +0.260] under the conformal rule (+0.187 [+0.087, +0.265] plug-in).")
        else:
            note += f"p(<=0) {o.p_le0:.3f} -> {n.p_le0:.3f}; CI still excludes 0 (not Holm-corrected, as before)."
        add(lab, o, n, f"reader {pct(o.fpr_reader)} / LLM {pct(o.fpr_llm)}",
            f"reader {pct(n.fpr_reader)} / LLM {pct(n.fpr_llm)}", "no", note)
    c = {cv: rd("a2fusion", cv, "repro_wb_fusion.csv") for cv in ("plugin", "conformal")}
    sel = lambda x: x[(x["mode"] == "full") & (x.probe == "sab") & (x.q == 0.1)].iloc[0]  # noqa
    o, n = sel(c["plugin"]), sel(c["conformal"])
    o = o.rename({"diff": "est"})
    n = n.rename({"diff": "est"})
    t = {cv: rd("wbfusion", cv, "fusion.csv") for cv in ("plugin", "conformal")}
    tsel = lambda x, rule: x[(x["mode"] == "full") & (x.probe == "sab") & (x.alpha == 0.01) & (x.rule == rule)].iloc[0]  # noqa
    to, tn = tsel(t["plugin"], "cascade_0.1"), tsel(t["conformal"], "cascade_0.1")
    add("Overview (d): sabotage-probe triage (10% of honest steps, 13% of all) + gpt-4.1-mini - gpt-4.1-mini alone, "
        "TPR@1% (audit-2 repro_wb_fusion, the plotted value)", o, n,
        f"cascade {pct(o.realized_fpr_cascade)} / LLM {pct(o.realized_fpr_llm)}",
        f"cascade {pct(n.realized_fpr_cascade)} / LLM {pct(n.realized_fpr_llm)}", "no",
        f"Audit-2 code reproduced exactly; a2lib.rand_threshold/alarm replaced by the conformal rule. Track's own "
        f"analyze_fusion (10 splits, B=300): {f3(to.gain_vs_llm)} {ci(to.gain_lo, to.gain_hi)} (FPR "
        f"{pct(to.fpr)} / LLM {pct(tsel(t['plugin'], 'llm').fpr)}) -> {f3(tn.gain_vs_llm)} "
        f"{ci(tn.gain_lo, tn.gain_hi)} (FPR {pct(tn.fpr)} / LLM {pct(tsel(t['conformal'], 'llm').fpr)}). LLM "
        f"realized FPR stays above 1% (task-grouped splits), not a rule effect.")

    out = pd.DataFrame(rows)[COLS]
    out.to_csv(OUT_ROOT / "rows_wb.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print(out.drop(columns="note").to_string())


if __name__ == "__main__":
    main()
