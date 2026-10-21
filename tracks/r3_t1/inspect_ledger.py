"""Print a few ledger-variant outputs from the MB cache (sanity check of the carried-forward notes)."""
import json
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/raw/r3_t1/mb_cache.sqlite")
rows = db.execute("SELECT rec FROM r").fetchall()
led = [json.loads(r[0]) for r in rows if "LEDGER" in (json.loads(r[0]).get("text") or "")]
print(len(rows), "cached;", len(led), "with a LEDGER block")
for rec in [x for x in led if x["int_score"] >= 5][:2] + led[:1]:
    print("----", rec["int_score"], rec["expected"]); print(rec["text"][-700:])
