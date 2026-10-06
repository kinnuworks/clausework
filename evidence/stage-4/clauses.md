# Stage 4 clause register: seating changes and recurring amendments

Source: `tablekeeper/spec/stage-4.md`. Stages 1–3 still apply. Written by examiner from the specification alone.
Probe files: `test_s4_replan.py`, `test_s4_series_amend.py`, `test_s4_compat.py`. All stage-1/2/3 probe files are carried unchanged.

## Carried forward (cross-cutting, against every new entry point)

| id | carried clause | new entry points | probe |
|---|---|---|---|
| S4-C1 | §5 error body; 401 without a token; 403 for an authenticated non-manager (S3-20); 404 for an unknown resource | replans, apply, series amend | test_preview_apply_lifecycle, test_amend_validation_and_stale |
| S4-C2 | §7 idempotency: missing key 400, replay 200 identical even after later changes, reuse with a different body 409, a failed key is reusable | replans, apply, series amend | test_preview_apply_lifecycle, test_amend_basic_and_replay, test_amend_atomic_and_precedence |
| S4-C3 | S2-41/S3-C7 serialisability | concurrent applies; concurrent series amends from one revision | test_concurrent_applies, test_amend_concurrent_same_revision |
| S4-C4 | all-or-nothing (S1-90, S3-55) | failed apply (stale) and failed amend leave records, histories, revisions and keys unchanged | test_stale_plan_and_other_restaurant, test_amend_atomic_and_precedence |
| S4-C5 | S1-97 moves precedence by input order (stage-2 audit weak spot: second variant) | [own cancelled, other-restaurant] gives 409 reservation_cancelled; [own, other-restaurant] gives 422 | test_moves_precedence_variant |
| S4-C6 | all S1/S2/S3 clauses | carried probe files | test_basics … test_s3_series |

## Seating changes after a closure

| id | quoted text | family | discriminator |
|---|---|---|---|
| S4-01 | "requires a manager and an idempotency key" | ERR | non-manager 403, no token 401, no key 400. [lifecycle] |
| S4-02 | "The instants have explicit offsets and from < to; invalid interval is 422 validation_failed, unknown table 404." | ERR | from = to, from > to, no offset, garbage all give 422; unknown table 404; unknown restaurant 404. [lifecycle] |
| S4-03 | "Consider every confirmed booking at this restaurant overlapping that interval." | BEH, RULING | bookings on ANY table at the restaurant overlapping the closure are considered and listed (builder reading (i) agrees). The closure is half-open: a slot at the closure's `to` instant is not blocked. [lifecycle, bruteforce] |
| S4-10 | "Among feasible plans minimize, in order: 1. Number of bookings whose table set changes. 2. Total unused seats … 3. The vector of option ranks in ascending reservation-reference order. Singles … first in fixture order, then pairs in declared order, starting at 0." | BEST | brute-force reference over every option vector, run on 40 seeded random scenarios with 6 tables, 4 pairs and ≤ 6 considered bookings. Assignments, changed flags, moved_count and unused_seats must equal the unique optimum. [test_replan_matches_bruteforce] |
| S4-11 | "Assignments include every considered booking in reference order." | ORD | [bruteforce, lifecycle] |
| S4-12 | "with enough capacity under its own accepted terms" | BEH | after a later policy lowers q_4 to 2, a party-4 booking accepted under policy 0 still goes to q_4 (unused 0). A careless implementation picks the q_1+q_2 pair. [test_accepted_terms_capacity_and_cutoff_ignored] |
| S4-13 | "Diners' cancellation cutoffs do not prevent an operator repair." | TIME | a booking 45–60 minutes away is moved and applied. [same] |
| S4-14 | "without conflicts with fixed bookings, other assignments, previously applied closures or the proposed closure" | BEH | part of the brute-force model. [bruteforce] |
| S4-15 | "No feasible plan gives 409 no_feasible_plan, changing nothing." | ERR, AON | the restaurant revision is unchanged afterwards. [test_no_feasible_plan] |
| S4-16 | "Planning must support up to 6 tables, 4 declared pairs and 6 considered bookings; larger inputs may return 422 planning_limit." | LIM | within the limits a plan or no_feasible_plan must come back, never planning_limit. Above the limits planning_limit is allowed and not asserted. [bruteforce] |
| S4-20 | "Returns 201: {plan_id, restaurant_revision, closure, assignments, moved_count, unused_seats}" | PRES | the closure echo has the same table and the same instants (builder reading (ii)). [bruteforce] |
| S4-21 | "A restaurant revision starts at 0 after reset and increments once for each successful new booking, real amendment, cancellation, policy publication or plan application. No-op writes, failures, previews and replays do not increment it." | BEH, REP | sequence: 0; a booking gives 1; a replay, a failure, a no-op PATCH and another restaurant's booking keep it at 1; a real PATCH gives 2; moves 3; series adoption 4 (once); a policy 5; cancel 6; a repeat cancel 6. A preview reports the current value. [test_restaurant_revision_counting] |
| S4-22 | "Preview stores only a plan: no closure, occupancy, reservation revision or history changes." | AON | the record, history and availability are identical after the preview. [lifecycle] |
| S4-23 | "apply … Return 201 with {plan_id, restaurant_revision, reservations}; reservations include every considered booking in reference order." | PRES | [lifecycle] |
| S4-24 | "Unknown plan or one from another restaurant is 404." | ERR | [lifecycle] |
| S4-25 | "Any intervening restaurant revision invalidates the plan: 409 stale_plan, changing nothing." | ERR, AON | a real booking in between gives stale_plan; the stale plan's closure is not recorded. Writes at another restaurant, no-ops, failures and replays do not invalidate. [test_stale_plan_and_other_restaurant] |
| S4-26 | "A plan already applied under a different key gives 409 plan_already_applied; replay of the successful key returns the original response with 200, even after later changes." | REP, ORD, RULING | plan_already_applied comes before stale_plan (applying a plan raises the revision, so stale_plan would otherwise hide it; builder reading (iv) agrees). [lifecycle] |
| S4-27 | "Each moved booking increments its revision once and gains one reassigned history entry with a table_ids change and plan_id; accepted terms and times remain identical. Unmoved bookings gain nothing." | BEH | exact entry `{"field":"table_ids","from":["q_3"],"to":["q_4"]}` with plan_id; starts_at, ends_at, accepted_terms, identity and created_at are unchanged. [lifecycle] |
| S4-28 | "The restaurant revision increments once for the whole plan." | BEH | 3 → 4. [lifecycle] |
| S4-29 | "Closures thereafter exclude singles and pairs from availability and reject creates/amendments with 409 table_unavailable. In explanations, no_overlap is false for a closure" | BEH | single, pair, create, PATCH and explain are all checked. [lifecycle] |
| S4-30 | "Concurrent applications must not leave partially moved bookings. A closure at another restaurant does not invalidate this plan." | SIM, AON | 10 concurrent applies of two competing plans: exactly one 201, the rest stale_plan or plan_already_applied, and the winner's assignments are fully present. [test_concurrent_applies, test_stale_plan_and_other_restaurant] |

## Recurring amendments

| id | quoted text | family | discriminator |
|---|---|---|---|
| S4-50 | "POST /series/{series_id}/amend is an owner-only idempotent write. Unknown or another owner's series is 404; no token is 401." | ERR | [test_amend_validation_and_stale] |
| S4-51 | "Revision must be a positive integer; from_index an integer in 0..count-1; local_time exactly HH:MM in 00:00..23:59. Booleans are invalid integers. Invalid input gives 422" | ERR, LIM | 14 bad values plus each field missing. [same] |
| S4-52 | "a mismatched series revision gives 409 stale_revision before any occurrence's cutoff or booking validation" | ORD | stale wins over an otherwise failing time. [same] |
| S4-53 | "Consider indices at or after from_index, excluding cancelled occurrences and those marked exception." | BEH | [test_amend_skips_exceptions_and_cancelled] |
| S4-54 | "Change their clock time on their original scheduled local dates, retaining each reference, owner, party size and current table selection." | BEH | [basic] |
| S4-55 | "A change with identical resulting fields is a no-op … All-no-op or empty eligible sets succeed without changing revisions." | REP | [basic] |
| S4-56 | "Each changed occurrence gains one ordinary changed history entry and one reservation revision. The series and restaurant revisions each increase once … Series amendments do not mark exceptions." | BEH | [basic] |
| S4-57 | "Each real change checks its old accepted cutoff, then adopts the policy for its resulting start date" | BEH | an occurrence in a later policy's period gets that policy's terms. [test_amend_atomic_and_precedence] |
| S4-58 | "On failure, histories, idempotency records and all revisions remain unchanged." | AON | [same] |
| S4-59 | "Non-occupancy errors take precedence in occurrence-index order; otherwise an occupancy conflict returns table_unavailable." | ORD | occupancy at index 1 against outside_opening_hours at index 3 gives 422. [same] |
| S4-60 | "Replay returns the original response with 200 even after further edits or cancellations." | REP | [basic] |
| S4-61 | DST via ordinary rules (stage-3 S3-57 carried) | TIME | 02:30 on 2027-03-28 Berlin gives invalid_local_time. [test_amend_dst] |
| S4-62 | "Concurrent amendments from the same expected revision may not both make a real change." | SIM | [test_amend_concurrent_same_revision] |
| S4-67 | "Seating repairs may move series occurrences. They preserve their exception flags, scheduled dates, identities and accepted terms. Each affected series revision increases once per plan application if at least one member moved." | BEH | [test_repair_moves_series_occurrence] |

## Compatibility

| id | quoted text | family | discriminator |
|---|---|---|---|
| S4-80 | "A stage-4 service must accept exports produced by the same team's stages 1–3." | COMPAT | stage 1/2 via the carried test_s3_compat; stage 3 via test_s4_compat (TK_S3_URL from tag stage-3-frozen). |
| S4-81 | "These operations must support imported series, including moved and cancelled occurrences." | COMPAT | an imported series with a moved (exception) occurrence and a cancelled one is amended; only eligible occurrences change. [test_s4_compat] |
| S4-82 | "Earlier booking and series receipts, histories and retries remain valid." | COMPAT, REP | booking and series replays are identical; histories are identical after import; a replan and apply on imported bookings works. [same] |

## Rulings
S4-03 and S4-26 are recorded above. Builder readings (iii) and (v) also agree with the text. (iii): only a real change checks the
cutoff. (v): planning_limit above the stated limits is permitted ("may").

## Not probed
Reaching planning_limit, because it is optional. The cutoff path inside a series amendment: it needs an occurrence that falls within
its cutoff after adoption, which cannot be arranged reliably against the real clock.
