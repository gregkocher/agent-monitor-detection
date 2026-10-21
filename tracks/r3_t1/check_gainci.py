"""Check r3lib.gains_full (amd.evaluation.paired) against the corrected round-2 numbers in
results/fixes/corrections.csv: persistent-state gpt-4.1-mini / gpt-4o current_only gradual, top-3 sum vs max."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from ps_sets import r2_ps_sets  # noqa: E402
from r2lib import paired_gain, run_matched, suite  # noqa: E402
from r3lib import gains_full  # noqa: E402

for ss in r2_ps_sets():
    if not ss.name.endswith("current_only:gradual") or "gemini" in ss.name or "qwen" in ss.name:
        continue
    d = {k: v for k, v in suite().items() if k in ("max", "top3sum")}
    _, raw = run_matched(ss, detectors=d, alphas=(0.05, 0.01), n_splits=20, n_boot=10, return_raw=True)
    for al in (0.05, 0.01):
        old = paired_gain(raw, al, a="top3sum", b="max")
        new = gains_full(ss, raw, (al,), ["top3sum"]).iloc[0]
        print(ss.name, al, "old", [round(x, 3) for x in old], "paired", round(new.gain_vs_max, 3),
              [round(new.lo, 3), round(new.hi, 3)], "p<=0", round(new.p_le0, 3))
