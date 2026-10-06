# Stage 3: verdict, round 2

**ACCEPT**: revision `840eef4260fb24ba878a82289d3d8c1251cf0615` (main), folder `stage-3/`, round 2.
Inspector, 2026-10-06. Round-1 failure F1 is fixed, and nothing that passed has broken.

## What changed since round 1
- `git diff bc172db 840eef4` touches only `stage-3/ui/`. First `a8900ab` (the F1 fix plus the stage-2 O1/O2 fixes), then `840eef4`, which changes 3 files: format.js, booking.js and grid.js.
- `stage-3/src` is identical to bc172db, so the round-1 API evidence (`/tmp/insp-s3r1-attack/api.py`, `compat.py`) still applies unchanged.
- stage-1 and stage-2 are identical to their frozen tags.
- stage-1, stage-2 and stage-3 at HEAD 576622d are identical to 840eef4.

## F1 smallest input, re-run first
Clean export of 840eef4 (`/tmp/insp-s3r2-141Y`), run as a container with 2 vCPU / 2 GiB.
- **Setup:** restaurant r (Europe/Berlin). Tables t_1 (capacity 2), t_2 (capacity 4), t_3 (capacity 4). `combinable [["t_2","t_1"]]`. A manager-published policy from 2027-03-01: slot 45, open 17:00–22:00, capacities {t_1:6, t_2:6, t_3:1}.
- **Search:** 2027-03-05.
- **Result:** for parties 10, 5 and 1, at **375, 768 and 1280**: the slot times match the API, and there are **0 mismatches** between grid cells and `available_options`. For party 10 the `slot-t_2+t_1-*` pair cell is present with data-available="true" ("12 seats · Open"). Tiles show the policy's capacities ("Window 6 seats", "Bar 1 seat"). **FIXED.**
- **O1 (round 1):** "1 seat" is now singular. **Resolved.**

## Everything else

| Step | Result |
|---|---|
| `check run … 3 isolated` (clone at 840eef4) | S1 **120/120**, S2 **25/25**, S3 **7/7**. Stage-4 probe **FAILS**. "claimed stage: 3 on the shipped checks" (checks/1006-072806-20216). |
| Examiner probes | Seal `c19fc8cf…46a6` matches. **101/101 passed**, 0 skipped (TK_S1_URL and TK_S2_URL point at the frozen-tag containers). |
| Browser flows (Chromium, real API, 375/768/1280) | 18/18 pass. At each width: <br>• signed-out click shows auth-error <br>• lost response twice, then the retry gives the original reference, with no uncertain or error elements left <br>• unchanged resubmit gives the same reference <br>• a 409 keeps the edited form (party 4), shows no confirmation and refreshes the grid <br>• cancel on the lookup screen removes the cancel button <br>• focus has a 2 px amber outline <br>• current-user appears on all 4 routes, and the pair labels appear in the summary, the ticket and the lookup <br>**No sideways scrolling in any of the 54 captures.** |
| Surface | I looked at the 375 captures of the grid under the policy and of the ticket. The ticket shows the end time (19:00–20:30) and keeps the reference on one line. The look matches the stage-2 surface. |
| Rules 1, 2, 4, 5, 6 | Unchanged from round 1. PASS. |

## Clause rows: stage 3 (69 clauses)

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S3-C1 | S1-13/14: error body; 400 for an unparseable or non-object body and for wrong JSON ty… | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C2 | F1 / S2-C6: no 5xx from deeply nested unknown fields | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C3 | S1-30..37 idempotency: missing key 400, length 256 gives 422, replay 200 identical, r… | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C4 | S1-20/27 auth: 401 without a token | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C5 | S1-56 owner-only 404 | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C6 | S1-90/S2-28 all-or-nothing | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C7 | S1-96/S2-41 serialisability | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-C8 | all S1-* and S2-* clauses (stage 2 must remain intact) | PASS | probes see register (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-01 | Every table of the restaurant appears exactly once, available or not, in fixture orde… | PASS | probes test_explain_shape_and_reference (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-02 | Both rules are reported for every table, in the order above … No rule may be omitted. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-03 | available is true exactly when both hold, and the table_ids whose available is true a… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-04 | a table excluded by both reports both false | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-05 | Without it the response keeps stage 1's shape — no explanation fields appear. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-06 | Its only accepted value is true; any other value, including false, 1 and the empty st… | PASS | probes test_explain_validation_and_closed (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-07 | A closed day still returns slots: [] … a slot with no available table still appears —… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-08 | With explain=true, each table explanation additionally identifies its policy_version.… | PASS | probes test_explain_uses_policy (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-10 | seq starts at 1 and increases by exactly 1 … returned in seq order, which is also at … | PASS | probes test_history_rules (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-11 | created names all three fields, each with from: null" (order table_id, starts_at_loca… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-12 | changed names only the fields that actually changed, in the order table_id, starts_at… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-13 | A PATCH that sets a field to the value it already has … still succeeds, and it record… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-14 | cancelled carries an empty changes, and nothing follows it | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-15 | Replaying an idempotent POST /reservations records nothing | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-16 | Only its owner may read it; anyone else, signed in or not, gets the same 404" / "Hist… | PASS | probes test_history_and_decision_visibility (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-17 | Each history entry additionally carries the reservation's resulting revision and comp… | PASS | probes test_amendment_reselects_policy (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-20 | Only these users may publish policies. Unknown restaurant is 404; an authenticated no… | PASS | probes test_publish_permissions_and_versions (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-21 | requires an idempotency key, with stage 1's replay rules | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-22 | Returns 201 with the supplied policy plus policy_version, an integer starting at 1 an… | PASS | probes test_policy_validation_no_version (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-23 | GET … is public and returns {policies: [...]} in publication order, omitting policy 0… | PASS | probes test_publish_permissions_and_versions (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-24 | All fields above are required … grid and duration are integers 1..1440; cutoff 0..100… | PASS | probes test_policy_validation_no_version (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-25 | Invalid policy is 422 validation_failed, with no version or state change. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-26 | For a booking's local start date, choose the greatest effective_from not later than t… | PASS | probes test_policy_selection (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-27 | Policy 0 is the original fixture's rules and applies before any published policy. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-28 | A policy publication does not change existing bookings, their end times, or their his… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-29 | Availability and booking decisions use the selected policy, not that detail. | PASS | F1 re-run on 840eef4 at 375/768/1280: 0 grid/API mismatches; API as round 1 |
| S3-33 | Every reservation response gains revision (1 at creation) and accepted_terms … a snap… | PASS | probes policy_selection, history (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-34 | A real diner amendment … checks the old accepted cutoff first, then validates all res… | PASS | probes test_amendment_reselects_policy (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-35 | Failed amendments change nothing. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-36 | Cancel checks the accepted cutoff, against the current start. | PASS | probes test_accepted_cutoff_rules (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-37 | A no-op amendment … still requires a confirmed, editable booking. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-38 | expected_revision. A positive integer differing from the current revision gives 409 s… | PASS | probes test_expected_revision, test_accepted_cutoff_rules (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-39 | Two concurrent amendments using one revision: at most one real change succeeds." / "C… | PASS | probes test_expected_revision, test_history_rules (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-40 | GET /reservations/{reference}/decision returns {reference, revision, accepted_terms} … | PASS | probes test_history_and_decision_visibility (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-41 | Responses to old idempotency keys remain the original response, including the origina… | PASS | probes test_history_rules (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-45 | Occurrence zero is the anchor itself: its reference, identity, revision, terms, histo… | PASS | probes test_adopt_basic (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-46 | Unknown or another owner's anchor gives 404; cancelled gives 409 reservation_cancelle… | PASS | probes test_adopt_errors, test_adopt_basic (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-47 | count is an integer 2..12 …; interval_weeks 1..4. Invalid values, including booleans,… | PASS | probes test_adopt_errors (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-48 | Occurrence i starts on the anchor's local calendar date plus i × interval_weeks × 7 d… | PASS | probes test_series_exceptions_and_revision (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-49 | Each generated occurrence independently selects its date's policy | PASS | probes test_adopt_basic (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-50 | Occurrences appear in ordinary reservation lists, occupy tables, and have ordinary hi… | PASS | probes test_adopt_basic (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-51 | A real individual PATCH permanently marks that occurrence as exception: true and incr… | PASS | probes test_series_exceptions_and_revision (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-52 | Cancellation increments the series revision once … not … an exception; repeated cance… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-53 | Cancelling the anchor does not cancel its siblings. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-54 | Replays return the original series response, even after later changes, and change no … | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-55 | No partial series, reservations, histories, counters or idempotency claim survive fai… | PASS | probes test_adopt_atomic_and_first_failure (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-56 | The first failing occurrence in index order determines the ordinary booking error. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-57 | A nonexistent local time rejects the entire adoption with invalid_local_time; repeate… | PASS | probes test_adopt_dst (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-58 | Generated occurrences use the anchor's party size and table selection. | PASS | probes test_combined_anchor_series (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-60 | For a creation of a pair, replace the table_id change by table_ids (from null to the … | PASS | probes test_combined_history (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-61 | A reversed input pair names the same set and is not an amendment on its own. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-62 | For a change involving a pair, use table_ids (complete before/after lists)" / single-… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-63 | capacity is the sum of the selected policy's capacities | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-70 | Each real change in POST /reservation-moves uses individual PATCH semantics … A no-op… | PASS | probes test_moves_under_policies (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-71 | Per-move expected_revision is optional and follows PATCH validation and stale-revisio… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-72 | failure leaves every booking unchanged … A failed batch or replay changes no revision… | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-73 | Each affected series revision increases once, and each changed series occurrence beco… | PASS | probes test_series_exceptions_and_revision (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-80 | A stage-3 service must accept exports produced by the same team's stage-1 or stage-2 … | PASS | probes test_s3_compat (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-81 | Existing confirmation links, sessions and original booking retries remain valid. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-82 | Adoption must work on reservations imported this way. | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |
| S3-83 | Failed keys reusable and a different body gives 409 after import (carried S1-78) | PASS | probes same (101/101 on 840eef4); supplied S3 7/7; inspector api.py (round 1, same src) |

Stage-1 and stage-2 clauses: PASS. Evidence: probes 101/101, supplied S1 120/120 and S2 25/25, and the browser flows above. S2-57 under a policy now passes (F1).

## Rulings
The round-1 rulings on the builder's readings (a)–(h) stand: all accepted, none blocks.
The finisher's decision to leave the ticket's re-read of the booking (6248726) out of stage 3 is correct. It belongs to stage-4 replans, and rule 4 forbids later-stage work.

## Observations (not blocking)
- O1. At 375 px the 2-seat Window tile still shows seat dots without the "N seats" text. The count is in the aria-label and on wider screens.
- O2. The examiner's probe for F1 is not yet in the stage-3 probe set (seal unchanged). It should be carried into stage 4.
