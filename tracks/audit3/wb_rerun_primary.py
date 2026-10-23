"""Audit pass 3 (r4_wb): rerun the committed tracks/r4_wb/analyze_primary.py unchanged, with its output directory
redirected to results/audit3/wb_rerun_primary/ (so results/r4_wb is not touched).

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.wb_rerun_primary
"""
from amd.common.schema import REPO
from tracks.r4_wb import analyze_primary as ap

ap.OUT = REPO / "results" / "audit3" / "wb_rerun_primary"

if __name__ == "__main__":
    ap.main()
