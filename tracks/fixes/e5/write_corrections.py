"""Corrections CSVs for audit issues C1, M5 (r2_t2 E5) and m2, m3, m11 (T2 / r3_t2).

Reads only result CSVs (no new computation beyond e5_allocation_fixed.py / e5_auroc_fixed.py /
e5_report_fixed.py, which must have run first) and writes
  results/fixes/r2_t2/corrections_r2_t2.csv   (C1, M5)
  results/fixes/t2/corrections_t2.csv          (m2, m3, m11)
Columns: issue_id,track,original_claim,corrected_claim,numbers_before,numbers_after,verdict

    unset VIRTUAL_ENV; uv run python tracks/fixes/e5/write_corrections.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "results"
FX = R / "fixes"
COLS = ["issue_id", "track", "original_claim", "corrected_claim", "numbers_before", "numbers_after", "verdict"]


def g(df, **kw):
    for k, v in kw.items():
        df = df[df[k] == v]
    assert len(df) == 1, (kw, len(df))
    return df.iloc[0]


def ci(x, lo, hi, sign=True):
    f = "{:+.2f}" if sign else "{:.2f}"
    return f"{f.format(x)} [{f.format(lo)}, {f.format(hi)}]"


def r2t2_rows():
    O = pd.read_csv(R / "r2_t2" / "e5_allocation.csv")
    S = pd.read_csv(FX / "r2_t2" / "e5_allocation_fixed.csv")
    EQ = pd.read_csv(FX / "r2_t2" / "e5_equal_spend_1pct.csv")
    FL = pd.read_csv(FX / "r2_t2" / "e5_spend_floor.csv")
    CN = pd.read_csv(FX / "r2_t2" / "e5_claim_counts.csv")
    A = pd.read_csv(FX / "r2_t2" / "e5_auroc_by_provenance.csv").set_index("signal")
    OH = pd.read_csv(FX / "r2_t2" / "e5_originals_honest_rules.csv")
    Sg = S[S.design == "grouped"]
    rows = []

    # ---- C1: CFAR doubling
    om = O[(O.B == 0.01) & (O["mode"] == "matched")]
    sp = om.groupby("rule").spend.agg(["min", "max"])
    fl = g(FL, design="grouped", rule="cfar")
    sh = Sg[(Sg.B == 0.01) & (Sg["mode"] == "matched") & Sg.rule.isin(["cfar", "stack", "stack_m0", "maxdet"])]
    before = []
    after = [f"1% spend-matched: not estimable for cfar (matched in {sh[sh.rule == 'cfar'].share_matched_plain.min():.2f}-"
             f"{sh[sh.rule == 'cfar'].share_matched_plain.max():.2f} of plain splits; spend floor mean "
             f"{100 * fl.floor_mean:.1f}%, 5-95% {100 * fl.floor_q05:.1f}-{100 * fl.floor_q95:.1f}%; analytic "
             f"sum_c w_c/(n_c+1) = {100 * fl.analytic_sum_w_over_ncal_plus1:.1f}%)"]
    for s in ("wb_dec_full", "wb_fibs_fu_full"):
        oc, og = g(om, signal=s, rule="cfar"), g(om, signal=s, rule="global")
        before.append(f"{s}: cfar {oc.tpr_uniform:.2f} (realized spend {100 * oc.spend:.2f}%) vs global "
                      f"{og.tpr_uniform:.2f} (spend {100 * og.spend:.2f}%)")
        e = g(EQ, signal=s, design="grouped", rule="cfar")
        m5c = g(Sg, signal=s, B=0.05, mode="matched", rule="cfar")
        m5g = g(Sg, signal=s, B=0.05, mode="matched", rule="global")
        after.append(f"{s}: at equal realized spend {100 * e.spend:.1f}% cfar {e.tpr_uniform:.2f} vs global "
                     f"{e.global_tpr_uniform:.2f}, diff {ci(e.d_tpr_uniform, e.d_tpr_uniform_q025, e.d_tpr_uniform_q975)} "
                     f"(split interval); 5% matched cfar {m5c.tpr_uniform:.2f} vs global {m5g.tpr_uniform:.2f}, paired "
                     f"{ci(m5c.tpr_uniform_d, m5c.tpr_uniform_dlo, m5c.tpr_uniform_dhi)}")
    rows.append(dict(
        issue_id="C1", track="r2_t2 (E5)",
        original_claim="CFAR roughly doubles uniform TPR for the heterogeneous probes (dec_full 0.24 -> 0.50 at 1%; "
                       "fibs_fu_full 0.35 -> 0.62), spend-matched",
        corrected_claim="The 1% 'matched' CFAR rows were clamped at 1.95-2.76% realized spend. With plug-in per-cluster thresholds "
                        "and 15-106 calibration honest runs per cluster the realized spend has a floor of ~2.5%, so a "
                        "1% spend-matched comparison is not estimable. At equal realized spend (~2.9-3.6%) CFAR still "
                        "raises uniform TPR for dec / fibs_fu probes, by ~0.15-0.2 (about 1.3-1.5x, not 2x); at 5% "
                        "matched the gain is significant for dec_full / dec_none only. All attacks here are 94% "
                        "fabricated-output rewrites.",
        numbers_before="; ".join(before), numbers_after="; ".join(after), verdict="weakened"))

    rows.append(dict(
        issue_id="C1", track="r2_t2 (E5)",
        original_claim="All 1% spend-matched rows for cfar / stack / stack_m0 / maxdet in results/r2_t2/e5_tables.md",
        corrected_claim="Not estimable: these rules cannot realize 1% test spend in most splits (spend floor above "
                        "1%). Reported instead: nominal 1% rows with their realized spend, and a comparison against "
                        "global at the same realized spend (results/fixes/r2_t2/e5_equal_spend_1pct.csv).",
        numbers_before="matched 1% realized spend: " + ", ".join(
            f"{r} {100 * sp.loc[r, 'min']:.2f}-{100 * sp.loc[r, 'max']:.2f}%" for r in ("cfar", "stack", "stack_m0",
                                                                                     "maxdet", "global")),
        numbers_after="share of plain splits matched at 1% (grouped): " + ", ".join(
            f"{r} {sh[sh.rule == r].share_matched_plain.min():.2f}-{sh[sh.rule == r].share_matched_plain.max():.2f}"
            for r in ("cfar", "stack", "stack_m0", "maxdet")) + "; nominal 1% realized spend (grouped): " + ", ".join(
            f"{r} {100 * Sg[(Sg.B == 0.01) & (Sg['mode'] == 'nominal') & (Sg.rule == r)].spend.mean():.2f}%"
            for r in ("global", "cfar", "stack", "maxdet")),
        verdict="dropped"))

    c5 = g(Sg, signal="wb_sab_full", B=0.05, mode="matched", rule="cfar")
    g5 = g(Sg, signal="wb_sab_full", B=0.05, mode="matched", rule="global")
    o5c = g(O, signal="wb_sab_full", B=0.05, mode="matched", rule="cfar")
    o5g = g(O, signal="wb_sab_full", B=0.05, mode="matched", rule="global")
    cn = g(CN, source="corrected grouped", B=0.05, mode="matched", rule="cfar", metric="sel_informed")
    rows.append(dict(
        issue_id="C1", track="r2_t2 (E5)",
        original_claim="CFAR does not raise selection safety (e.g. sab_full 0.39 vs global 0.56 at 5%)",
        corrected_claim=f"Holds in direction under the corrected design: CFAR selection safety >= global on only "
                        f"{cn.n_ge_global}/17 signals at 5% matched; no paired interval excludes 0.",
        numbers_before=f"sab_full 5%: cfar {o5c.sel_informed:.2f} vs global {o5g.sel_informed:.2f}",
        numbers_after=f"sab_full 5% matched (grouped): cfar {c5.sel_informed:.2f} vs global {g5.sel_informed:.2f}, "
                      f"paired {ci(c5.sel_informed_d, c5.sel_informed_dlo, c5.sel_informed_dhi)}",
        verdict="holds"))

    # ---- M5: Stackelberg count
    def cnt(src, B, mode):
        return g(CN, source=src, B=B, mode=mode, rule="stack", metric="sel_informed")
    o = cnt("E5 original (clamped matching, iid split)", 0.05, "matched")
    o1 = cnt("E5 original (clamped matching, iid split)", 0.01, "matched")
    i5 = cnt("corrected iid", 0.05, "matched")
    g5c = cnt("corrected grouped", 0.05, "matched")
    ex = []
    for s in ("llm_gpt-4.1_none", "wb_fibs_fu_full"):
        a, b = g(Sg, signal=s, B=0.05, mode="matched", rule="stack"), g(Sg, signal=s, B=0.05, mode="matched", rule="global")
        ex.append(f"{s} stack {a.sel_informed:.2f} vs global {b.sel_informed:.2f}, paired "
                  f"{ci(a.sel_informed_d, a.sel_informed_dlo, a.sel_informed_dhi)}")
    rows.append(dict(
        issue_id="M5", track="r2_t2 (E5)",
        original_claim="Stackelberg >= global on 14/17 signals at 5% (e.g. gpt-4.1 0.55 vs 0.31; fibs_fu_full 0.62 vs "
                       "0.40); paired intervals wide and cover 0",
        corrected_claim=f"The original matched CSV gives {o.n_ge_global}/17 at 5% (14/17 is the clamped 1% count). "
                        f"With non-clamped matching (iid split) {i5.n_ge_global}/17; with the attack split grouped by "
                        f"base attack {g5c.n_ge_global}/17. No signal has a paired interval excluding 0 in any version. "
                        f"Stackelberg's selection advantage on E5 is not established.",
        numbers_before=f"claimed 14/17; original CSV 5% matched {o.n_ge_global}/17 (1% clamped {o1.n_ge_global}/17); "
                       "gpt-4.1 0.55 vs 0.31; fibs_fu_full 0.62 vs 0.40",
        numbers_after=f"5% matched: iid {i5.n_ge_global}/17, grouped {g5c.n_ge_global}/17 (CI>0: {g5c.n_ci_above_0}); "
                      + "; ".join(ex),
        verdict="weakened"))

    # ---- M5: CFAR uniform TPR comparison under corrected design
    cu_o = g(CN, source="E5 original (clamped matching, iid split)", B=0.05, mode="matched", rule="cfar", metric="tpr_uniform")
    cu_g = g(CN, source="corrected grouped", B=0.05, mode="matched", rule="cfar", metric="tpr_uniform")
    sig_pos = Sg[(Sg.B == 0.05) & (Sg["mode"] == "matched") & (Sg.rule == "cfar") & (Sg.tpr_uniform_dlo > 0)].signal.tolist()
    eqg = EQ[(EQ.design == "grouped") & (EQ.rule == "cfar")]
    oh = OH[(OH.B == 0.05) & (OH["mode"] == "matched") & (OH.rule == "cfar")]
    rows.append(dict(
        issue_id="M5", track="r2_t2 (E5)",
        original_claim="CFAR raises uniform TPR (spend-matched) for the heterogeneous probes",
        corrected_claim=f"Grouped split, 5% matched: CFAR uniform TPR >= global on {cu_g.n_ge_global}/17 signals, paired "
                        f"interval > 0 on {cu_g.n_ci_above_0} ({', '.join(sig_pos)}). At nominal 1% (equal realized "
                        f"spend vs global) the split interval excludes 0 for "
                        f"{int((eqg.d_tpr_uniform_q025 > 0).sum())}/17 signals, all white-box probes. On the 33 "
                        f"originals (honest-only rules, no fabrication confound, 1-15 per cluster): cfar >= global on "
                        f"{int((oh.tpr_uniform_d >= 0).sum())}/17 for uniform TPR, interval > 0 on "
                        f"{int((oh.tpr_uniform_dlo > 0).sum())} (dec_none, fibs_fu_full); pooled TPR interval > 0 on "
                        f"{int((oh.tpr_pooled_dlo > 0).sum())}.",
        numbers_before=f"original CSV 5% matched: cfar >= global {cu_o.n_ge_global}/17, CI>0 {cu_o.n_ci_above_0}; "
                       "1% matched (clamped) 17/17, CI>0 17/17",
        numbers_after=f"grouped 5% matched: {cu_g.n_ge_global}/17, CI>0 {cu_g.n_ci_above_0}; equal-spend 1% nominal: "
                      f"split interval>0 {int((eqg.d_tpr_uniform_q025 > 0).sum())}/17; originals-only 5%: "
                      + ", ".join(f"{r.signal} {ci(r.tpr_uniform_d, r.tpr_uniform_dlo, r.tpr_uniform_dhi)}"
                                  for _, r in oh[oh.signal.isin(["wb_dec_full", "wb_fibs_fu_full", "llm_gpt-4.1_none"])].iterrows()),
        verdict="weakened"))

    # ---- M5: AUROCs
    keys = ["llm_gpt-4.1_none", "wb_fibs_fu_full", "llm_gpt-4.1-mini_none", "wb_dec_full", "wb_sab_full", "wb_sab_max_full"]
    nd = int((A.d_sb_lo > 0).sum())
    rows.append(dict(
        issue_id="M5", track="r2_t2 (E5)",
        original_claim="E5 probe / monitor AUROCs on the 541-attack set (gpt-4.1 0.911, fibs_fu_full 0.905, ..., "
                       "sab_max_none 0.596)",
        corrected_claim=f"The AUROCs are dominated by the 508 refined rewrites with fabricated outputs. On the 33 "
                        f"originals AUROCs are much lower for most signals and the ranking changes (the sab probes "
                        f"lead, dec_full falls to near chance). Refined variants of the SAME base attacks score higher "
                        f"than their originals on {nd}/17 signals (interval > 0), so the gap is not base-attack mix; "
                        f"fabrication and rewrite artifacts cannot be separated with this data. Originals n = 33: "
                        f"intervals are wide.",
        numbers_before="; ".join(f"{s} {A.loc[s, 'auroc_all']:.3f}" for s in keys),
        numbers_after="originals (n=33): " + "; ".join(
            f"{s} {A.loc[s, 'auroc_originals']:.3f} [{A.loc[s, 'auroc_originals_lo']:.2f}, {A.loc[s, 'auroc_originals_hi']:.2f}]"
            for s in keys) + "; same-base refined - originals: " + "; ".join(
            f"{s} {ci(A.loc[s, 'd_samebase_minus_orig'], A.loc[s, 'd_sb_lo'], A.loc[s, 'd_sb_hi'])}" for s in keys),
        verdict="weakened"))

    rows.append(dict(
        issue_id="M5", track="r2_t2 (E5)",
        original_claim="E5 attack set: 541 attacks (33 originals + 508 T3 refined), split iid within context",
        corrected_claim="541 distinct trajectories from 148 base attacks; 0 exact-content duplicates inside the E5 set "
                        "(the 329/419 identical adaptive-vs-r0 copies share a traj_id and were already merged by E5's "
                        "loader). The leak was correlated variants of one base attack on both sides of the split; "
                        "the corrected design splits and bootstraps by base attack.",
        numbers_before="541 attacks, iid split",
        numbers_after="541 kept after dedupe (0 removed); 148 base attacks; per cluster 6-42 base attacks",
        verdict="holds"))

    rows.append(dict(
        issue_id="M5", track="r2_t2 (E5)",
        original_claim="Probe scores are far more context-dependent than LLM-monitor scores (tau, ICC, per-cluster FPR "
                       "range; honest runs only)",
        corrected_claim="Unaffected by C1 / M5: the heterogeneity statistics use honest runs only and no spend matching.",
        numbers_before="tau@5% dec_full 3.79, fibs_fu_full 2.70; LLM 0.00-0.46", numbers_after="unchanged",
        verdict="holds"))
    return rows


def t2_rows():
    rp = pd.read_csv(R / "audit" / "repro_t2.csv")
    a1 = pd.read_csv(R / "t2" / "allocation_summary_full_main_lasweep_mrt_small.csv")
    a5 = pd.read_csv(R / "t2" / "allocation_summary_full_main5.csv")
    PZ = pd.read_csv(R / "t2" / "poisoning_summary.csv")
    E2 = pd.read_csv(R / "r2_t2" / "e2_breakdown_summary.csv")
    rows = []

    def al(df, panel, mode, B, rule):
        return g(df[df.ncal == -1], panel=panel, mode=mode, B=B, rule=rule)
    st1, gl1 = g(rp, B=0.01, rule="stackelberg"), g(rp, B=0.01, rule="global")
    st5, gl5 = g(rp, B=0.05, rule="stackelberg"), g(rp, B=0.05, rule="global")
    m1s, m1g = al(a1, "akshn_setting", "matched", 0.01, "stackelberg"), al(a1, "akshn_setting", "matched", 0.01, "global")
    n1s = al(a1, "akshn_setting", "nominal", 0.01, "stackelberg")
    m5s = al(a5, "akshn_setting", "matched", 0.05, "stackelberg")
    rows.append(dict(
        issue_id="m2", track="t2",
        original_claim="Damage-equalizing Stackelberg thresholds are best against attack selection (7 settings: 0.79 vs "
                       "0.64 at 1%, 0.97 vs 0.89 at 5%)",
        corrected_claim="Holds against global with attacker information independent of the defender's fit set "
                        "(3-way split). At 1% the spend-matched paired interval crosses 0; at 5% it excludes 0.",
        numbers_before=f"nominal 1%: stack {n1s.sel_informed:.3f} (spend {100 * n1s.spend:.2f}%) vs global 0.64; 5%: "
                       f"0.97 vs 0.89",
        numbers_after=f"independent attacker info (audit repro): 1% {st1.sel_indep:.3f} vs global {gl1.sel_indep:.3f} "
                      f"(same-set {st1.sel_info:.3f}); 5% {st5.sel_indep:.3f} vs {gl5.sel_indep:.3f} (same-set "
                      f"{st5.sel_info:.3f}); spend-matched 1%: {m1s.sel_informed:.3f} vs {m1g.sel_informed:.3f}, paired "
                      f"[{m1s.sel_informed_dlo:+.2f}, {m1s.sel_informed_dhi:+.2f}], P(>0) {m1s.sel_informed_pgt:.2f}, "
                      f"matched_ok {m1s.matched_ok:.2f}; spend-matched 5%: {m5s.sel_informed:.3f}, paired "
                      f"[{m5s.sel_informed_dlo:+.2f}, {m5s.sel_informed_dhi:+.2f}]",
        verdict="holds"))
    rows.append(dict(
        issue_id="m2", track="t2",
        original_claim="Stackelberg 1% gain is robust (7 settings, spend-matched)",
        corrected_claim="At 1% the gain is not significant when spend-matched (interval crosses 0); caveat 1%, 5% is "
                        "robust.",
        numbers_before="0.79 vs 0.64 at 1%",
        numbers_after=f"matched 1% {m1s.sel_informed:.3f} vs {m1g.sel_informed:.3f}, paired [{m1s.sel_informed_dlo:+.2f}, "
                      f"{m1s.sel_informed_dhi:+.2f}]",
        verdict="weakened"))
    cs_n, cg_n = al(a1, "ca_setting_model", "nominal", 0.01, "stackelberg"), al(a1, "ca_setting_model", "nominal", 0.01, "global")
    cs_m, cg_m = al(a1, "ca_setting_model", "matched", 0.01, "stackelberg"), al(a1, "ca_setting_model", "matched", 0.01, "global")
    cs5, cg5 = al(a5, "ca_setting_model", "matched", 0.05, "stackelberg"), al(a5, "ca_setting_model", "matched", 0.05, "global")
    rows.append(dict(
        issue_id="m2", track="t2",
        original_claim="Stackelberg beats global against selection on ControlArena at 1%",
        corrected_claim="The nominal 1% gain comes from overspending (1.38% vs 0.97%); spend-matched there is no gain, and "
                        "34% of splits could not be matched (the T2 matcher clamps like r2lib, so the matched value is "
                        "partly extrapolated). At 5% matched the gain remains (P(>0) 0.96, interval touches 0).",
        numbers_before=f"nominal 1%: stack {cs_n.sel_informed:.3f} (spend {100 * cs_n.spend:.2f}%) vs global "
                       f"{cg_n.sel_informed:.3f} (spend {100 * cg_n.spend:.2f}%)",
        numbers_after=f"matched 1%: {cs_m.sel_informed:.3f} vs {cg_m.sel_informed:.3f}, paired [{cs_m.sel_informed_dlo:+.2f}, "
                      f"{cs_m.sel_informed_dhi:+.2f}], matched_ok {cs_m.matched_ok:.2f}; matched 5%: {cs5.sel_informed:.3f} vs "
                      f"{cg5.sel_informed:.3f}, paired [{cs5.sel_informed_dlo:+.2f}, {cs5.sel_informed_dhi:+.2f}]",
        verdict="dropped"))

    # m3
    os_ = PZ[(PZ.rule == "os_shift") & (PZ.poison == "attack_max")]
    gl = PZ[(PZ.rule == "global") & (PZ.poison == "attack_max")]
    panels = ["akshn_setting", "ca_setting_model", "la_env_local", "la_taskcat_local"]
    at10 = "; ".join(f"{p} {g(os_, panel=p, eps=0.1).tpr_t:.2f} (worst target {g(os_, panel=p, eps=0.1).tpr_t_worst:.2f})"
                     for p in panels)
    rng = "; ".join(f"{p} {os_[(os_.panel == p) & (os_.eps > 0) & (os_.eps <= 0.1)].tpr_t.min():.2f}-"
                    f"{os_[(os_.panel == p) & (os_.eps > 0) & (os_.eps <= 0.1)].tpr_t.max():.2f}" for p in panels)
    clean = "; ".join(f"{p} {g(os_, panel=p, eps=0.0).tpr_t:.3f} vs global {g(gl, panel=p, eps=0.0).tpr_t:.3f}" for p in panels)
    e2 = "; ".join(f"{p} os_loco worst eps 2%/5%/10% = {g(E2, panel=p, B=0.01, rule='os_loco').worst_eps2:.2f}/"
                   f"{g(E2, panel=p, B=0.01, rule='os_loco').worst_eps5:.2f}/{g(E2, panel=p, B=0.01, rule='os_loco').worst_eps10:.2f}"
                   for p in panels)
    rows.append(dict(
        issue_id="m3", track="t2",
        original_claim="OS-CFAR with a leave-one-context-out tail holds 0.77-0.86 under poisoning (B = 1%, up to "
                       "eps = 10%)",
        corrected_claim="The range is la_env_local's. Per panel, single-context poisoning at eps = 10% gives 0.62-0.81 "
                        "(mean over poisoned target contexts; the worst target context is far lower). OS-CFAR also costs "
                        "detection without poisoning on la_taskcat (0.78 vs global 0.91). Under spread poisoning "
                        "(round-2 E2: poison in all other contexts) the LOCO tail breaks at eps ~ B; the frozen-reference "
                        "tail is the robust variant.",
        numbers_before="0.77-0.86 (also 0.81-0.86 in EXPERIMENT_LOG)",
        numbers_after=f"eps=10%: {at10}. Range over eps 0.5-10%: {rng}. Unpoisoned: {clean}. E2 spread poisoning (1%): {e2}",
        verdict="weakened"))

    rows.append(dict(
        issue_id="m11", track="r3_t2",
        original_claim="akshn_adj rows in results/r3_t2/tables.md (watcher_strict / sev_tilt / tilt_mm at 0.98-0.99 "
                       "damage-weighted detection) shown without caveat",
        corrected_claim="These rows use aksh-n's outcome-adjudicated severity (label-leaking: severity AUROC 0.998), so "
                        "they are an upper bound no deployed rater can reach. Annotated copy with the caveat in each "
                        "affected section header: results/fixes/r3_t2/tables_annotated.md. Numbers unchanged; with the "
                        "blind rater (mb_* panels) severity AUROC is 0.53-0.54 and tiers do not beat global.",
        numbers_before="akshn_adj 1%: watcher_strict dmg_unif 0.99, sev_tilt 0.99, tilt_mm 0.98 (no caveat)",
        numbers_after="same numbers, flagged as label-leaking upper bound",
        verdict="weakened"))
    return rows


def main():
    (FX / "r2_t2").mkdir(parents=True, exist_ok=True)
    (FX / "t2").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(r2t2_rows(), columns=COLS).to_csv(FX / "r2_t2" / "corrections_r2_t2.csv", index=False)
    pd.DataFrame(t2_rows(), columns=COLS).to_csv(FX / "t2" / "corrections_t2.csv", index=False)
    for p in (FX / "r2_t2" / "corrections_r2_t2.csv", FX / "t2" / "corrections_t2.csv"):
        d = pd.read_csv(p)
        print(p.name, len(d))
        for _, r in d.iterrows():
            print(f"  [{r.issue_id} {r.verdict}] {r.numbers_after[:300]}")


if __name__ == "__main__":
    main()
