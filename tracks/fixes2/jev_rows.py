"""Assemble results/fixes2/rows_jev.csv (old = plug-in, new = conformal randomized threshold) from
  results/fixes2/jev_primary_{plugin,conformal}_thrfix/{hypotheses,cascade_cells}.csv + data/fixes2/jev_boot_*/ pickles
  results/fixes2/jev_audit_{plugin,conformal}_thrfix.csv
and check that the plug-in reruns reproduce the committed tables (results/r5_jev, results/audit3).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.jev_rows
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from amd.common.schema import DATA, REPO

from tracks.r5_jev.analyze_primary import MIN_CAL

F2 = REPO / "results" / "fixes2"
CONV = ("plugin", "conformal")


def ci(lo, hi):
    return f"[{lo:+.3f}, {hi:+.3f}]"


def fp(x):
    return f"{100 * x:.2f}%"


def load(conv):
    d = F2 / f"jev_primary_{conv}_thrfix"
    with open(DATA / "fixes2" / f"jev_boot_{conv}" / "primary_S50_B1000.pkl", "rb") as f:
        boot = pickle.load(f)
    return dict(hyp=pd.read_csv(d / "hypotheses.csv").set_index("hypothesis"),
                cells=pd.read_csv(d / "cascade_cells.csv"), boot=boot,
                audit=pd.read_csv(F2 / f"jev_audit_{conv}_thrfix.csv").set_index("claim"))


def nc(R, a):
    return float(np.mean(R["llm_only"][a]["n_cal"]))


def rfpr(Rs, key, a):
    keep = [R for R in Rs if nc(R, a) >= MIN_CAL[a]]
    return float(np.mean([np.mean(R[key][a]["fpr"]) for R in keep]))


HYP = {"H1-MB": ("mb", ("jev", 0.2), "llm_only"), "H1-AK": ("ak", ("jev", 0.2), "llm_only"),
       "H2-MB": ("mb", ("jev", 0.1), ("nano", 0.1)), "H2-AK": ("nano", ("jev", 0.1), ("nano", 0.1)),
       "H3-MB": ("mb", ("jev", 0.1), ("probe", 0.1))}


def main():
    D = {c: load(c) for c in CONV}
    # ---- reproduction checks (plug-in rerun == committed)
    com = pd.read_csv(REPO / "results/r5_jev/hypotheses.csv").set_index("hypothesis")
    h0 = D["plugin"]["hyp"]
    rep_h = float(np.max(np.abs(com[["est", "lo", "hi", "p_ni", "p_ni_holm"]].values -
                                h0.loc[com.index, ["est", "lo", "hi", "p_ni", "p_ni_holm"]].values)))
    cc = pd.read_csv(REPO / "results/r5_jev/cascade_cells.csv")
    num = ["tpr", "tpr_lo", "tpr_hi", "d_llm", "d_lo", "d_hi", "fpr"]
    rep_c = float(np.nanmax(np.abs(cc[num].values - D["plugin"]["cells"][num].values)))
    print(f"plug-in rerun vs committed: hypotheses max |diff| {rep_h:.2e}; cascade_cells max |diff| {rep_c:.2e}")
    a3 = pd.read_csv(REPO / "results/audit3/jev_indep_hyp.csv")
    a3 = a3[a3.variant == "orig_grouping"].set_index("hypothesis")
    a3t = pd.read_csv(REPO / "results/audit3/jev_h1ak_task.csv")
    a3t = a3t[a3t.variant == "orig_grouping"].set_index("hypothesis")
    a3e = pd.read_csv(REPO / "results/audit3/jev_equalfpr.csv")
    au = D["plugin"]["audit"]
    pairs = [(a3.loc["H1-AK leave out akshn_shade"], au.loc["H1-AK leave out akshn_shade"]),
             (a3.loc["H1-AK at 5% FPR, 7 settings, e=0.2"], au.loc["H1-AK at 5% FPR, 7 settings, e=0.2"]),
             (a3.loc["H1-AK"], au.loc["H1-AK pooled (indep, S20 B400)"]),
             (a3t.loc["H1-AK equal-weight settings"], au.loc["H1-AK equal-weight settings (S20 B2000)"]),
             (a3t.loc["H1-AK"], au.loc["H1-AK pooled (h1ak_task, S20 B2000)"])]
    for _, r in a3e[a3e.alpha_nominal == 0.05].iterrows():
        if r.config == "('plain', 'jev')":
            continue
        x = au.loc[f"MB 5% {r.config} vs mini, {r.kind}"]
        pairs.append((pd.Series(dict(est=r.d, lo=r.d_lo, hi=r.d_hi, p_ni=np.nan)), x))
    rep_a = max(float(np.nanmax(np.abs([o[k] - n[k] for k in ("est", "lo", "hi", "p_ni")]))) for o, n in pairs)
    print(f"plug-in audit rerun vs committed audit3 tables: max |diff| {rep_a:.2e}")

    rows = []
    # ---- preregistered H1-H3
    for h, (pan, k1, k2) in HYP.items():
        o, n = D["plugin"]["hyp"].loc[h], D["conformal"]["hyp"].loc[h]
        fr = {}
        for c in CONV:
            b = D[c]["boot"]
            Rs = {"mb": [b["mb"]], "ak": b["ak"], "nano": b["nano"]}[pan]
            fr[c] = f"{fp(rfpr(Rs, k1, 0.01))} / {fp(rfpr(Rs, k2, 0.01))}"
        vc = "yes" if bool(o.supported) != bool(n.supported) else "no"
        rows.append(dict(claim=f"{h} (1% FPR, NI margin 0.03, Holm over 5)", old_estimate=f"{o.est:+.3f}",
                         old_ci=ci(o.lo, o.hi), new_estimate=f"{n.est:+.3f}", new_ci=ci(n.lo, n.hi),
                         old_realized_fpr=fr["plugin"], new_realized_fpr=fr["conformal"], verdict_change=vc,
                         note=(f"TPR {o.tpr1:.3f} vs {o.tpr2:.3f} -> {n.tpr1:.3f} vs {n.tpr2:.3f}; NI p {o.p_ni:.4f} -> "
                               f"{n.p_ni:.4f}; Holm p {o.p_ni_holm:.4f} -> {n.p_ni_holm:.4f}; supported "
                               f"{bool(o.supported)} -> {bool(n.supported)} (committed pipeline, S=50, B=1000)")))

    # ---- audit variants of H1-AK (jev_indep / jev_h1ak_task implementation)
    for name, key, src in (("H1-AK leave SHADE out (audit3, 1%)", "H1-AK leave out akshn_shade", "jev_indep S=20 B=400"),
                           ("H1-AK settings weighted equally (audit3, 1%)", "H1-AK equal-weight settings (S20 B2000)",
                            "jev_h1ak_task S=20 B=2000; weights per setting are equal averaging of per-setting TPRs, "
                            "thresholds use integer bootstrap multiplicities (trajectory units), no fractional masses"),
                           ("H1-AK at 5% FPR, 7 settings, e=20% (audit3 AK 5% cascade cell)",
                            "H1-AK at 5% FPR, 7 settings, e=0.2", "jev_indep S=20 B=400")):
        o, n = D["plugin"]["audit"].loc[key], D["conformal"]["audit"].loc[key]
        p_note = f"NI p {o.p_ni:.4f} -> {n.p_ni:.4f}; P(d>=0) {o.p_inf:.4f} -> {n.p_inf:.4f}"
        if "5%" in name:
            sig_o, sig_n = o.hi < 0, n.hi < 0
            vc = "yes" if sig_o != sig_n else "no"
            p_note += f"; CI below 0 {sig_o} -> {sig_n}"
        else:
            vc = "yes" if (o.p_ni < 0.025) != (n.p_ni < 0.025) else "no"
            p_note += f"; NI at one-sided 0.025 (unadjusted) {o.p_ni < 0.025} -> {n.p_ni < 0.025}"
        rows.append(dict(claim=name, old_estimate=f"{o.est:+.3f}", old_ci=ci(o.lo, o.hi), new_estimate=f"{n.est:+.3f}",
                         new_ci=ci(n.lo, n.hi), old_realized_fpr=f"{fp(o.fpr1)} / {fp(o.fpr2)}",
                         new_realized_fpr=f"{fp(n.fpr1)} / {fp(n.fpr2)}", verdict_change=vc,
                         note=f"{p_note} ({src}); FPR = JEV cascade / Gemini only, mean over settings"))

    # ---- AK 5% in the committed pipeline (akshn_pooled, 7 settings)
    def cell(conv, panel, first, e, a):
        c = D[conv]["cells"]
        m = (c.panel == panel) & (c["first"] == first) & (c.mapping == "floor") & (c.alpha == a)
        m &= c.e.isna() if e is None else np.isclose(c.e.fillna(-1), e)
        assert m.sum() == 1, (panel, first, e, a)
        return c[m].iloc[0]

    o, n = cell("plugin", "akshn_pooled", "jev", 0.2, 0.05), cell("conformal", "akshn_pooled", "jev", 0.2, 0.05)
    ob, nb = cell("plugin", "akshn_pooled", "llm_only", None, 0.05), cell("conformal", "akshn_pooled", "llm_only", None, 0.05)
    rows.append(dict(claim="AK 5% FPR, JEV cascade e=20% - Gemini only, 7 settings pooled (committed pipeline cell)",
                     old_estimate=f"{o.d_llm:+.3f}", old_ci=ci(o.d_lo, o.d_hi), new_estimate=f"{n.d_llm:+.3f}",
                     new_ci=ci(n.d_lo, n.d_hi), old_realized_fpr=f"{fp(o.fpr)} / {fp(ob.fpr)}",
                     new_realized_fpr=f"{fp(n.fpr)} / {fp(nb.fpr)}",
                     verdict_change="yes" if (o.d_hi < 0) != (n.d_hi < 0) else "no",
                     note=f"NI p {o.p_ni_vs_llm:.4f} -> {n.p_ni_vs_llm:.4f}; cascade_cells.csv S=50 B=1000"))

    # ---- MB 5% secondary cells: committed pipeline (nominal) and audit3 equal-realized-FPR
    for first, e in (("jev", 0.05), ("jev", 0.10), ("probe", 0.05)):
        o, n = cell("plugin", "mb", first, e, 0.05), cell("conformal", "mb", first, e, 0.05)
        ob, nb = cell("plugin", "mb", "llm_only", None, 0.05), cell("conformal", "mb", "llm_only", None, 0.05)
        rows.append(dict(claim=f"MB 5% FPR: {first} cascade e={int(e * 100)}% - mini only (committed cell, nominal)",
                         old_estimate=f"{o.d_llm:+.3f}", old_ci=ci(o.d_lo, o.d_hi), new_estimate=f"{n.d_llm:+.3f}",
                         new_ci=ci(n.d_lo, n.d_hi), old_realized_fpr=f"{fp(o.fpr)} / {fp(ob.fpr)}",
                         new_realized_fpr=f"{fp(n.fpr)} / {fp(nb.fpr)}",
                         verdict_change="yes" if (o.d_lo > 0) != (n.d_lo > 0) else "no",
                         note=(f"TPR {o.tpr:.3f} vs {ob.tpr:.3f} -> {n.tpr:.3f} vs {nb.tpr:.3f}; CI above 0 "
                               f"{o.d_lo > 0} -> {n.d_lo > 0}; cascade_cells.csv S=50 B=1000")))
        cfg = str(("casc", first, e))
        o = D["plugin"]["audit"].loc[f"MB 5% {cfg} vs mini, equal_realized_fpr"]
        n = D["conformal"]["audit"].loc[f"MB 5% {cfg} vs mini, equal_realized_fpr"]
        nn = D["conformal"]["audit"].loc[f"MB 5% {cfg} vs mini, nominal"]
        rows.append(dict(claim=f"MB 5% FPR: {first} cascade e={int(e * 100)}% - mini only at equal realized FPR (audit3)",
                         old_estimate=f"{o.est:+.3f}", old_ci=ci(o.lo, o.hi), new_estimate=f"{n.est:+.3f}",
                         new_ci=ci(n.lo, n.hi), old_realized_fpr=f"{fp(o.fpr1)} / {fp(o.fpr2)}",
                         new_realized_fpr=f"{fp(n.fpr1)} / {fp(n.fpr2)}",
                         verdict_change="yes" if (o.lo > 0) != (n.lo > 0) else "no",
                         note=(f"cascade nominal alpha used {o.alpha_used:.3f} -> {n.alpha_used:.3f} (chosen so its "
                               f"split-mean test FPR matches mini@5%); new convention at nominal 5% for both: "
                               f"{nn.est:+.3f} {ci(nn.lo, nn.hi)} at {fp(nn.fpr1)} / {fp(nn.fpr2)}; jev_equalfpr S=20 B=300")))
    out = pd.DataFrame(rows)
    out.to_csv(F2 / "rows_jev.csv", index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_colwidth", 60)
    print(out.drop(columns="note").to_string(index=False))


if __name__ == "__main__":
    main()
