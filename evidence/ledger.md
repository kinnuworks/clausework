# Factory ledger — tablekeeper (result-b)

Lead: lead. Hard stop 09:00 local (IST). Intake 06:33.

## Task record
- Workspace root: /Users/kinnu/hackathon4
- Result repo: /Users/kinnu/hackathon4/band-work/result-b (branch main). Do not edit mandates/.
- Specs: /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-{1..4}.md -> result-b/stage-{1..4}/
- Checks: /Users/kinnu/hackathon4/factory/bin/check run tablekeeper <repo> N [isolated]; check build tablekeeper <folder> N; check repo tablekeeper <repo>
- Judging: isolated. Key line: "claimed stage: N on the shipped checks". Ignore repo-scan complaints about README.md, FACTORY.md, room.json.
- Probe tooling: /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python (pytest, httpx, playwright+chromium). Docker on PATH.
- Delivery rules: each folder self-contained (Dockerfile, RUN.md, source); stage-N+1 starts as copy of stage-N (no nested .git); each folder judged against checks 1..N; no later-stage work early; frozen folders never change; no runtime network (assets in image); no credentials, no literal assignment to *KEY/*TOKEN/*SECRET/*PASSWORD in Dockerfile/config; no symlinks/submodules.
- Surfaces: stage 2 adds browser screens (/, /signup, /login, /lookup) + product brief (evening service, ink green/charcoal, amber accent). Stage 1 API only.

## Seats
All five seats present in room at 06:33 (dhirajkavuri/{lead,builder,finisher,examiner,inspector}).

## Time shares (06:36 -> 09:00, 144 min)
| Stage | Window | Share |
|---|---|---|
| 1 | 06:36 - 07:15 | 39 min |
| 2 | 07:15 - 07:58 | 43 min (weighted) |
| 3 | 07:58 - 08:38 | 40 min (weighted) |
| 4 | 08:38 - 08:55 | 17 min |
| Report | 08:55 - 09:00 | 5 min |

## Events
| Time | Stage | Step | Round | Revision | Owes | Note |
|---|---|---|---|---|---|---|
| 06:33 | - | intake | - | 974014c | - | Task received, seats confirmed |
| 06:42 | 1 | orders sent | 1 | 447a0a5 | builder: revision by 07:05; examiner: clauses+seal by 07:00 | Full spec pasted in 3 parts each |
| 06:44 | 2 (look-ahead) | finisher order | - | - | finisher: design brief by 07:05, static UI in evidence/design/ui/ by ~07:30 | Stage 1 has no surface; finisher builds stage-2 UI outside stage folders |
| 06:47 | 2 (look-ahead) | finisher brief in | - | 710c5ff | finisher: UI by ~07:30 | Single index.html for 4 routes, assets under /static/ |
| 06:48 | 1 | seal in | 1 | 0166619 | builder: revision report | 96 clauses, 53 probes, seal 9901cc05…b993 |
| 06:52 | 1 | inspect | 1 | 85374cb | inspector: verdict-1 by 07:10; examiner: reveal + probe audit by 07:10 | Builder self-check isolated 120/120, claimed stage 1. 8 doubts forwarded to inspector |
| 06:55 | 1 | verdict | 1 | 85374cb | builder: fix F1 (5xx on deeply nested JSON, idempotency canonical recursion) → inspector round 2 | REJECT. Supplied 120/120, probes 53/53, probe audit 5/5 planted caught |
| 06:55 | 1 | round 2 ordered | 2 | 85374cb | builder: F1 fix + O2 (seed hashing speed) + O3 (numeric reference) by 07:08; examiner: ruling on moves 404-vs-409 order | Inspector accepted all 8 builder doubts |
| 06:55 | 2 (look-ahead) | examiner order | - | - | examiner: stage-2 clauses + seal by 07:25 | |
| 06:56 | 2 (look-ahead) | finisher UI in | - | 8282510 / b297385 | finisher: polish rough edges | 48 captures, 21/21 behaviour self-check against mock API; serving contract in evidence/design/ui/README.md |
| 06:59 | 1 | verdict | 2 | fa79f76 | - | ACCEPT. 120/120 isolated, 53/53 probes, 97 clauses pass. Ruling S1-97: moves errors in input order |
| 06:59 | 1 | FROZEN | 2 | fa79f76 (tag stage-1-frozen) | - | Rounds used 2; time 06:38-06:59 (21 min). Open clauses: none known. Note: F1 regression probe to be carried in stage-2 probes |
| 06:59 | 2 | OPEN | 1 | - | builder: stage-2 revision by 07:40; finisher: copy UI into stage-2 static dir + real-API captures; examiner: stage-2 seal by 07:25 | |
| 07:00 | 1 | ruling | - | 14b7fe2 | - | S1-97 final: moves errors resolved per item in input order (404→422 restaurant→409 cancelled→409 cutoff→field codes), occupancy last. Frozen fa79f76 already conforms (inspector verified) |
| 07:00 | 2 | seal in | 1 | 5af0d19 | builder: revision by 07:40 | 52 rows, 78 probes (incl. 53 stage-1, 11 Playwright UI, 1 compat), seal ed593705…c047 |
| 07:01 | 2 | seal v2 | 1 | ffec895 | - | Seal replaced (before any reveal): 6a3480c8…d4ca0, 79 probes, adds F1 depth-3000 regression. TK_S1_URL must be a container from git archive stage-1-frozen |
| 07:02 | 2 | builder status | 1 | c6f3a5a | finisher: copy UI into stage-2/ui/; builder: final report after UI | Isolated: S1 120/120, S2 25/25, claimed stage 2 (UI empty yet) |
| 07:04 | 2 | inspect | 1 | c7275b7 | inspector: verdict-1 by 07:40; examiner: reveal + audit by 07:40 | Builder: isolated S1 120/120, S2 25/25, claimed 2. 5 doubts forwarded |
| 07:06 | 2 | revision amended | 1 | fbae59c | inspector: verdict on fbae59c | Finisher polish beec94c (stage-2/ui CSS only) landed after builder report; real-API captures fbae59c; behave 31/31, upgrade 9/9 |
| 07:07 | 3 (look-ahead) | seal in | - | 4f3a492 | - | 69 rows, 101 probes, seal c19fc8cf…46a6; needs TK_S1_URL + TK_S2_URL (stage-2-frozen) |
