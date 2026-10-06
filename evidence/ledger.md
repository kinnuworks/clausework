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
