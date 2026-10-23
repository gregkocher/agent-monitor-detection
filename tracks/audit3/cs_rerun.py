"""Audit pass 3 (track r4_cs): re-run the committed r4_cs analysis scripts unchanged, writing to audit paths.

    unset VIRTUAL_ENV; uv run python tracks/audit3/cs_rerun.py <ps_multi|mechanism|mole|arl|arl_reanalyse> [script args]

The committed modules are imported as-is; only their output directories are redirected:
  tables / CSVs -> results/audit3/cs_rerun/ ; per-split raw pickles -> data/raw/audit3_cs/ (gitignored).
mechanism.py reads ps_raws.pkl, ps_gains.csv and mole_*.csv from the redirected directories, so run
ps_multi and mole first. No API calls (scores are read from data/processed).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
R4 = HERE.parent / "r4_cs"
sys.path.insert(0, str(R4))

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "audit3" / "cs_rerun"
RAW = REPO / "data" / "raw" / "audit3_cs"


def _load(name):
    """Import tracks/r4_cs/<name>.py by path (r4lib puts tracks/r2_t1 and t1_matched_budget first on sys.path,
    where modules with the same names exist, e.g. t1_matched_budget/mechanism.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"r4cs_{name}", R4 / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    which = sys.argv[1]
    sys.argv = [which] + sys.argv[2:]
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    import r4lib
    r4lib.OUT, r4lib.RAW = OUT, RAW
    if which == "ps_multi":
        m = _load("ps_multi")
        m.OUT, m.RAW = OUT, RAW
        m.main()
    elif which == "mechanism":
        m = _load("mechanism")
        m.OUT, m.RAW = OUT, RAW
        m.main()
    elif which == "mole":
        m = _load("mole_r4_analysis")
        m.OUT = OUT
        m.main()
    elif which == "arl":
        import ps_arl as m
        m.OUT = OUT
        m.main()
    elif which == "arl_reanalyse":   # tables from the COMMITTED replicates, written to the audit dir
        import pandas as pd
        import ps_arl as m
        R = pd.read_csv(REPO / "results" / "r4_cs" / "arl_replicates.csv.gz")
        m.OUT = OUT / "arl_from_committed"
        m.OUT.mkdir(parents=True, exist_ok=True)
        mons = m.ps_monitor_streams()
        m.analyse(R, [x for x in mons if x in set(R.monitor)], mons)
    else:
        raise SystemExit(f"unknown target {which}")


if __name__ == "__main__":
    main()
