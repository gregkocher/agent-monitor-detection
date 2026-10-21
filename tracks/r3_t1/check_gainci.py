"""Check r3lib.paired_gain_full against the auditor's reproduction (results/audit/repro_t1_ps.csv): round-2
persistent-state gpt-4.1-mini / gpt-4o current_only gradual, top-3 sum vs max."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from ps_sets import r2_ps_sets  # noqa: E402
from r2lib import paired_gain, run_matched, suite  # noqa: E402
from r3lib import paired_gain_full  # noqa: E402

for ss in r2_ps_sets():
    if not ss.name.endswith("current_only:gradual") or "gemini" in ss.name or "qwen" in ss.name:
        continue
    d = {k: v for k, v in suite().items() if k in ("max", "top3sum")}
    _, raw = run_matched(ss, detectors=d, alphas=(0.05, 0.01), n_splits=20, n_boot=10, return_raw=True)
    for al in (0.05, 0.01):
        old = paired_gain(raw, al, a="top3sum", b="max")
        new = paired_gain_full(raw, al, "top3sum")
        print(ss.name, al, "old", [round(x, 3) for x in old], "full", {k: round(v, 3) for k, v in new.items()})
