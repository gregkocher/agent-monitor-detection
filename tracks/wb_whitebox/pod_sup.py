"""Pod-side offline steps on the saved per-step mean activations (never copied off the pod).

  sup     cross-fitted in-distribution supervised probe ("sup"): logistic regression on per-step mean
          activations (layers 27/35/43 concatenated, standardized), 5 folds grouped by main task over
          honest + attack trajectories of one source/mode. Positives: attack steps from the onset
          (heuristic first_attack_step, else attack_step) through the execution step; negatives: all
          honest steps; other attack steps are not used for training. Every step is scored by the fold
          model that did not see its trajectory's task. Output out/<src>_<mode>_sup.jsonl.
          With --transfer-from mb: fit on all of MonitoringBench (same mode) and score another source.
  decode  J-lens decoding of probe directions: for each linear probe w at layer l, the top / bottom
          tokens of W_U diag(g) J_l w (final-norm gain g; the RMS scale is dropped for a direction).

    python pod_sup.py sup --src mb --mode full
    python pod_sup.py decode
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import torch

WORK = "/root/wb"
HF = os.environ.get("HF_HOME", "/root/hf")
ALL_LAYERS = [19, 27, 35, 43, 51, 58]
SUP_LAYERS = [27, 35, 43]


def load_acts(src, mode, ids):
    X, idx = [], []
    for i, t in enumerate(ids):
        p = f"{WORK}/acts/{src}_{mode}/{t.replace(':', '__').replace('/', '_')}.npy"
        a = np.load(p)                                          # [n_steps, 6, d] fp16
        X.append(a[:, [ALL_LAYERS.index(l) for l in SUP_LAYERS]].reshape(len(a), -1))
        idx.append(np.full(len(a), i))
    return np.concatenate(X).astype(np.float32), np.concatenate(idx)


def fit_lr(X, y, w, epochs=300, l2=1e-3):
    dev = "cuda"
    X = torch.tensor(X, device=dev)
    y = torch.tensor(y, device=dev, dtype=torch.float32)
    w = torch.tensor(w, device=dev, dtype=torch.float32)
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    beta = torch.zeros(Z.shape[1], device=dev, requires_grad=True)
    b0 = torch.zeros(1, device=dev, requires_grad=True)
    opt = torch.optim.LBFGS([beta, b0], lr=1, max_iter=epochs, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        z = Z @ beta + b0
        loss = (w * torch.nn.functional.binary_cross_entropy_with_logits(z, y, reduction="none")).sum() / w.sum() \
            + l2 * (beta ** 2).sum()
        loss.backward()
        return loss
    opt.step(closure)
    return (beta / sd).detach(), (b0 - (beta * mu / sd).sum()).detach()


def labels(recs):
    ys = []
    for r in recs:
        n = r["n_steps"]
        y = np.full(n, -1.0) if r["label"] == "attack" else np.zeros(n)
        if r["label"] == "attack":
            m = r["meta"]
            on = m.get("first_attack_step")
            on = m.get("attack_step") if on is None else on
            ex = m.get("attack_step")
            if on is not None and on < n:
                hi = ex if ex is not None and ex < n else n - 1
                y[on:max(hi, on) + 1] = 1.0
        ys.append(y)
    return ys


def sup(src, mode, transfer_from=None):
    recs = [json.loads(l) for l in open(f"{WORK}/inputs/{src}.jsonl")]
    recs = [r for r in recs if r["n_steps"] > 0 and os.path.exists(
        f"{WORK}/acts/{src}_{mode}/{r['traj_id'].replace(':', '__').replace('/', '_')}.npy")]
    X, ti = load_acts(src, mode, [r["traj_id"] for r in recs])
    pred = np.zeros(len(X), np.float32)
    if transfer_from:
        tr = [json.loads(l) for l in open(f"{WORK}/inputs/{transfer_from}.jsonl")]
        tr = [r for r in tr if r["n_steps"] > 0]
        Xt, _ = load_acts(transfer_from, mode, [r["traj_id"] for r in tr])
        yt = np.concatenate(labels(tr))
        keep = yt >= 0
        wpos = (yt[keep] == 0).sum() / max((yt[keep] == 1).sum(), 1)
        beta, b0 = fit_lr(Xt[keep], yt[keep], np.where(yt[keep] == 1, wpos, 1.0))
        pred = (torch.tensor(X, device="cuda") @ beta + b0).cpu().numpy()
        tag = f"sup_from_{transfer_from}"
    else:
        y = np.concatenate(labels(recs))
        groups = np.array([str(r["meta"].get("task_id")) for r in recs])[ti]
        ug = np.unique(groups)
        rng = np.random.default_rng(0)
        fold_of = dict(zip(ug, rng.permutation(len(ug)) % 5))
        f = np.array([fold_of[g] for g in groups])
        for k in range(5):
            tr = (f != k) & (y >= 0)
            wpos = (y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1)
            beta, b0 = fit_lr(X[tr], y[tr], np.where(y[tr] == 1, wpos, 1.0))
            te = f == k
            pred[te] = (torch.tensor(X[te], device="cuda") @ beta + b0).cpu().numpy()
            print("fold", k, "train pos", int((y[tr] == 1).sum()), "neg", int((y[tr] == 0).sum()), flush=True)
        tag = "sup"
    out = f"{WORK}/out/{src}_{mode}_sup.jsonl"
    mode_w = "a" if transfer_from and os.path.exists(out) else "w"
    with open(out, mode_w) as fo:
        for i, r in enumerate(recs):
            fo.write(json.dumps({"traj_id": r["traj_id"], "streams": {tag: [round(float(v), 4) for v in pred[ti == i]]}}) + "\n")
    print("wrote", out, tag)


def decode():
    from safetensors import safe_open
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-27B")
    snap = glob.glob(f"{HF}/hub/models--Qwen--Qwen3.5-27B/snapshots/*")[0]
    WU, g = None, None
    for f in glob.glob(f"{snap}/*.safetensors"):
        with safe_open(f, "pt") as sf:
            for k in sf.keys():
                if k.endswith("lm_head.weight"):
                    WU = sf.get_tensor(k).float().cuda()
                if k.endswith("language_model.norm.weight") or k == "model.norm.weight":
                    g = sf.get_tensor(k).float().cuda()
    gain = 1.0 + g if g.abs().mean() < 0.5 else g              # Qwen3.5 RMSNorm stores (gain - 1)
    lens = glob.glob(f"{HF}/hub/models--neuronpedia--jacobian-lens/snapshots/*/qwen3.5-27b/jlens/*/*.pt")[0]
    J = torch.load(lens, map_location="cpu", weights_only=True)["J"]
    probes = torch.load(f"{WORK}/probes.pt", weights_only=False)
    root = glob.glob(f"{HF}/hub/models--AlignmentResearch--probe-inference-weights/snapshots/*/qwen3.5-27b")[0]
    out = {}
    for l in ALL_LAYERS:
        dirs = {n: probes["W"][n][l].float() for n in probes["names"]}
        sd = torch.load(f"{root}/linear/layer_{l}/model.pt", map_location="cpu", weights_only=True)
        dirs["fibs"] = sd["linear.weight"].float().reshape(-1)
        Jl = J[l].float().cuda()
        for n, w in dirs.items():
            v = WU @ (gain * (Jl @ w.cuda()))
            v = (v - v.mean()) / v.std()
            top = torch.topk(v, 25).indices.tolist()
            bot = torch.topk(-v, 15).indices.tolist()
            out[f"{n}_L{l}"] = {"top": [tok.decode([i]) for i in top], "bottom": [tok.decode([i]) for i in bot]}
            print(n, l, "TOP", out[f"{n}_L{l}"]["top"][:15], flush=True)
    json.dump(out, open(f"{WORK}/out/probe_direction_jlens.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--src")
    ap.add_argument("--mode")
    ap.add_argument("--transfer-from")
    a = ap.parse_args()
    if a.cmd == "sup":
        sup(a.src, a.mode, a.transfer_from)
    elif a.cmd == "decode":
        decode()
