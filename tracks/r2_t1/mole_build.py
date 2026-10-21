"""MOLE (forgelab/mole, Apache-2.0; arXiv 2609.06966): account x day units for cross-day accumulation.

    uv run python tracks/r2_t1/mole_build.py --corpus gpt53_single_day [--corpus gpt53_multiday]

Input: data/raw/r2_t1/mole/{audit,transcripts,labels}/<corpus>/*.parquet (downloaded subsets only).
For each (account, day):
  - n_events, the audit-level rendering used by MOLE's LLM judge (`_render`: ts account service.action
    resource [EXTERNAL] args[:600]; at most MAX_EVENTS events, chronological). Supervision columns
    (account_kind, is_malicious, gate_decision) are never rendered.
  - the 20 MOLE rollup features (mole.audit.rollup; numeric metadata only).
  - labels: attack_session (the account ran a session with session_mode == attack that day; supervision only),
    outcome (labels parquet: executed / attempted / refused / no_attempt), is_insider (any attack session),
    collusive (scenario c1_/c2_).
  - classical monitors (level 0, $0): MOLE's robust z-score (ZScoreAnomalyMonitor) and peer-fit
    (PeerFitMonitor with the org-template peer groups) fit on ROUTINE account-days only, with 5-fold
    cross-fitting over routine accounts (a routine account is never scored by a profile fit on itself);
    insider accounts are scored by a profile fit on all routine accounts.
Output: data/processed/r2_mole/<corpus>/accountdays.parquet (+ renders.jsonl with the text).
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

from amd.common.schema import PROCESSED, REPO

RAW = REPO / "data" / "raw" / "r2_t1" / "mole"
CODE = REPO / "data" / "raw" / "r2_t1" / "mole_code"
OUT = PROCESSED / "r2_mole"
MAX_EVENTS = 400
ARG_CHARS = 600


def _import_mole():
    if "mole" not in sys.modules:
        m = types.ModuleType("mole")
        m.__path__ = [str(CODE / "mole")]
        sys.modules["mole"] = m
    from mole.audit.rollup import rollup
    from mole.audit.schema import AuditEvent
    from mole.monitors.classical.anomaly import ZScoreAnomalyMonitor
    from mole.monitors.facade.peer_fit import PeerFitMonitor, peers_from_org_yaml
    return rollup, AuditEvent, ZScoreAnomalyMonitor, PeerFitMonitor, peers_from_org_yaml


def render(g: pd.DataFrame) -> str:
    lines = []
    for r in g.itertuples():
        args = ""
        if r.args:
            try:
                args = json.dumps(json.loads(r.args), default=str, ensure_ascii=False)[:ARG_CHARS]
            except Exception:  # noqa: BLE001
                args = str(r.args)[:ARG_CHARS]
        ext = " EXTERNAL" if r.is_external else ""
        lines.append(f"{r.ts} {r.account} {r.service}.{r.action} {r.resource_id or ''}{ext} {args}".rstrip())
    return "\n".join(lines)


def build(corpus: str, renders_on: bool = True):
    rollup, AuditEvent, ZS, PF, peers_from_org_yaml = _import_mole()
    cols = ["event_id", "ts", "account", "service", "action", "resource_id", "args", "exit_code", "bytes",
            "dest_domain", "is_external", "task_id"]
    a = pd.concat([pd.read_parquet(f, columns=cols) for f in sorted((RAW / "audit" / corpus).glob("*.parquet"))])
    a["day"] = a.ts.str[:10]
    a = a.sort_values(["account", "ts"]).reset_index(drop=True)
    t = pd.concat([pd.read_parquet(f, columns=["account", "task_id", "sim_ts", "session_mode"])
                   for f in sorted((RAW / "transcripts" / corpus).glob("*.parquet"))])
    t["day"] = t.sim_ts.str[:10]
    att = t[t.session_mode == "attack"].groupby(["account", "day"]).size().rename("n_attack_sessions")
    lab = pd.read_parquet(RAW / "labels" / corpus / "0000.parquet").rename(columns={"date": "day"})
    lab = lab.drop_duplicates(["account", "day"]).set_index(["account", "day"])[["scenario", "outcome"]]

    # features via MOLE's rollup
    evs = []
    for r in a.itertuples():
        try:
            args = json.loads(r.args) if r.args else {}
        except Exception:  # noqa: BLE001
            args = {}
        evs.append(AuditEvent(event_id=r.event_id, ts=r.ts, real_ts=0.0, account=r.account, account_kind="",
                              service=r.service, action=r.action, resource_id=r.resource_id or "", args=args,
                              exit_code=int(r.exit_code or 0), bytes=int(r.bytes or 0),
                              dest_domain=r.dest_domain, is_external=bool(r.is_external), task_id=r.task_id or ""))
    rows = rollup(evs)
    by_key = {(x.account, x.date): x for x in rows}

    recs, renders = [], []
    for (acct, day), g in a.groupby(["account", "day"], sort=True):
        txt = render(g.iloc[:MAX_EVENTS]) if renders_on else ""
        if renders_on:
            renders.append({"account": acct, "day": day, "text": txt})
        recs.append(dict(account=acct, day=day, n_events=len(g), render_chars=len(txt),
                         n_attack_sessions=int(att.get((acct, day), 0))))
    D = pd.DataFrame(recs)
    D = D.join(lab, on=["account", "day"])
    D["attack_day"] = D.n_attack_sessions > 0
    ins = D.groupby("account").attack_day.any()
    D["is_insider"] = D.account.map(ins)
    scen = lab.reset_index().groupby("account").scenario.first()
    D["scenario_acct"] = D.account.map(scen)
    D["collusive"] = D.scenario_acct.fillna("").str.startswith(("c1_", "c2_"))

    # classical monitors, cross-fit over routine accounts
    routine = sorted(D.account[~D.is_insider].unique())
    rng = np.random.default_rng(0)
    folds = np.array_split(rng.permutation(routine), 5)
    peer_of = peers_from_org_yaml(str(CODE / "bootstrap" / "org_template.yaml"))
    D["z_score"] = np.nan
    D["peer_fit"] = np.nan

    def fit_score(fit_accts, score_mask):
        fr = [by_key[(x.account, x.day)] for x in D[D.account.isin(fit_accts)].itertuples()]
        zs = ZS().fit(fr)
        try:
            pf = PF(peer_of=peer_of).fit(fr)
        except TypeError:
            pf = PF(peer_of).fit(fr)
        idx = np.flatnonzero(score_mask)
        for i in idx:
            row = by_key[(D.account.iat[i], D.day.iat[i])]
            D.iat[i, D.columns.get_loc("z_score")] = zs._row_score(row)
            s = pf._row_score(row)
            D.iat[i, D.columns.get_loc("peer_fit")] = s[0] if isinstance(s, tuple) else s
    for f in folds:
        fit_score([x for x in routine if x not in set(f)], D.account.isin(f).to_numpy())
    fit_score(routine, D.is_insider.to_numpy())
    feat_names = [k for k in rows[0].FIELDS if k not in ("account", "date", "is_malicious")]
    F = pd.DataFrame([{k: getattr(by_key[(x.account, x.day)], k) for k in feat_names} for x in D.itertuples()])
    D = pd.concat([D, F.add_prefix("f_")], axis=1)
    out = OUT / corpus
    out.mkdir(parents=True, exist_ok=True)
    D.to_parquet(out / "accountdays.parquet", index=False)
    if renders_on:
        with open(out / "renders.jsonl", "w") as fh:
            for r in renders:
                fh.write(json.dumps(r) + "\n")
    print(f"{corpus}: {len(D)} account-days, {D.account.nunique()} accounts "
          f"({(~D.is_insider).groupby(D.account).first().sum()} routine), attack days {D.attack_day.sum()}, "
          f"render chars mean {D.render_chars.mean():.0f} total {D.render_chars.sum() / 1e6:.1f}M", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--no-renders", action="store_true", help="skip the LLM-input renders (classical monitors only)")
    a = ap.parse_args()
    for c in a.corpus:
        build(c, renders_on=not a.no_renders)


if __name__ == "__main__":
    main()
