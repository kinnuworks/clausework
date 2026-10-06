# Stage 4: verdict, round 2

**ACCEPT**: revision `40b40839d0a9e9180d590e35223cf3d15061a367` (main), folder `stage-4/`, round 2.
Inspector, 2026-10-06. Round 2 re-checks the finisher's final UI-only change made after the round-1 ACCEPT of 4c5ea79. Nothing blocks.

## Scope check
- `git diff --stat 4c5ea79 40b4083 -- stage-1 stage-2 stage-3 stage-4`: only `stage-4/ui/css/base.css` (+2), `stage-4/ui/css/search.css` (+4/-1) and `stage-4/ui/js/views/booking.js` (+7/-1). No server code changed, so the round-1 API evidence stands unchanged: brute-force optimiser 188/188 plus 50/50 infeasible, apply, stale and concurrency, series amend, and compatibility (see verdict-1.md).
- `stage-1..4` at HEAD 937977c are identical to 40b4083.

## Evidence

| Step | Result |
|---|---|
| `check run … 4 isolated` (clone at 40b4083) | S1 **120/120**, S2 **25/25**, S3 **7/7**, S4 **6/6**. "claimed stage: 4 on the shipped checks" (checks/1006-074238-25894). |
| Examiner probes | Seal v2 `d50cd243…4640` matches. **118/118 passed**, 0 skipped (frozen S1/S2/S3 URLs set). This includes all UI probes and the policy-capacity grid probe. |
| Applied-plan surface (`/tmp/insp-s4r2-attack/ui_plan.py`, 375/768/1280) | A booking made in the UI on Booth (t_2) is moved by an applied plan to Bar. Resubmitting the unchanged form gives the **same** confirmation-reference with no booking-error, and confirmation-tables shows "Bar". The new **"Seating changed: the restaurant has since moved this booking to Bar"** note is shown and the grid refreshes. After re-searching, the closed t_2 cells 18:00/19:00/20:00 have data-available=false, 21:00 is true, and there are 0 mismatches between grid and available_options. Lookup shows "Bar". No sideways scrolling. |
| Stage-2 browser flows (`ui_flow.py`, 375/768/1280) | 18/18 pass, covering lost→retry giving the original reference, 409 keeping the edited form and refreshing, resubmit giving the same reference, auth-error when signed out, cancel on lookup, and visible focus. There is no sideways scrolling in any of the 54 captures. |
| Round-1 O1: seat-count clipping (`clip.py`) | 48 visible seat-count texts at each of 375, 768 and 1280: **0 clipped**, measured both against their own box and against the tile edge. At 375 the 2-seat tile reads "Window / 2 seats" on two lines (captured). **Resolved.** |
| Round-1 O2: stale form summary after a plan | The panel now shows a "Seating changed" information note with the new table and refreshes availability. It is not an error or an uncertain state. **Resolved.** |

## Clause rows
All 45 stage-4 clauses: **PASS**. Row-by-row evidence is in verdict-1.md, re-confirmed here by probes 118/118 and supplied S4 6/6 on 40b4083. All stage-1/2/3 clauses: PASS (carried probes, supplied S1/S2/S3, the browser flows above).

## Rulings
The round-1 rulings (i)–(vi) stand. The examiner has stated agreement with readings (i)–(v).

## Observations (not blocking)
- None new.
