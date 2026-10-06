# Stage 3 clause register: policies, history, recurring reservations

Source: `tablekeeper/spec/stage-3.md`. stage-1.md and stage-2.md still apply. Written by examiner from the specification alone.
Families: BEH, ERR, ORD, AON, SIM, REP, TIME, LIM, COMPAT, BEST, PRES (as in stage 1). Probe files: `test_s3_explain_history.py`,
`test_s3_policies.py`, `test_s3_series.py`, `test_s3_compat.py`. Carried unchanged: the stage-1 files, `test_s2_api.py` and `test_s2_ui.py`.

## Carried forward (cross-cutting, against every new entry point)

| id | carried clause | new entry points | probe |
|---|---|---|---|
| S3-C1 | S1-13/14: error body; 400 for an unparseable or non-object body and for wrong JSON types | /series and /restaurants/{id}/policies: `{` and `[1]` give 400; `anchor_reference: 5` gives 400 | test_new_paths_f1_and_errors |
| S3-C2 | F1 / S2-C6: no 5xx from deeply nested unknown fields | a depth-3000 unknown field on /series and /policies gives < 500 | same |
| S3-C3 | S1-30..37 idempotency: missing key 400, length 256 gives 422, replay 200 identical, reuse 409, a failed key is reusable, a concurrent identical burst gives one 201 | policies and series | test_publish_permissions_and_versions, test_adopt_errors, test_adopt_atomic_and_first_failure, test_series_burst_and_policy_burst |
| S3-C4 | S1-20/27 auth: 401 without a token | POST /series, POST /policies | test_adopt_errors, test_publish_permissions_and_versions |
| S3-C5 | S1-56 owner-only 404 | history, decision, GET /series | test_history_and_decision_visibility, test_adopt_basic |
| S3-C6 | S1-90/S2-28 all-or-nothing | series adoption; moves under policies; failed amendments leave revision, history and terms unchanged | test_adopt_atomic_and_first_failure, test_moves_under_policies, test_amendment_reselects_policy |
| S3-C7 | S1-96/S2-41 serialisability | 20 concurrent policy publications get versions exactly 1..20; concurrent adoption of one anchor gives one 201 and the rest 409 already_in_series; concurrent PATCHes with one expected_revision give at most one real change | test_series_burst_and_policy_burst, test_expected_revision |
| S3-C8 | all S1-* and S2-* clauses (stage 2 must remain intact) | the carried probe files run unchanged | test_basics … test_s2_ui |

## Availability explanations

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-01 | "Every table of the restaurant appears exactly once, available or not, in fixture order" | PRES, ORD | [test_explain_shape_and_reference] |
| S3-02 | "Both rules are reported for every table, in the order above … No rule may be omitted." | PRES | rules equal `[capacity, no_overlap]` with holds values from the reference model, for parties 1..7. [same] |
| S3-03 | "available is true exactly when both hold, and the table_ids whose available is true are exactly available_table_ids, in the same order." | BEH, BEST | compared on every slot. [same] |
| S3-04 | "a table excluded by both reports both false" | BEH | a booked table that is too small. [same] |
| S3-05 | "Without it the response keeps stage 1's shape — no explanation fields appear." | COMPAT | no slot has an `explain` key; the keys are a subset of the stage-1/2 keys. [same] |
| S3-06 | "Its only accepted value is true; any other value, including false, 1 and the empty string, is 422" | ERR | false, 1, "", TRUE, True, yes all give 422. [test_explain_validation_and_closed] |
| S3-07 | "A closed day still returns slots: [] … a slot with no available table still appears — now with a full explain" | BEH | [same] |
| S3-08 | "With explain=true, each table explanation additionally identifies its policy_version." "Published policies can change the slot values." | BEH | after a policy with new capacities, the explanations carry that version and the new capacity results. [test_explain_uses_policy] |

## History

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-10 | "seq starts at 1 and increases by exactly 1 … returned in seq order, which is also at order" | ORD | [test_history_rules] |
| S3-11 | "created names all three fields, each with from: null" (order table_id, starts_at_local, party_size) | PRES | [same] |
| S3-12 | "changed names only the fields that actually changed, in the order table_id, starts_at_local, party_size" | PRES, ORD | a PATCH sends the fields out of order; the history records starts_at_local then party_size only. [same] |
| S3-13 | "A PATCH that sets a field to the value it already has … still succeeds, and it records no entry at all." | REP | the revision is unchanged too. [same] |
| S3-14 | "cancelled carries an empty changes, and nothing follows it" | BEH | a repeat cancel adds nothing. [same] |
| S3-15 | "Replaying an idempotent POST /reservations records nothing" | REP | [same] |
| S3-16 | "Only its owner may read it; anyone else, signed in or not, gets the same 404" / "History and decision return 404 even without authentication" | ERR, RULING | another user, a manager, no token and a bogus token all give 404 (not 401). [test_history_and_decision_visibility] |
| S3-17 | "Each history entry additionally carries the reservation's resulting revision and complete accepted_terms. Old entries never acquire newer terms." | COMPAT | entry terms TERMS0 then the new policy's terms. [test_amendment_reselects_policy] |

## Policies

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-20 | "Only these users may publish policies. Unknown restaurant is 404; an authenticated non-manager is 403 forbidden; no token is 401." | ERR | a manager of another restaurant gets 403 too; manager_user_ids defaults to []. [test_publish_permissions_and_versions] |
| S3-21 | "requires an idempotency key, with stage 1's replay rules" | REP | [same] |
| S3-22 | "Returns 201 with the supplied policy plus policy_version, an integer starting at 1 and increasing by one per restaurant. Failed writes and replays allocate no version." | BEH | after 25 invalid policies the next version is still 1; a replay allocates nothing. [test_policy_validation_no_version] |
| S3-23 | "GET … is public and returns {policies: [...]} in publication order, omitting policy 0. The ordinary restaurant detail still returns its original fixture configuration." | PRES | [test_publish_permissions_and_versions] |
| S3-24 | "All fields above are required … grid and duration are integers 1..1440; cutoff 0..10080; booleans are not integers … no duplicate weekdays … capacities names exactly the restaurant's table ids with integer capacities 1..100." | ERR, LIM | each field missing, every boundary on both sides, booleans, 2.5, missing or extra table ids, duplicate weekday, opens ≥ closes, bad weekday: all give 422. The boundaries 1440 / 0 / 10080 are accepted. [test_policy_validation_no_version] |
| S3-25 | "Invalid policy is 422 validation_failed, with no version or state change." | AON | [same] |
| S3-26 | "For a booking's local start date, choose the greatest effective_from not later than that date; ties choose the greatest policy_version." | BEST, TIME | publication order differs from effective order; a tie on the same date is resolved by the higher version. [test_policy_selection] |
| S3-27 | "Policy 0 is the original fixture's rules and applies before any published policy." | BEH | a booking before the earliest effective date gets TERMS0. [same] |
| S3-28 | "A policy publication does not change existing bookings, their end times, or their history." | COMPAT | [same] |
| S3-29 | "Availability and booking decisions use the selected policy, not that detail." | BEH | the grid uses the new slot length (60) and capacity (p_1 = 3). [same] |

## Accepted terms, revision, decision

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-33 | "Every reservation response gains revision (1 at creation) and accepted_terms … a snapshot of the entire selected policy, excluding effective_from." | PRES | exact equality with the policy snapshot. [policy_selection, history] |
| S3-34 | "A real diner amendment … checks the old accepted cutoff first, then validates all resulting fields against the policy applicable to the resulting start date. It atomically replaces accepted terms and end time and increments revision once." | BEH, ORD | changing only the date gives party_exceeds_capacity under the new date's capacity; the record is unchanged; a valid change gets the new terms and a 60-minute end. [test_amendment_reselects_policy] |
| S3-35 | "Failed amendments change nothing." | AON | [same] |
| S3-36 | "Cancel checks the accepted cutoff, against the current start." | TIME, RULING | a later policy with cutoff 0 does not relax a booking accepted with cutoff 120 (409); a booking accepted under cutoff 0 can be cancelled 60 minutes before its start. [test_accepted_cutoff_rules] |
| S3-37 | "A no-op amendment … still requires a confirmed, editable booking." | ERR | a no-op within the cutoff gives 409 cutoff_passed; a no-op on a cancelled booking gives 409 reservation_cancelled. [same] |
| S3-38 | "expected_revision. A positive integer differing from the current revision gives 409 stale_revision before cutoff/validation; invalid type/range gives 422." | ERR, ORD | stale + party 0 gives stale_revision; stale on a booking past its cutoff gives stale_revision; 0, -1, "1", true, 1.5 give 422. [test_expected_revision, test_accepted_cutoff_rules] |
| S3-39 | "Two concurrent amendments using one revision: at most one real change succeeds." / "Cancel increments revision once; repeated cancel does not." | SIM | a burst of 10 gives ≤ 1 real change and the rest stale_revision; revision and history agree. [test_expected_revision, test_history_rules] |
| S3-40 | "GET /reservations/{reference}/decision returns {reference, revision, accepted_terms} … including after cancellation" | PRES | [test_history_and_decision_visibility] |
| S3-41 | "Responses to old idempotency keys remain the original response, including the original revision and terms." | REP | [test_history_rules] |

## Series

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-45 | "Occurrence zero is the anchor itself: its reference, identity, revision, terms, history, timestamps … remain unchanged." | COMPAT | [test_adopt_basic] |
| S3-46 | "Unknown or another owner's anchor gives 404; cancelled gives 409 reservation_cancelled; already adopted gives 409 already_in_series … No token gives 401." | ERR, RULING | adopting any occurrence of an existing series also gives already_in_series. An anchor inside its cutoff gives 409 cutoff_passed (RULING: "satisfy its accepted cancellation cutoff" uses the ordinary cutoff code). [test_adopt_errors, test_adopt_basic] |
| S3-47 | "count is an integer 2..12 …; interval_weeks 1..4. Invalid values, including booleans, give 422" | LIM, ERR | 1, 13, true, 2.5, null, missing; 0, 5, true. count 12 with interval 4 is accepted. [test_adopt_errors] |
| S3-48 | "Occurrence i starts on the anchor's local calendar date plus i × interval_weeks × 7 days, at the same local clock time." | TIME | interval 2 gives days 0/14/28/42. [test_series_exceptions_and_revision] |
| S3-49 | "Each generated occurrence independently selects its date's policy" | BEH | occurrence 2 gets the later policy's terms. [test_adopt_basic] |
| S3-50 | "Occurrences appear in ordinary reservation lists, occupy tables, and have ordinary histories." / "GET /series … only the owner … another user or no token gives 404" / replay returns the original | BEH, REP | [test_adopt_basic] |
| S3-51 | "A real individual PATCH permanently marks that occurrence as exception: true and increments the series revision once; a no-op or failure changes neither." | BEH | patching back to the original value keeps exception true. [test_series_exceptions_and_revision] |
| S3-52 | "Cancellation increments the series revision once … not … an exception; repeated cancel does nothing." | BEH | [same] |
| S3-53 | "Cancelling the anchor does not cancel its siblings." | BEH | [same] |
| S3-54 | "Replays return the original series response, even after later changes, and change no counter." | REP | [same] |
| S3-55 | "No partial series, reservations, histories, counters or idempotency claim survive failure." | AON | after a failure there is no new reservation, the anchor is unchanged, and the same key works later. [test_adopt_atomic_and_first_failure] |
| S3-56 | "The first failing occurrence in index order determines the ordinary booking error." | ORD | occurrence 2 occupied (409) and occurrence 3 closed by policy (422): the response is 409; after the blocker is freed it is 422. [same] |
| S3-57 | "A nonexistent local time rejects the entire adoption with invalid_local_time; repeated times use stage 1's first occurrence rule." | TIME | Berlin 2027-03-28 02:30 gives 422; 2026-10-25 02:30 is +02:00 and ends 03:00+01:00. [test_adopt_dst] |
| S3-58 | "Generated occurrences use the anchor's party size and table selection." | BEH | a pair anchor produces pair occurrences. [test_combined_anchor_series] |

## Combined-table history; collective moves

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-60 | "For a creation of a pair, replace the table_id change by table_ids (from null to the pair)." / "Table-set order is the declared combination order." | PRES | input `["p_1","p_2"]` with declared `["p_2","p_1"]` is recorded as `["p_2","p_1"]`. [test_combined_history] |
| S3-61 | "A reversed input pair names the same set and is not an amendment on its own." | REP | the revision stays 1 and no entry is added. [same] |
| S3-62 | "For a change involving a pair, use table_ids (complete before/after lists)" / single-to-single keeps table_id | PRES | [same] |
| S3-63 | "capacity is the sum of the selected policy's capacities" | BEH | [same] |
| S3-70 | "Each real change in POST /reservation-moves uses individual PATCH semantics … A no-op retains its terms and history." | BEH | [test_moves_under_policies] |
| S3-71 | "Per-move expected_revision is optional and follows PATCH validation and stale-revision rules." | ERR | [same] |
| S3-72 | "failure leaves every booking unchanged … A failed batch or replay changes no revisions, histories or exception flags." | AON, REP | [same] |
| S3-73 | "Each affected series revision increases once, and each changed series occurrence becomes a permanent diner exception." | BEH | two occurrences in one batch raise the series revision by exactly 1. [test_series_exceptions_and_revision] |

## Compatibility

| id | quoted text | family | discriminator |
|---|---|---|---|
| S3-80 | "A stage-3 service must accept exports produced by the same team's stage-1 or stage-2 service." | COMPAT | exports from stage-1-frozen (TK_S1_URL) and stage-2-frozen (TK_S2_URL) import with 204. [test_s3_compat] |
| S3-81 | "Existing confirmation links, sessions and original booking retries remain valid." | COMPAT, RULING | the token works; a replay keeps every original field. RULING: only `table_ids`, `revision` (= 1) and `accepted_terms` may be added to a pre-stage-3 record or receipt; an imported booking is treated like a seeded one (revision 1, policy 0). [same] |
| S3-82 | "Adoption must work on reservations imported this way." | COMPAT | an imported booking anchors a series as occurrence 0; history and decision answer 200. [same] |
| S3-83 | Failed keys reusable and a different body gives 409 after import (carried S1-78) | COMPAT | [same] |

## Not probed
"Adoption increments the restaurant revision once": the restaurant revision is not exposed by any endpoint the spec names. Strings for integer policy fields (400 vs 422) are not probed; booleans are (422, stated explicitly).
