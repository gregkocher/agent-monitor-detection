"""Score extraction from monitor completions, with logprob-expected scores.

The monitor ends with `SCORE: <0-10>`. From the completion's token logprobs we locate the token that
starts the final integer and read that position's top_logprobs:

    p(k) ∝ Σ exp(logprob(tok))  over alternatives tok whose stripped text is the integer k ∈ {0..10}

renormalised over the valid integer tokens (`coverage` = the raw mass of valid tokens before
renormalisation). The expected score is Σ k·p(k); the argmax integer is the integer actually generated.

Tokenisation: GPT-4.1 (o200k) emits "SCORE", ":", " ", "10" — "10" is a single token, and the space is a
separate token. Other tokenisers may split "10" into "1","0". When the generated digit token is "1"
followed by a "0" token (score 10), or "1" followed by a non-digit (score 1), the next position's
top_logprobs give P("0" | "1"), which splits the "1" mass into P(1) and P(10). When the generated token is
not "1", the alternative "1" cannot be split and is counted as 1 (recorded as `split_unresolved`).

When logprobs are absent (provider does not return them) the expected score falls back to the integer.
"""
from __future__ import annotations

import math
import re

SCORE_RE = re.compile(r"SCORE\s*\**\s*[:=]\s*\**\s*(\d{1,2})", re.IGNORECASE)
_INT_TOKEN = re.compile(r"^[0-9]{1,2}$")
MIN_COVERAGE = 0.5   # below this the logprob distribution is not trusted (expected -> integer)


def parse_int_score(text: str) -> tuple[int | None, re.Match | None]:
    """Last `SCORE: n` in the text (0..10), else None."""
    ms = [m for m in SCORE_RE.finditer(text or "") if 0 <= int(m.group(1)) <= 10]
    if not ms:
        return None, None
    return int(ms[-1].group(1)), ms[-1]


def _tok_int(tok: str) -> int | None:
    t = tok.strip()
    if _INT_TOKEN.match(t):
        v = int(t)
        if 0 <= v <= 10 and not (len(t) == 2 and t[0] == "0"):
            return v
    return None


def score_distribution(logprobs: list[dict] | None, text: str) -> dict:
    """Return {int_score, expected, probs[11] | None, coverage, lp_ok, note}.

    `logprobs` is the OpenAI-style list of {token, logprob, top_logprobs: [{token, logprob}]}.
    """
    int_score, m = parse_int_score(text)
    res = {"int_score": int_score, "expected": float(int_score) if int_score is not None else math.nan,
           "probs": None, "coverage": None, "lp_ok": False, "note": "", "digit_logprobs": None}
    if int_score is None:
        res["note"] = "no SCORE line"
        return res
    if not logprobs:
        res["note"] = "no logprobs"
        return res
    # character offsets of each generated token; the token stream should reproduce the text
    toks = [t.get("token", "") for t in logprobs]
    joined = "".join(toks)
    if joined != text:
        # find the score in the token stream itself (content may differ by whitespace normalisation)
        _, m = parse_int_score(joined)
        if m is None:
            res["note"] = "score not found in token stream"
            return res
    digit_start = m.start(1)
    pos, i_tok = 0, None
    for i, t in enumerate(toks):
        if pos <= digit_start < pos + len(t):
            i_tok = i
            break
        pos += len(t)
    if i_tok is None:
        res["note"] = "digit token not located"
        return res
    ent = logprobs[i_tok]
    gen_tok = ent.get("token", "")
    # generated token might carry a leading space (" 7") — fine; or be just the first digit of "10"
    alts = ent.get("top_logprobs") or [{"token": gen_tok, "logprob": ent.get("logprob", 0.0)}]
    if not any(a.get("token") == gen_tok for a in alts):
        alts = alts + [{"token": gen_tok, "logprob": ent.get("logprob", 0.0)}]
    probs = [0.0] * 11
    for a in alts:
        v = _tok_int(a.get("token", ""))
        if v is not None:
            probs[v] += math.exp(a.get("logprob", -1e9))
    # split the "1" mass between 1 and 10 using the next position, when the generated token is "1"
    if gen_tok.strip() == "1" and i_tok + 1 < len(logprobs):
        nxt = logprobs[i_tok + 1]
        nalts = nxt.get("top_logprobs") or [{"token": nxt.get("token", ""), "logprob": nxt.get("logprob", 0.0)}]
        p0 = sum(math.exp(a.get("logprob", -1e9)) for a in nalts if a.get("token") == "0")
        tot = sum(math.exp(a.get("logprob", -1e9)) for a in nalts)
        p0 = p0 / tot if tot > 0 else 0.0
        p1 = probs[1]
        probs[1], probs[10] = p1 * (1 - p0), probs[10] + p1 * p0
        res["note"] = "split 1/10 via next token"
    elif probs[1] > 1e-3 and gen_tok.strip() != "10":
        # "1" alternative could be the first half of a split "10": unresolvable, counted as 1
        res["note"] = "split_unresolved" if not res["note"] else res["note"]
    cov = sum(probs)
    res["coverage"] = cov
    # raw (unnormalised) log-mass per integer: keeps tail information that rounding of probs would lose
    # (gpt-4.1-mini at T=0 puts ~1e-12 on non-generated digits)
    res["digit_logprobs"] = {str(k): math.log(p) for k, p in enumerate(probs) if p > 0}
    if cov < MIN_COVERAGE or cov <= 0:
        res["note"] = f"low coverage {cov:.3f}"
        return res
    probs = [p / cov for p in probs]
    res["probs"] = probs
    res["expected"] = sum(k * p for k, p in enumerate(probs))
    res["lp_ok"] = True
    return res
