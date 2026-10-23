"""Threshold-convention rerun of tracks/audit3/rep_r4_independent.py (the audit's independent r4_replay analysis:
source of "-0.214 [-0.478, +0.054]", "all 33 pairs -0.242", "no firewall -0.375", the decomposition and Holm).

That script uses its own plug-in copy (tracks/audit2/a2lib.rand_threshold / alarm), which the convention flag
does not reach. --convention conformal swaps both names in the module namespace for the conformal randomized
rule (rep_thrfix_lib.conformal_a2lib); --convention plugin runs it unchanged. Same seeds and B = 4000.

Output dir redirected to results/fixes2/rep_r4_indep_<conv>_thrfix/. Replay verdicts are still read from
results/r4_replay/<arm>/. The multiplicity section (Holm over the track's 24 exec cells) reads the track table
paired_contrasts.json: it is pointed at the matching-convention rerun of tracks/r4_replay/analyze.py
(results/fixes2/rep_r4_analyze_<conv>_thrfix/, run rep_r4_analyze_thrfix first).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_r4_independent_thrfix --convention plugin
    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_r4_independent_thrfix --convention conformal
"""
from __future__ import annotations

import argparse
import json

import tracks.audit3.rep_r4_independent as ind
from tracks.fixes2.rep_thrfix_lib import OUT, conformal_a2lib


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--convention", choices=("plugin", "conformal"), required=True)
    a = ap.parse_args(argv)
    out = OUT / f"rep_r4_indep_{a.convention}_thrfix"
    out.mkdir(parents=True, exist_ok=True)
    track_tab = OUT / f"rep_r4_analyze_{a.convention}_thrfix"
    assert (track_tab / "paired_contrasts.json").exists(), "run rep_r4_analyze_thrfix first"
    rr_replay = ind.RR

    def load_exec(arm):                       # replay verdicts from the committed replay dir
        o = {}
        for f in (rr_replay / arm).glob("*.json"):
            r = json.loads(f.read_text())
            o[r.get("uuid") or f.stem] = r
        return o

    ind.load_exec = load_exec
    ind.RR = track_tab                        # only used afterwards for paired_contrasts.json (multiplicity)
    ind.OUT = out
    with conformal_a2lib(ind, enabled=(a.convention == "conformal")):
        ind.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
