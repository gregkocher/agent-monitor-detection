"""Score refined trajectories with the deployed monitor in `none` (innovation) mode.

Full-mode scores are saved in-loop by refine.py; this adds the `none`-mode per-step scores for the
same monitor_id (openai/gpt-4.1-mini|ctrl-basic-v1|none) for every refined arm (final + round0), so
evaluate.py can run the innovation-monitor analysis. Resumable via each source's score_cache.sqlite.

    uv run python -m tracks.t3_aware_attacker.score_refined [--arms max,cusum,multichart]
        [--variants final,r0] [--concurrency 32] [--yes]
"""
from __future__ import annotations

import argparse

from amd.scoring import run

MODEL = "openai/gpt-4.1-mini"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="max,cusum,multichart")
    ap.add_argument("--variants", default="final,r0")
    ap.add_argument("--modes", default="none")   # full already saved in-loop
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    rc = 0
    for arm in a.arms.split(","):
        for var in a.variants.split(","):
            src = f"t3_refined/{arm}" + ("" if var == "final" else "_r0")
            for mode in a.modes.split(","):
                argv2 = ["--source", src, "--model", MODEL, "--history", mode, "--track", "t3",
                         "--max-steps", "60", "--concurrency", str(a.concurrency)]
                if a.yes:
                    argv2.append("--yes")
                print(f"### scoring {src} [{mode}]", flush=True)
                rc = run.main(argv2) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
