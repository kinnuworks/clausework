#!/usr/bin/env python3
"""Per-seat token use from Claude Code session logs. Usage: usage-report.py <projects dir> <start ISO> <end ISO>"""
import sys, json, glob, os, collections
proj, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
SEATS = ("lead", "builder", "finisher", "examiner", "inspector")
PRICE = {"in": 4.0, "out": 20.0, "cache_read": 0.20, "cache_write": 5.0}  # USD per million tokens, Opus 5.5 list; cache write assumed 1.25x input
rows = []
import re
AUTHOR = re.compile(r"(?:user\.name[= ]+|GIT_AUTHOR_NAME=|--author[= ]+)[\\\"']*(lead|builder|finisher|examiner|inspector)")
for f in sorted(glob.glob(os.path.join(proj, "*.jsonl"))):
    u = collections.Counter(); seat = None; models = set(); t0 = t1 = None; turns = 0; seen = set(); who = collections.Counter()
    for line in open(f, errors="replace"):
        try: e = json.loads(line)
        except Exception: continue
        ts = e.get("timestamp")
        if not ts or ts < start or ts > end: continue
        t0 = t0 or ts; t1 = ts
        msg = e.get("message") or {}
        for m in AUTHOR.findall(line): who[m] += 1
        if e.get("type") == "assistant" and msg.get("usage"):
            mid = msg.get("id")
            if mid in seen: continue
            seen.add(mid); turns += 1; models.add(msg.get("model"))
            us = msg["usage"]
            u["in"] += us.get("input_tokens", 0); u["out"] += us.get("output_tokens", 0)
            u["cache_read"] += us.get("cache_read_input_tokens", 0); u["cache_write"] += us.get("cache_creation_input_tokens", 0)
    seat = who.most_common(1)[0][0] if who else None
    if turns: rows.append((seat or os.path.basename(f)[:8], t0, t1, turns, u, models))
tot = collections.Counter(); cost_tot = 0
print("| Seat | Model | API calls | Input | Cache write | Cache read | Output | API-equivalent |"); print("|---|---|---:|---:|---:|---:|---:|---:|")
for seat, t0, t1, turns, u, models in sorted(rows, key=lambda r: str(r[0])):
    cost = sum(u[k] * PRICE[k] for k in PRICE) / 1e6; cost_tot += cost; tot.update(u); tot["turns"] += turns
    print(f"| {seat} | {','.join(sorted(m for m in models if m))} | {turns} | {u['in']:,} | {u['cache_write']:,} | {u['cache_read']:,} | {u['out']:,} | ${cost:.2f} |")
print(f"| **Total** | | {tot['turns']} | {tot['in']:,} | {tot['cache_write']:,} | {tot['cache_read']:,} | {tot['out']:,} | **${cost_tot:.2f}** |")
print("all tokens:", f"{tot['in']+tot['cache_write']+tot['cache_read']+tot['out']:,}")
