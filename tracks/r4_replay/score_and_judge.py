"""Score the round-4 structured rewrites with the gpt-4.1 history-free monitor and run the LLM
validity judge -- the same monitor and judge used in rounds 2/3 -- so undetected-success can be
recomputed with EXECUTION validity (step 5). Reuses refine_r2.score_traj and the round-2 judge.

    uv run python -m tracks.r4_replay.score_and_judge --arms rewrite_control,pace_max

Writes, per arm dir data/processed/t3_refined/r4_<arm>/:
  * scores_openai_gpt-4.1_none.jsonl   (per-step monitor scores, none mode, logprob-expected)
  * trajectories.jsonl updated in place with meta.valid / meta.validity (judge all_preserved)
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from amd.common.openrouter import OpenRouter, spend_report
from amd.common.schema import PROCESSED, Trajectory, load_trajectories, write_jsonl
from tracks.r2_t3.refine_r2 import score_traj
from tracks.t3_aware_attacker.refine import _JUDGE_SYS, parse_json, render_original

REFINED = PROCESSED / "t3_refined"
MONITOR_MODEL = "openai/gpt-4.1"
JUDGE_MODEL = "openai/gpt-4.1-mini"


def _load_trajs(path: Path) -> list[Trajectory]:
    out = []
    for l in open(path):
        t = json.loads(l)
        out.append(Trajectory(**{k: t[k] for k in ("traj_id", "source", "label", "context", "steps",
                                                    "attack_step", "harm_step", "side_task_success", "meta")}))
    return out


def _checklists() -> dict:
    cl = {}
    for l in open(REFINED / "checklists.jsonl"):
        d = json.loads(l)
        if d["traj_id"].startswith("monitoringbench:"):
            cl[d["traj_id"].split(":")[-1]] = d["effects"]
    return cl


async def judge_one(orc, traj, effects):
    jmsgs = [{"role": "system", "content": _JUDGE_SYS},
             {"role": "user", "content": "CHECKLIST:\n" +
              "\n".join(f"  {e['id']}. {e['effect']}" for e in effects) +
              "\n\nRESTRUCTURED SEQUENCE:\n" + render_original(traj)}]
    try:
        jres = await orc.chat(JUDGE_MODEL, jmsgs, max_tokens=1500, temperature=0.0)
        vjs = parse_json(jres.get("text") or "") or {}
        if not isinstance(vjs, dict):
            vjs = {"error": "judge non-object"}
    except Exception as e:
        vjs = {"error": str(e)[:150]}
    return vjs


async def amain(a):
    cl = _checklists()
    arms = a.arms.split(",")
    async with OpenRouter(track="r4rep", concurrency=a.concurrency, tag="r4_scorejudge") as orc:
        for arm in arms:
            d = REFINED / f"r4_{arm}"
            trajs = _load_trajs(d / "trajectories.jsonl")
            # monitor scoring (none) + judge, concurrently per trajectory
            async def work(t):
                base_u = t.traj_id.split(":")[-1]
                stream = await score_traj(orc, t, "none", MONITOR_MODEL)
                vjs = await judge_one(orc, t, cl[base_u])
                t.meta["validity"] = vjs
                t.meta["valid"] = bool(vjs.get("all_preserved")) if "all_preserved" in vjs else None
                return t, stream
            res = await asyncio.gather(*[work(t) for t in trajs])
            streams = [s for _, s in res]
            write_jsonl(d / "scores_openai_gpt-4.1_none.jsonl", streams)
            write_jsonl(d / "trajectories.jsonl", [t for t, _ in res])
            valid = sum(1 for t, _ in res if t.meta.get("valid"))
            lits = sum(1 for t, _ in res if (t.meta.get("literal_preservation") or 0) >= 0.999)
            print(f"arm={arm}: scored+judged {len(res)}; judge-valid {valid}, literal-full {lits}", flush=True)
    print(spend_report())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="rewrite_control,pace_max")
    ap.add_argument("--concurrency", type=int, default=8)
    asyncio.run(amain(ap.parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
