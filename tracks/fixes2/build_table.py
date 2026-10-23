"""Assemble results/fixes2/headline_threshold_rerun.csv from the per-track rows (rows_<prefix>.csv).

Every row compares one headline claim under the historical plug-in randomized threshold (old) and the
conformal randomized threshold (new, amd.evaluation.calibration.conformal_randomized_threshold), computed with
the track's own analysis code and only the threshold convention switched (scripts tracks/fixes2/<prefix>_*.py).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.build_table
"""
import pandas as pd

TRACKS = [("ctx", "r4_ctx / Idea 2"), ("cs", "r4_cs / Idea 1"), ("wb", "r4_wb / white-box"),
          ("jev", "r5_jev"), ("rep", "r4_replay / Idea 3")]


def fmt(est, ci):
    est, ci = str(est).strip(), str(ci).strip()
    if est in ("", "nan"):
        return ""
    return est if ci in ("", "nan") else f"{est} {ci}"


rows = []
for prefix, track in TRACKS:
    d = pd.read_csv(f"results/fixes2/rows_{prefix}.csv", dtype=str, keep_default_na=False)
    for _, r in d.iterrows():
        rows.append(dict(track=track, claim=r.claim,
                         old_estimate_ci=fmt(r.old_estimate, r.old_ci),
                         new_estimate_ci=fmt(r.new_estimate, r.new_ci),
                         old_realized_fpr=r.old_realized_fpr, new_realized_fpr=r.new_realized_fpr,
                         verdict_change=r.verdict_change.strip().lower(), note=r.note))
out = pd.DataFrame(rows)
out.to_csv("results/fixes2/headline_threshold_rerun.csv", index=False)
print(out[["track", "claim", "old_estimate_ci", "new_estimate_ci", "verdict_change"]].to_string())
print(f"\n{len(out)} rows; verdict changes: {(out.verdict_change == 'yes').sum()}")
