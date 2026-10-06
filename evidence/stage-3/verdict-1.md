# Stage 3: verdict, round 1

**REJECT**: revision `bc172db4482789aae8b7f8895fe10ea93c6e7a95` (main), folder `stage-3/`, round 1.
There is one blocking failure, on the **surface** (owner: finisher). The API, the checks and the probes all pass.
The finisher's later UI-only commits `9c2100c`/`a8900ab` already fix F1. I ran everything below against a8900ab as well, and it passes, so round 2 can be a quick re-run on a8900ab.
Inspector, 2026-10-06.

## Evidence

| Step | bc172db | a8900ab (pre-check only) |
|---|---|---|
| Clean copies | `/tmp/insp-s3r1-lHpZ` (stage-3 plus frozen stage-1/stage-2 from their tags) | `/tmp/insp-s3r1a-U1PQ`; differs from bc172db only under `stage-3/ui/` (and evidence/) |
| Rule 2: stage-1 and stage-2 frozen | `git diff stage-1-frozen bc172db -- stage-1` and `stage-2-frozen … -- stage-2` are both empty | same |
| `check run … 3 isolated` | S1 **120/120**, S2 **25/25**, S3 **7/7**. Stage-4 probe **FAILS**. "claimed stage: 3 on the shipped checks" (checks/1006-071629-16340) | the same counts and line (checks/1006-072030-18201) |
| `check build … stage-3 3` | S1 pass, S3 pass. The S2 error is the upgrade test, which needs `run` mode (same harness limit as stage 2) | not run |
| `check repo` | only the 3 complaints that may be ignored | not run |
| Rules 4, 5, 6 | No replans, closures, plan apply, series amend, or `restaurant_revision` in any response. Healthy under 1 s at 2 vCPU / 2 GiB. `/health` works with `--network none`. No credentials | same code |
| Examiner probes | Seal `c19fc8cf…46a6` **matches**. **101/101 passed**, 0 skipped, with TK_S1_URL and TK_S2_URL pointing at containers built from the frozen tags | **101/101 passed** |

## Failure (blocking)

### F1: under a published policy, the grid hides a joined-table option that /availability offers
- **Clauses:**
  - S3-29: "Availability and booking decisions use the selected policy, not that detail".
  - S2-57 (stage-2 §UI): combination cells are "shown when a declared pair is available for the searched party size". The cell must carry data-available like a single cell.
  - Stage-3 "The availability grid continues to follow the stage-2 rules."
- **Smallest input:**
  - Fixture: restaurant `r` (Europe/Berlin), open 17:00–23:00 every day. Tables t_1 (capacity 2), t_2 (capacity 4), t_3 (capacity 4). `combinable: [["t_2","t_1"]]`, `manager_user_ids: ["u_mgr"]`.
  - The manager publishes `{effective_from:"2027-03-01", slot_minutes:45, reservation_duration_minutes:90, cancellation_cutoff_minutes:120, opening_hours: all days 17:00–22:00, capacities:{t_1:6,t_2:6,t_3:1}}`.
  - On `/`, search date 2027-03-05, party 10.
- **What happened:** `GET /availability` offers `{"table_ids":["t_2","t_1"],"capacity":12}` in all 5 slots (17:00, 17:45 … 20:00). The grid draws **no** `slot-t_2+t_1-HH:MM` cell and labels every time "Fully booked", so the diner cannot book the option the server offers. The slot times do follow the policy, and every single-table `data-available` is correct. The UI decides which pairs to draw, and the "N seats" text, from the restaurant detail's fixture capacities (2+4=6 < 10), not from the selected policy. The tile text is also wrong: "Window 2 seats", "Bar 4 seats" against the policy's 6 and 1.
- **What the clause requires:** a `slot-t_2+t_1-17:00` (etc.) cell with `data-available="true"`, because the pair is available for party 10 under the selected policy.
- **Already fixed at a8900ab:** same input, 0 mismatches between the grid and `available_options` for parties 10, 5 and 1. The pair tile shows "12 seats · Open", Window shows 6 seats and Bar shows 1. Captures: `/tmp/insp-s3r1-attack/{bc172db,a8900ab}-p10.png`.

## Own attack, API (`/tmp/insp-s3r1-attack/api.py`, `compat.py`): all PASS
- **Policy publication:**
  - Refusals: non-manager → 403. No token → 401. Unknown restaurant → 404. No key → 400.
  - Invalid → 422 in 11 cases (bool or string slot, 1441, cutoff 10081, duration 0, 2027-02-30, capacities missing or extra a table, capacity 101, duplicate weekday, missing field), with no version used.
  - Replay → 200 with the same version. Same key with a different body → 409.
  - `GET /policies` lists them in publication order. The restaurant detail is the fixture without manager_user_ids.
- **Selection:** published out of order, v1 (03-01), v2 (02-01), then v3 (03-01, a tie). `explain` reports policy_version 0, 2 and 3 for 01-15, 02-15 and 03-05, and v3 wins the tie. On every slot of 03-05, `explain` covers 3 tables, each with [capacity, no_overlap], and the available ids equal `available_table_ids`. explain=`false`, `1` or empty → 422. Without explain the stage-1 shape is kept.
- **Amendment crossing into another policy:**
  - Into v2's 60-minute grid → not_on_slot_grid. Into v2's capacity 2 with party 4 → party_exceeds_capacity.
  - A valid cross → revision 2 under terms v3, with ends_at from v3's duration.
  - A no-op with identical values → no entry and no revision.
  - History has 2 entries, in the restaurant's offset.
- **expected_revision:** `"1"` and 0 → 422. Stale → 409. 10 concurrent PATCHes with expected_revision=2 → exactly 1 × 200 and 9 × 409.
- **Owner-only reads:** history, decision and series return 404 to another user, with no token and with a bad token.
- **Cancel:** cancel → revision 2. Repeated cancel → still 2, and history has 2 entries.
- **Pair history:**
  - Created as `table_ids` null → [t_2,t_1], in declared order.
  - The reversed pair alone is a no-op.
  - Pair → single is logged as `table_ids` [t_2,t_1] → [t_3]. Single → single is logged as `table_id`.
- **Series:**
  - Each occurrence picks its own date's policy: weeks 0–3 under policy 0, weeks 4–7 under v2.
  - A capacity failure partway through → 422, with nothing partial, and the key can be reused.
  - A DST gap (Berlin 2027-03-28 02:30) → 422 invalid_local_time, with nothing partial.
  - A fall-back occurrence → 201.
  - Refusals: already_in_series → 409. count 1/13, interval 5, count `true` → 422. Anchor 5 → 400.
  - A PATCH marks the occurrence as an exception, a repeat no-op adds nothing, a cancel does not mark it, and the series revision is 3.
  - A replay after those changes → the original response.
  - Moves: a stale per-move expected_revision → 409. A real change plus a no-op → the series revision is 4, only the changed occurrence becomes an exception, and only it gets revision 2.
- **Compatibility:** stage-1 and stage-2 (pair) exports import into stage 3 → revision 1 under policy 0 with one created entry. The original key replays the identical body. Tokens and logins still work. Adopting the imported booking as a series anchor → 201.

## Own attack, browser (a8900ab, real API, 375/768/1280)
Every stage-2 flow still holds at all three widths, with no sideways scrolling and visible focus:
- lost response twice, then the original reference
- 409 keeps the edited form and refreshes the grid
- unchanged resubmit gives the same reference
- auth-error when signed out, and current-user on every route
- pair labels in the summary, the ticket and the lookup
- cancel on the lookup screen

The confirmation now also shows the end time.

## Clause rows: stage 3 (69 clauses in evidence/stage-3/clauses.md)

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S3-C1 | S1-13/14: error body; 400 for an unparseable or non-object body and for wrong JSON ty… | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C2 | F1 / S2-C6: no 5xx from deeply nested unknown fields | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C3 | S1-30..37 idempotency: missing key 400, length 256 gives 422, replay 200 identical, r… | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C4 | S1-20/27 auth: 401 without a token | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C5 | S1-56 owner-only 404 | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C6 | S1-90/S2-28 all-or-nothing | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C7 | S1-96/S2-41 serialisability | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-C8 | all S1-* and S2-* clauses (stage 2 must remain intact) | PASS | probes see register; supplied S3 7/7; inspector api.py |
| S3-01 | Every table of the restaurant appears exactly once, available or not, in fixture orde… | PASS | probes test_explain_shape_and_reference; supplied S3 7/7; inspector api.py |
| S3-02 | Both rules are reported for every table, in the order above … No rule may be omitted. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-03 | available is true exactly when both hold, and the table_ids whose available is true a… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-04 | a table excluded by both reports both false | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-05 | Without it the response keeps stage 1's shape — no explanation fields appear. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-06 | Its only accepted value is true; any other value, including false, 1 and the empty st… | PASS | probes test_explain_validation_and_closed; supplied S3 7/7; inspector api.py |
| S3-07 | A closed day still returns slots: [] … a slot with no available table still appears —… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-08 | With explain=true, each table explanation additionally identifies its policy_version.… | PASS | probes test_explain_uses_policy; supplied S3 7/7; inspector api.py |
| S3-10 | seq starts at 1 and increases by exactly 1 … returned in seq order, which is also at … | PASS | probes test_history_rules; supplied S3 7/7; inspector api.py |
| S3-11 | created names all three fields, each with from: null" (order table_id, starts_at_loca… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-12 | changed names only the fields that actually changed, in the order table_id, starts_at… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-13 | A PATCH that sets a field to the value it already has … still succeeds, and it record… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-14 | cancelled carries an empty changes, and nothing follows it | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-15 | Replaying an idempotent POST /reservations records nothing | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-16 | Only its owner may read it; anyone else, signed in or not, gets the same 404" / "Hist… | PASS | probes test_history_and_decision_visibility; supplied S3 7/7; inspector api.py |
| S3-17 | Each history entry additionally carries the reservation's resulting revision and comp… | PASS | probes test_amendment_reselects_policy; supplied S3 7/7; inspector api.py |
| S3-20 | Only these users may publish policies. Unknown restaurant is 404; an authenticated no… | PASS | probes test_publish_permissions_and_versions; supplied S3 7/7; inspector api.py |
| S3-21 | requires an idempotency key, with stage 1's replay rules | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-22 | Returns 201 with the supplied policy plus policy_version, an integer starting at 1 an… | PASS | probes test_policy_validation_no_version; supplied S3 7/7; inspector api.py |
| S3-23 | GET … is public and returns {policies: [...]} in publication order, omitting policy 0… | PASS | probes test_publish_permissions_and_versions; supplied S3 7/7; inspector api.py |
| S3-24 | All fields above are required … grid and duration are integers 1..1440; cutoff 0..100… | PASS | probes test_policy_validation_no_version; supplied S3 7/7; inspector api.py |
| S3-25 | Invalid policy is 422 validation_failed, with no version or state change. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-26 | For a booking's local start date, choose the greatest effective_from not later than t… | PASS | probes test_policy_selection; supplied S3 7/7; inspector api.py |
| S3-27 | Policy 0 is the original fixture's rules and applies before any published policy. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-28 | A policy publication does not change existing bookings, their end times, or their his… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-29 | Availability and booking decisions use the selected policy, not that detail. | **FAIL (surface)** | API PASS (probes, api.py). Grid FAIL at bc172db: F1 below; PASS at a8900ab |
| S3-33 | Every reservation response gains revision (1 at creation) and accepted_terms … a snap… | PASS | probes policy_selection, history; supplied S3 7/7; inspector api.py |
| S3-34 | A real diner amendment … checks the old accepted cutoff first, then validates all res… | PASS | probes test_amendment_reselects_policy; supplied S3 7/7; inspector api.py |
| S3-35 | Failed amendments change nothing. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-36 | Cancel checks the accepted cutoff, against the current start. | PASS | probes test_accepted_cutoff_rules; supplied S3 7/7; inspector api.py |
| S3-37 | A no-op amendment … still requires a confirmed, editable booking. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-38 | expected_revision. A positive integer differing from the current revision gives 409 s… | PASS | probes test_expected_revision, test_accepted_cutoff_rules; supplied S3 7/7; inspector api.py |
| S3-39 | Two concurrent amendments using one revision: at most one real change succeeds." / "C… | PASS | probes test_expected_revision, test_history_rules; supplied S3 7/7; inspector api.py |
| S3-40 | GET /reservations/{reference}/decision returns {reference, revision, accepted_terms} … | PASS | probes test_history_and_decision_visibility; supplied S3 7/7; inspector api.py |
| S3-41 | Responses to old idempotency keys remain the original response, including the origina… | PASS | probes test_history_rules; supplied S3 7/7; inspector api.py |
| S3-45 | Occurrence zero is the anchor itself: its reference, identity, revision, terms, histo… | PASS | probes test_adopt_basic; supplied S3 7/7; inspector api.py |
| S3-46 | Unknown or another owner's anchor gives 404; cancelled gives 409 reservation_cancelle… | PASS | probes test_adopt_errors, test_adopt_basic; supplied S3 7/7; inspector api.py |
| S3-47 | count is an integer 2..12 …; interval_weeks 1..4. Invalid values, including booleans,… | PASS | probes test_adopt_errors; supplied S3 7/7; inspector api.py |
| S3-48 | Occurrence i starts on the anchor's local calendar date plus i × interval_weeks × 7 d… | PASS | probes test_series_exceptions_and_revision; supplied S3 7/7; inspector api.py |
| S3-49 | Each generated occurrence independently selects its date's policy | PASS | probes test_adopt_basic; supplied S3 7/7; inspector api.py |
| S3-50 | Occurrences appear in ordinary reservation lists, occupy tables, and have ordinary hi… | PASS | probes test_adopt_basic; supplied S3 7/7; inspector api.py |
| S3-51 | A real individual PATCH permanently marks that occurrence as exception: true and incr… | PASS | probes test_series_exceptions_and_revision; supplied S3 7/7; inspector api.py |
| S3-52 | Cancellation increments the series revision once … not … an exception; repeated cance… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-53 | Cancelling the anchor does not cancel its siblings. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-54 | Replays return the original series response, even after later changes, and change no … | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-55 | No partial series, reservations, histories, counters or idempotency claim survive fai… | PASS | probes test_adopt_atomic_and_first_failure; supplied S3 7/7; inspector api.py |
| S3-56 | The first failing occurrence in index order determines the ordinary booking error. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-57 | A nonexistent local time rejects the entire adoption with invalid_local_time; repeate… | PASS | probes test_adopt_dst; supplied S3 7/7; inspector api.py |
| S3-58 | Generated occurrences use the anchor's party size and table selection. | PASS | probes test_combined_anchor_series; supplied S3 7/7; inspector api.py |
| S3-60 | For a creation of a pair, replace the table_id change by table_ids (from null to the … | PASS | probes test_combined_history; supplied S3 7/7; inspector api.py |
| S3-61 | A reversed input pair names the same set and is not an amendment on its own. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-62 | For a change involving a pair, use table_ids (complete before/after lists)" / single-… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-63 | capacity is the sum of the selected policy's capacities | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-70 | Each real change in POST /reservation-moves uses individual PATCH semantics … A no-op… | PASS | probes test_moves_under_policies; supplied S3 7/7; inspector api.py |
| S3-71 | Per-move expected_revision is optional and follows PATCH validation and stale-revisio… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-72 | failure leaves every booking unchanged … A failed batch or replay changes no revision… | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-73 | Each affected series revision increases once, and each changed series occurrence beco… | PASS | probes test_series_exceptions_and_revision; supplied S3 7/7; inspector api.py |
| S3-80 | A stage-3 service must accept exports produced by the same team's stage-1 or stage-2 … | PASS | probes test_s3_compat; supplied S3 7/7; inspector api.py |
| S3-81 | Existing confirmation links, sessions and original booking retries remain valid. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-82 | Adoption must work on reservations imported this way. | PASS | probes same; supplied S3 7/7; inspector api.py |
| S3-83 | Failed keys reusable and a different body gives 409 after import (carried S1-78) | PASS | probes same; supplied S3 7/7; inspector api.py |

Stage-1 and stage-2 clauses: PASS. Evidence: the carried probes (101/101), supplied S1 120/120 and S2 25/25, and the stage-2 browser flows above. Exception: S2-57 FAILS under a published policy at bc172db (F1).

## Rulings on the builder's readings (none blocks)
(a) **A seeded or imported booking is revision 1 under policy 0, with one `created` entry at created_at; a seeded cancelled booking stays at revision 1:** accepted. The spec says "seeded bookings start at revision 1 under policy 0".
(b) **History `at` in the restaurant's offset:** accepted. RFC 3339 with an offset is all §3.4 requires. Imported entries keep their original created_at offset (+00:00), which is also valid.
(c) **PATCH order:** accepted. Note: the code checks wrong types (400) before the 404 ownership check, the reverse of the order you declared. The spec does not order these.
(d) **Policies POST order, with every field error as 422:** accepted. The spec says "Invalid policy is 422".
(e) **Series order:** accepted, and it matches the spec ("first failing occurrence in index order").
(f) **Internal, exported restaurant revision:** accepted. It is not exposed in responses, as rule 4 requires.
(g) **Detail without manager_user_ids:** accepted. The detail is the "original fixture configuration", and the managers are not shown.
(h) **Past occurrences allowed, with only the anchor's cutoff checked:** accepted. This follows §4 ("not rejected solely because its start is in the past") and the spec's anchor-only cutoff rule.

## Observations (not blocking)
- O1. At a8900ab a 1-seat table reads "1 seats" (it should be "1 seat").
- O2. The probe set passes at bc172db despite F1. Examiner: please add a probe for F1's smallest input, comparing every grid cell with `available_options` under a policy that raises capacities.
- O3. The `check build` stage-2 error is the same harness limit as in stage 2. Rely on `check run`.
