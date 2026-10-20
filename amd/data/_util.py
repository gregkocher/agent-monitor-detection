"""Shared helpers for the data loaders (HTTP with retries, HF auth, truncation, zip/zstd access).

Secrets: the HF token is read from ~/.hf_token into the HF_TOKEN env var and only ever sent as an
Authorization header to huggingface.co. It is never printed or written to disk.
"""
from __future__ import annotations

import io
import json
import os
import time
import urllib.request
import zipfile
from pathlib import Path

import httpx

OUT_CHARS = 2000      # tool output / observation
ACTION_CHARS = 4000   # tool call arguments (file contents written by the agent can be long)
REASON_CHARS = 2000   # visible reasoning / assistant text


def hf_token() -> str | None:
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        p = Path("~/.hf_token").expanduser()
        if p.exists():
            tok = p.read_text().strip()
            os.environ["HF_TOKEN"] = tok
    return tok


def hf_headers() -> dict:
    tok = hf_token()
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def trunc(s, n: int) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = json.dumps(s, ensure_ascii=False, default=str)
    if len(s) <= n:
        return s
    half = n // 2
    return s[:half] + f"\n...[truncated {len(s) - n} chars]...\n" + s[-half:]


def fmt_call(function: str, arguments) -> str:
    """Render a tool call as `function(json-args)`, with string args kept readable."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            return f"{function}({arguments})"
    return f"{function}({json.dumps(arguments, ensure_ascii=False, default=str)})"


def content_text(content) -> tuple[str, str]:
    """Split an Inspect / OpenAI-style message content into (text, reasoning)."""
    if content is None:
        return "", ""
    if isinstance(content, str):
        return content, ""
    text, reasoning = [], []
    for part in content:
        if isinstance(part, str):
            text.append(part)
            continue
        t = part.get("type")
        if t == "text":
            text.append(part.get("text") or "")
        elif t == "reasoning":
            # Inspect ContentReasoning: `reasoning` holds visible text; `redacted` blobs are encrypted
            if not part.get("redacted"):
                reasoning.append(part.get("reasoning") or part.get("summary") or "")
        elif t in ("thinking",):
            reasoning.append(part.get("thinking") or "")
    return "\n".join(x for x in text if x), "\n".join(x for x in reasoning if x)


def http_get(url: str, headers: dict | None = None, timeout: float = 300, retries: int = 5,
             follow_redirects: bool = True) -> bytes:
    last = None
    for i in range(retries):
        try:
            r = httpx.get(url, headers=headers or {}, timeout=timeout, follow_redirects=follow_redirects)
            if r.status_code == 200:
                return r.content
            last = RuntimeError(f"HTTP {r.status_code} for {url.split('?')[0]}")
            if r.status_code in (403, 404):
                break
        except Exception as e:  # network hiccup
            last = e
        time.sleep(2 * (i + 1))
    raise last


def http_get_json(url: str, headers: dict | None = None, **kw):
    return json.loads(http_get(url, headers, **kw))


def download(url: str, dest: Path, headers: dict | None = None) -> Path:
    """Download to dest (atomic rename); skip if it already exists."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, headers=headers or {}, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    return dest


class HTTPRangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (for reading members of remote zips)."""

    def __init__(self, url: str, headers: dict | None = None):
        self.h = headers or {}
        self.pos = 0
        # GET bytes=0-0 instead of HEAD (presigned URLs often reject HEAD); follow redirects once.
        r = httpx.get(url, headers={**self.h, "Range": "bytes=0-0"}, follow_redirects=True, timeout=120)
        r.raise_for_status()
        self.url = str(r.url)
        cr = r.headers.get("Content-Range")
        self.size = int(cr.split("/")[-1]) if cr else int(r.headers["Content-Length"])
        # a redirect target (S3/CDN) must not receive the HF auth header
        if self.url.split("/")[2] != url.split("/")[2]:
            self.h = {}

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        for i in range(5):
            try:
                r = httpx.get(self.url, headers={**self.h, "Range": f"bytes={self.pos}-{end}"}, timeout=300)
                r.raise_for_status()
                d = r.content
                break
            except Exception:
                if i == 4:
                    raise
                time.sleep(2 * (i + 1))
        self.pos += len(d)
        return d

    def readinto(self, b):
        d = self.read(len(b))
        b[: len(d)] = d
        return len(d)


def open_remote_zip(url: str, headers: dict | None = None) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(url, headers), buffer_size=1 << 20))


def quantiles(xs, qs=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)):
    import numpy as np
    if not xs:
        return {}
    a = np.asarray(xs, dtype=float)
    return {f"q{int(q * 100)}": float(np.quantile(a, q)) for q in qs}
