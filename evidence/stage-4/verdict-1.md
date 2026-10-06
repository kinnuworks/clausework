# Stage 4: verdict, round 1

**ACCEPT**: revision `4c5ea79452c402ea796b00fa1fc9bf8d8da8d521` (main), folder `stage-4/`, round 1.
That is the builder's 9334ea9 plus the finisher's stage-4/ui commit. `stage-4/` at HEAD ce06c6a is identical.
Inspector, 2026-10-06. No blocking failures.

## Evidence

| Step | Result |
|---|---|
| Clean copies | `/tmp/insp-s4r1-3MUK`: stage-4 at 4c5ea79, plus stage-1/2/3 from their frozen tags. Repo clone at 4c5ea79 in `/tmp/insp-s4r1-repo-XVEL`. No nested .git, no symlinks. |
| Frozen stages | `git diff stage-N-frozen 4c5ea79 -- stage-N` is empty for N = 1, 2, 3. stage-4 is stage-3 plus optimizer.js, replans.js and series-amend.js, with the changed modules listed in the inspection log. |
| `check run … 4 isolated` | S1 **120/120**, S2 **25/25**, S3 **7/7**, S4 **6/6**. "claimed stage: 4 on the shipped checks" (checks/1006-073346-22631). |
| `check build … stage-4 4` | S1, S3 and S4 pass. The S2 error is the upgrade test, which needs `run` mode (same harness limit as in earlier stages). |
| `check repo` | Only the 3 complaints that may be ignored. |
| Rules 1, 5, 6 | Dockerfile, RUN.md and source are present. Healthy in under 1 s at 2 vCPU / 2 GiB. No credentials. |
| Examiner probes | Seal **v2** `d50cd243…4640` (adds test_s4_ui_policy.py) recomputes and **matches**. **118/118 passed**, 0 skipped. TK_S1_URL, TK_S2_URL and TK_S3_URL point at containers built from the frozen tags. |

## Own attack (scripts in `/tmp/insp-s4r1-attack/`)

**Optimiser against brute force (`brute.py`), 260 random fixtures.** Each fixture has 2–6 tables with capacity 1–6, 0–4 declared pairs in random orientation, and random singles and pairs booked at random times. In about half of them a policy is published partway through, so some bookings carry different accepted capacities and durations. The closure covers a random table and window. For every considered booking I enumerated all singles and declared pairs that have enough seats under **that booking's own accepted_terms**, that avoid the proposed closure, and that avoid every fixed booking. I then minimised (moved, unused, rank vector) and compared the result with the service.
- **188/188** feasible cases are identical: moved_count, unused_seats, and every assignment's table_ids and changed flag.
- **50/50** infeasible cases return 409 no_feasible_plan.
- 3 cases with 7–8 considered bookings return 422 planning_limit, which the spec allows above 6.
- 19 cases had no considered bookings and correctly returned 201 with an empty plan.

**Preview and apply (`apply.py`):**
- Preview refusals: non-manager → 403. No token → 401. from ≥ to → 422. No offset → 422. Unknown table → 404.
- Preview changes nothing: revision and history are untouched.
- Any later booking at the restaurant → `stale_plan`. A booking at another restaurant does not make the plan stale.
- Plan from another restaurant → 404. Unknown plan → 404. Non-manager apply → 403.
- **10 concurrent applies of one plan → exactly 1 × 201 and 9 × plan_already_applied.** The winner's key replays 200 with an identical body, and a new key gives 409 plan_already_applied.
- After apply:
  - The moved booking has the new table set and revision 2, with identical start, end and accepted_terms. It gains one `reassigned` entry with plan_id and a table_ids change.
  - Unmoved bookings are unchanged.
  - Availability drops the closed table and any pair containing it. Explain shows no_overlap false for it.
  - Creating on the closed table, booking a pair that contains it, or amending into it → 409 table_unavailable.
  - The same table at another restaurant can still be booked.
- no_feasible_plan changes nothing: the next preview still reports the same restaurant_revision.

**Series amend and compatibility (`series.py`):**
- Invalid input → 422: bool or 0 revision, from_index = count, `24:00`, `8:00`, `20:00:00`. Stale revision → 409. Another owner → 404. No token → 401.
- Occupancy conflict → 409 table_unavailable. An off-grid time → not_on_slot_grid, which takes precedence over the occupancy conflict.
- A successful amend from index 1:
  - Changed occurrences move to their own dates at the new time, with revision +1 and one `changed` entry each.
  - The exception occurrence and the cancelled occurrence are skipped.
  - No exceptions are marked, and the series revision rises by 1.
- Replay → 200 with the identical body. An all-no-op amend → 201 with no revision change.
- A plan application that moves an occurrence raises the series revision by 1 and keeps the exception flags.
- A stage-3 export containing a series with a moved (exception) occurrence and a cancelled occurrence imports. The series replay gives 200. Amend skips the exception and the cancelled occurrence. A replan on the imported data works.

**Surface after an applied plan (`ui_plan.py`, real API, 375/768/1280):**
- A booking made in the UI is moved by an applied plan. Resubmitting the unchanged form returns the **same** confirmation-reference with no error, and the ticket re-reads the booking: confirmation-tables shows "Bar" (the new table).
- Re-searching: t_2 cells inside the closure have data-available=false, and there are **0** mismatches between grid cells and available_options.
- Lookup shows reservation-tables "Bar". No sideways scrolling.
- The full stage-2 flow suite (`ui_flow.py`) passes 18/18 at all three widths, with no sideways scrolling in 54 captures.

## Clause rows: stage 4 (45 clauses in evidence/stage-4/clauses.md)

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S4-C1 | §5 error body; 401 without a token; 403 for an authenticated non-manager (S3-20); 404… | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C2 | §7 idempotency: missing key 400, replay 200 identical even after later changes, reuse… | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C3 | S2-41/S3-C7 serialisability | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C4 | all-or-nothing (S1-90, S3-55) | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C5 | S1-97 moves precedence by input order (stage-2 audit weak spot: second variant) | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C6 | all S1/S2/S3 clauses | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-C7 | stage-2 grid rule "A cell is true exactly when its table_id is in that slot's availab… | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-01 | requires a manager and an idempotency key | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-02 | The instants have explicit offsets and from < to; invalid interval is 422 validation_… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-03 | Consider every confirmed booking at this restaurant overlapping that interval. | PASS | probes lifecycle, bruteforce; supplied S4 6/6; inspector attack |
| S4-10 | Among feasible plans minimize, in order: 1. Number of bookings whose table set change… | PASS | probes test_replan_matches_bruteforce; supplied S4 6/6; inspector attack |
| S4-11 | Assignments include every considered booking in reference order. | PASS | probes bruteforce, lifecycle; supplied S4 6/6; inspector attack |
| S4-12 | with enough capacity under its own accepted terms | PASS | probes test_accepted_terms_capacity_and_cutoff_ignored; supplied S4 6/6; inspector attack |
| S4-13 | Diners' cancellation cutoffs do not prevent an operator repair. | PASS | probes same; supplied S4 6/6; inspector attack |
| S4-14 | without conflicts with fixed bookings, other assignments, previously applied closures… | PASS | probes bruteforce; supplied S4 6/6; inspector attack |
| S4-15 | No feasible plan gives 409 no_feasible_plan, changing nothing. | PASS | probes test_no_feasible_plan; supplied S4 6/6; inspector attack |
| S4-16 | Planning must support up to 6 tables, 4 declared pairs and 6 considered bookings; lar… | PASS | probes bruteforce; supplied S4 6/6; inspector attack |
| S4-20 | Returns 201: {plan_id, restaurant_revision, closure, assignments, moved_count, unused… | PASS | probes bruteforce; supplied S4 6/6; inspector attack |
| S4-21 | A restaurant revision starts at 0 after reset and increments once for each successful… | PASS | probes test_restaurant_revision_counting; supplied S4 6/6; inspector attack |
| S4-22 | Preview stores only a plan: no closure, occupancy, reservation revision or history ch… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-23 | apply … Return 201 with {plan_id, restaurant_revision, reservations}; reservations in… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-24 | Unknown plan or one from another restaurant is 404. | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-25 | Any intervening restaurant revision invalidates the plan: 409 stale_plan, changing no… | PASS | probes test_stale_plan_and_other_restaurant; supplied S4 6/6; inspector attack |
| S4-26 | A plan already applied under a different key gives 409 plan_already_applied; replay o… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-27 | Each moved booking increments its revision once and gains one reassigned history entr… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-28 | The restaurant revision increments once for the whole plan. | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-29 | Closures thereafter exclude singles and pairs from availability and reject creates/am… | PASS | probes lifecycle; supplied S4 6/6; inspector attack |
| S4-30 | Concurrent applications must not leave partially moved bookings. A closure at another… | PASS | probes test_concurrent_applies, test_stale_plan_and_other_restaurant; supplied S4 6/6; inspector attack |
| S4-50 | POST /series/{series_id}/amend is an owner-only idempotent write. Unknown or another … | PASS | probes test_amend_validation_and_stale; supplied S4 6/6; inspector attack |
| S4-51 | Revision must be a positive integer; from_index an integer in 0..count-1; local_time … | PASS | probes same; supplied S4 6/6; inspector attack |
| S4-52 | a mismatched series revision gives 409 stale_revision before any occurrence's cutoff … | PASS | probes same; supplied S4 6/6; inspector attack |
| S4-53 | Consider indices at or after from_index, excluding cancelled occurrences and those ma… | PASS | probes test_amend_skips_exceptions_and_cancelled; supplied S4 6/6; inspector attack |
| S4-54 | Change their clock time on their original scheduled local dates, retaining each refer… | PASS | probes basic; supplied S4 6/6; inspector attack |
| S4-55 | A change with identical resulting fields is a no-op … All-no-op or empty eligible set… | PASS | probes basic; supplied S4 6/6; inspector attack |
| S4-56 | Each changed occurrence gains one ordinary changed history entry and one reservation … | PASS | probes basic; supplied S4 6/6; inspector attack |
| S4-57 | Each real change checks its old accepted cutoff, then adopts the policy for its resul… | PASS | probes test_amend_atomic_and_precedence; supplied S4 6/6; inspector attack |
| S4-58 | On failure, histories, idempotency records and all revisions remain unchanged. | PASS | probes same; supplied S4 6/6; inspector attack |
| S4-59 | Non-occupancy errors take precedence in occurrence-index order; otherwise an occupanc… | PASS | probes same; supplied S4 6/6; inspector attack |
| S4-60 | Replay returns the original response with 200 even after further edits or cancellatio… | PASS | probes basic; supplied S4 6/6; inspector attack |
| S4-61 | DST via ordinary rules (stage-3 S3-57 carried) | PASS | probes test_amend_dst; supplied S4 6/6; inspector attack |
| S4-62 | Concurrent amendments from the same expected revision may not both make a real change… | PASS | probes test_amend_concurrent_same_revision; supplied S4 6/6; inspector attack |
| S4-67 | Seating repairs may move series occurrences. They preserve their exception flags, sch… | PASS | probes test_repair_moves_series_occurrence; supplied S4 6/6; inspector attack |
| S4-80 | A stage-4 service must accept exports produced by the same team's stages 1–3. | PASS | probes see register; supplied S4 6/6; inspector attack |
| S4-81 | These operations must support imported series, including moved and cancelled occurren… | PASS | probes test_s4_compat; supplied S4 6/6; inspector attack |
| S4-82 | Earlier booking and series receipts, histories and retries remain valid. | PASS | probes same; supplied S4 6/6; inspector attack |

Stage-1/2/3 clauses: PASS. Evidence: carried probes (118/118), supplied S1 120/120, S2 25/25 and S3 7/7, and the browser flows above.

## Rulings on the builder's readings (none blocks)
(i) **Considered = every confirmed booking at the restaurant overlapping [from,to), on any table:** accepted. This is the literal text ("every confirmed booking at this restaurant overlapping that interval"), and brute force agrees with it.
(ii) **Closure echo returns from and to as sent:** accepted.
(iii) **An occurrence already at the requested time is a full no-op, with no cutoff check:** accepted. The spec says "each **real** change checks its old accepted cutoff", and a change with identical resulting fields is a no-op.
(iv) **Apply order 404 → plan_already_applied → stale_plan:** accepted. An applied plan is always behind the revision, so checking already-applied first is the only way to return that code under a new key, as the spec requires.
(v) **Always 422 planning_limit above the limits:** accepted ("larger inputs may return").
(vi) **Restaurant revision also rises for adoption, and once per batch or series amend that changes something:** accepted. These are real amendments or new bookings under the counting rule, and stage 3 states it for adoption.

## Observations (not blocking)
- O1. At 375 px the 2-seat tile's "2 seats" text is clipped at the tile edge ("2 seat"). It is legible as a count but cut off.
- O2. After a plan moves the booking that is open in the panel, the ticket updates to the new table, but the open form's summary still names the originally chosen table until the diner searches again. No live updates are required, so this is not a clause violation.
- O3. The `check build` stage-2 error is the usual harness-mode limit. Rely on `check run`.
