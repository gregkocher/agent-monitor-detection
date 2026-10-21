"""Analysis helpers for the white-box (trusted reader) pilot.

Reader feature files (pulled from the pod) live in data/processed/whitebox/scores/<src>_<mode>.jsonl:
one record per trajectory, {"traj_id", "mode", "n_steps", "feats": {name: [per-step values]}}.
`derived()` turns raw per-step features into the named streams analysed in the write-up.

Stream definitions (all per agent step; the step's tokens = its rendered <action>...</action> block):
  sab        mean over the 6 FIBS layers of the synthetic-sabotage probe logit, mean-pooled over tokens
  sab_max    same, max-pooled over tokens
  dec        Apollo Instructed-Pairs deception probe, layer-mean of logits, mean-pooled
  fibs_tok   FIBS released linear probe applied directly to step tokens, layer-mean logit, mean-pooled
  fibs_fu    FIBS linear probe at the follow-up answer: layer-mean logit(No.) - layer-mean logit(Yes.)
  fibs_fu_ax FIBS axial probe: logit(No.) - logit(Yes.)
  jl_lm      J-lens watch-list log-mass, token mean, averaged over layers 27/35/43
  jl_lm_max  J-lens watch-list log-mass, token max, averaged over layers
  jl_hits    watch tokens in the J-lens top-25 per token, mean over tokens and layers
  sup        cross-fitted in-distribution supervised probe (per-step mean activations, pod-side)
"""
from __future__ import annotations

import json

import numpy as np

from amd.common.schema import PROCESSED, read_jsonl

WB = PROCESSED / "whitebox"
LAYERS = [19, 27, 35, 43, 51, 58]
JL = [27, 35, 43]
PRIMARY = ["sab", "sab_max", "dec", "fibs_tok", "fibs_fu", "fibs_fu_ax", "jl_lm", "jl_lm_max", "jl_hits", "sup"]


def _lm(F, key, layers):
    return np.mean([np.asarray(F[key.format(l=l)], float) for l in layers], axis=0)


def derived(F: dict) -> dict:
    out = {}
    if "sab_L19_mean" in F:
        out["sab"] = _lm(F, "sab_L{l}_mean", LAYERS)
        out["sab_max"] = _lm(F, "sab_L{l}_max", LAYERS)
        out["dec"] = _lm(F, "dec_L{l}_mean", LAYERS)
        for l in LAYERS:
            out[f"sab_L{l}"] = np.asarray(F[f"sab_L{l}_mean"], float)
            out[f"dec_L{l}"] = np.asarray(F[f"dec_L{l}_mean"], float)
    out["fibs_tok"] = _lm(F, "fibs_L{l}_mean", LAYERS)
    out["fibs_tok_max"] = _lm(F, "fibs_L{l}_max", LAYERS)
    if "fu_linL19_no" in F:
        out["fibs_fu"] = _lm(F, "fu_linL{l}_no", LAYERS) - _lm(F, "fu_linL{l}_yes", LAYERS)
        out["fibs_fu_no"] = _lm(F, "fu_linL{l}_no", LAYERS)
        out["fibs_fu_ax"] = np.asarray(F["fu_ax_no"], float) - np.asarray(F["fu_ax_yes"], float)
    out["jl_lm"] = _lm(F, "jl_L{l}_lm_mean", JL)
    out["jl_lm_max"] = _lm(F, "jl_L{l}_lm_max", JL)
    nt = np.maximum(np.asarray(F["ntok"], float), 1)
    out["jl_hits"] = _lm(F, "jl_L{l}_hit_sum", JL) / nt
    for l in JL:
        out[f"jl_L{l}"] = np.asarray(F[f"jl_L{l}_lm_mean"], float)
    return out


def load_reader(src: str, mode: str, sup: bool = True) -> dict:
    """traj_id -> {stream name: per-step array}."""
    out = {}
    for p in sorted((WB / "scores").glob(f"{src}_{mode}*.jsonl")):
        if "_sup" in p.name:
            continue
        for d in read_jsonl(p):
            if d["n_steps"] == 0:
                continue
            out[d["traj_id"]] = derived(d["feats"])
    sp = WB / "scores" / f"{src}_{mode}_sup.jsonl"
    if sup and sp.exists():
        for d in read_jsonl(sp):
            if d["traj_id"] in out:
                for k, v in d["streams"].items():
                    out[d["traj_id"]][k] = np.asarray(v, float)
    return out


def load_inputs_meta(src: str) -> dict:
    return {d["traj_id"]: {"label": d["label"], "n_steps": d["n_steps"], **d["meta"]}
            for d in read_jsonl(WB / "inputs" / f"{src}.jsonl")}


def jdump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)
