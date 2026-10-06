# Stage 2 clause register: online booking and combined tables

Source: `tablekeeper/spec/stage-2.md`. stage-1.md still applies in full. Written by examiner from the specification alone.
Families: as in the stage-1 register (BEH, ERR, ORD, AON, SIM, REP, TIME, LIM, COMPAT, BEST, PRES).
Compatibility probe export source: tag `stage-1-frozen` (fa79f76) run as TK_S1_URL.
Probe files: `test_s2_api.py`, `test_s2_ui.py`, `test_s2_compat.py`. The stage-1 probe files are carried unchanged.

## Carried forward from stage 1 (apply to every new entry point)

| id | carried clause | new entry points | probe |
|---|---|---|---|
| S2-C1 | S1-13/14/15/16: error body; 400 for wrong JSON types; 422 for missing fields and bad values | `table_ids` on POST/PATCH/moves: a string where an array is expected gives 400 malformed_request; `[]` gives 422 (RULING: an empty set is a bad value, not a wrong type); a `party_size` string gives 422 | test_s2_api::test_combo_errors |
| S2-C2 | S1-30..35: idempotency (replay, key reuse, missing key) | bodies with `table_ids`. "Same body" means the same JSON value, so array order counts: `["w_2","w_1"]` after `["w_1","w_2"]` on the same key gives 409 idempotency_key_reuse (RULING from §7's "same JSON value") | test_idempotency_with_table_ids |
| S2-C3 | S1-56/60/69: other people's bookings give 404 | PATCH with table_ids on a foreign reference gives 404 | test_patch_table_ids |
| S2-C4 | S1-66/90: a failed write changes nothing | PATCH and moves with table_ids: the record and both tables stay unchanged after a 422 or 409 | test_patch_table_ids, test_moves_with_table_ids |
| S2-C5 | S1-19/96, plus stage-2's "Concurrent requests must produce the same results as executing them one at a time in some order" | bursts mixing pairs and singles on shared tables: the winners are pairwise disjoint, and every 409 is explained by a winner | test_combo_concurrency |
| S2-C6 | S1-05 "Unknown fields … are ignored, never an error" plus S1-19 "must not produce 5xx" (inspector finding F1) | a 512-deep nested array in an ignored field: POST gives 201, moves 201, PATCH 200, signup 201. A 100000-deep body on POST, moves, PATCH, signup, login and import: always < 500, and any 4xx carries the error body. RULING: depth 512 is valid JSON and must be ignored; for extreme depth only "no 5xx, error body" is required. F1 regression (lead 07:01): a depth-3000 unknown field on POST /reservations and POST /reservation-moves gives a status < 500, and any 4xx carries the error body | test_f1_deeply_nested_ignored_field, test_f1_regression_depth_3000 |
| S2-C7 | S1-97 (ruling): moves precedence by input order | [own cancelled, unknown] gives 409 reservation_cancelled; [unknown, own cancelled] gives 404; cutoff comes before combination errors | test_ruling_s1_97_moves_precedence |
| S2-C8 | all stage-1 clauses S1-01..S1-96 | the stage-1 probe files run unchanged against stage 2 | test_basics … test_reservations |

## Model

| id | quoted text | family | discriminator |
|---|---|---|---|
| S2-05 | "Each entry is an unordered pair of table ids" | BEH | `["w_2","w_1"]` is accepted for the pair declared as `["w_1","w_2"]`. [test_combo_booking_and_shape] |
| S2-06 | "A pair not listed cannot be combined, whatever the table sizes are. Combining is not transitive" | ERR | w_1+w_2 and w_3+w_2 are declared, so `[w_1,w_3]` gives 422 combination_not_allowed. [test_combo_errors] |
| S2-07 | "A combination's capacity is the sum of its tables' capacities." | BEH | the capacity in options is the sum; party 7 on a pair of capacity 6 gives 422 party_exceeds_capacity. [api] |
| S2-08 | "Seeded reservations are confirmed unless they carry a status of cancelled" | BEH | a seeded cancelled booking shows status cancelled and does not block its table. [test_seeded_table_ids_and_status] |
| S2-09 | "… may hold either table_id or table_ids" | BEH | a seeded pair blocks both tables; its view has no `table_id`. [same] |

## API

| id | quoted text | family | discriminator |
|---|---|---|---|
| S2-12 | "available_table_ids stays exactly as it was — single tables only" | COMPAT | at party 5 it is `[w_4]` even though pairs fit. [test_available_options_basic] |
| S2-13 | "available_options lists every single table and every declared pair with capacity >= party_size and no overlapping confirmed reservation on any member." | BEH, BEST | compared with the reference model on every slot × party sizes 1..9 × 2 days after 6 mixed bookings. [test_options_reference_model] |
| S2-14 | "Singles first in fixture order, then pairs in combinable order. table_ids within a pair is in combinable order." | ORD, PRES | declared `["w_3","w_2"]` and `["w_4","w_1"]` must appear exactly in that order (a careless implementation sorts them). [basic] |
| S2-15 | "table_id is still accepted and means a set of one." | COMPAT | `table_id` gives table_ids `[id]`. [shape] |
| S2-16 | "Sending both is 422 validation_failed." | ERR | POST and PATCH. [errors, patch] |
| S2-17 | "Responses always carry table_ids. They also carry table_id when the set has exactly one member, and omit it otherwise." | PRES | checked on POST, GET, the list, PATCH and moves results. [shape, patch, moves] |
| S2-18 | "The booking occupies both tables for its full duration." | BEH | after a pair at 19:00 (90 min), a single on either member at 19:30 or 20:00 gives 409; at 20:30 gives 201. [shape] |
| S2-19 | "The pair is not in combinable → 422 combination_not_allowed" | ERR | [errors] |
| S2-20 | "More than two tables → 422 combination_not_allowed" | ERR, LIM | three tables give 422 combination_not_allowed. [errors] |
| S2-21 | "Any table in the set is taken for an overlapping interval → 409 table_unavailable" | ERR | [shape, patch] |
| S2-22 | "Duplicate table id in the set → 422 validation_failed" | ERR | `[w_1,w_1]`. [errors, patch] |
| S2-23 | "Existing single-table request formats remain supported." | COMPAT | [shape] |
| S2-24 | "Cancelling frees every table in the set." | BEH | [test_cancel_frees_all] |
| S2-25 | "PATCH … accepts table_ids under the same rules." | BEH, ERR | change single→pair→pair; every error code; the record is unchanged after each refusal. [test_patch_table_ids] |
| S2-26 | (S1-65 carried) release the old tables and reserve the new ones together | AON | a pair moved to another pair sharing w_2 gives 200. [patch] |
| S2-28 | "Atomic reservation moves … also accept table_ids per move. No table may belong to overlapping resulting bookings." | BEH, AON | swap a pair with a single in one batch gives 201; a conflict with an unchanged listed booking gives 409 and nothing changes; a replay gives 200 identical. [test_moves_with_table_ids] |
| S2-41 | "Concurrent requests must produce the same results as executing them one at a time in some order, and the requirements above hold at every read." | SIM | 50-request burst of pairs and singles. [test_combo_concurrency] |

## Screens

| id | quoted text | family | discriminator |
|---|---|---|---|
| S2-01 | "/ /signup /login /lookup … A screen route returns HTML" | PRES | 200 with text/html. [test_routes_are_html] |
| S2-50 | signup/login testids; "auth-error … Present only when there is one" | BEH | auth-error is absent before a wrong login and visible after. [test_signup_login_logout] |
| S2-51 | "current-user — Visible on every screen when signed in. Text contains the display name" | BEH, RULING | after signup, navigating to all four routes by URL still shows current-user (RULING: sign-in must survive navigation between the required screens). [same] |
| S2-52 | "logout-button" | BEH | after logout, current-user is absent. [same] |
| S2-55 | "slot-{table_id}-{HH:MM} — One cell per table per slot" | PRES | one cell per fixture table (including tables too small for the party) per API slot. [test_grid_matches_api] |
| S2-56 | "A cell is true exactly when its table_id is in that slot's available_table_ids … for the party size that was searched" | BEH | every cell compared with the API for parties 2 and 5. [same] |
| S2-57 | "slot-{t_a}+{t_b}-{HH:MM} … Ids in combinable order … shown when a declared pair is available" | PRES, ORD | a cell exists for each 2-table option; no `slot-w_2+w_1-*` and no `slot-w_1+w_3-*`. [same] |
| S2-58 | "no-slots — Shown instead of the grid when the day has no slots" | BEH | a closed Wednesday shows no-slots and zero slot cells. [same] |
| S2-59 | "clicking an available cell while signed out shows auth-error or navigates to /login" | BEH | no booking is created. [test_signed_out_click] |
| S2-60 | "booking-summary — Text contains the table label and the local start time" / "must name every table in the selection" | PRES | "Kamin" and "19:00"; for a pair, both labels. [flow, combination] |
| S2-61 | "booking-party-size — pre-filled from the search" | BEH | value "2". [flow] |
| S2-62 | "confirmation-reference — Text is exactly the reference"; "confirmation-details — restaurant name, table label and local start time" | PRES | regex on the text alone; "Zur Laterne", "Kamin", "19:00". [flow] |
| S2-63 | "Keep the booking form on screen after success. Submitting it again without changing a field must return the same confirmation-reference, without booking-error or another booking." | REP, RULING | the second submit sends the same key and body (RULING: §7 retry, and "the browser must not manufacture a successful result from cached data"); the same reference; one reservation in the API. [flow] |
| S2-64 | "Changing a field makes the next submission a new booking request." | REP | after changing the party size, the next POST is not answered 409 idempotency_key_reuse (it is a new request: 201 or a 409 table_unavailable shown as booking-error). [flow] |
| S2-31 | "If another client takes a table after the form opens, a 409 … shows booking-error and refreshes availability. Preserve the selected form and its inputs … Do not show a confirmation" | BEH | the edited party size "5" is kept; the cell becomes data-available="false"; no confirmation. [test_conflict_shows_error_and_refreshes] |
| S2-34 | "If a booking response is lost, including after the booking commits, show nonempty booking-uncertain text, without booking-error or a new confirmation. The unchanged form must retry with the same idempotency key and body. A successful retry removes the uncertainty/error elements and shows the original reference." | REP | Playwright commits the request, then aborts the response; the retry carries the same key and body, shows the committed reference, and leaves one reservation. [test_lost_response_then_retry] |
| S2-30 | "If search A starts before search B but finishes after it, the grid, table labels and booking form must describe B." | ORD, SIM | A's availability (r_lat) is delayed 2 s, B is r_gar; after A lands there are only g_a cells, and the booking summary says "Linde". [test_out_of_order_search] |
| S2-70 | combination cells, "confirmation-tables", "reservation-tables" contain every table label | PRES | Fenster and Kamin on the confirmation and on lookup. [test_combination_booking_ui] |
| S2-67 | lookup: "reservation-status — exactly confirmed or cancelled"; "reservation-cancel-button — Absent once cancelled"; "reservation-error — not found, or when a cancel is refused" | BEH, ERR | NOPE99 gives reservation-error; cancel, then the status is cancelled and the button is gone; a cancel within cutoff gives reservation-error and the status stays confirmed. [test_lookup_and_cancel] |
| S2-45 | "usable at a 375 CSS-pixel viewport … without horizontal page scrolling" | PRES, LIM | scrollWidth ≤ 375 on every route, after a search, and with the booking form open. [test_no_horizontal_scroll_375] |

## Upgrade / compatibility

| id | quoted text | family | discriminator |
|---|---|---|---|
| S2-35 | "A stage-2 service must accept an export produced by the same team's stage-1 service." | COMPAT, RULING | an export from the frozen stage-1 service imports into stage 2 with 204. Tokens are valid, login works, and each record keeps every stage-1 field. Replays (POST and moves) return the original stage-1 response; RULING: the only allowed difference is an added `table_ids` = `[table_id]`, because §7 requires the original response while stage 2 adds `table_ids`. Failed keys are reusable; reuse with a different body gives 409; availability gains singles-only options. [test_s2_compat] |
| S2-38 | "A browser signed in before that export/import upgrade must remain signed in afterwards … A booking whose response was lost before export remains retryable after import … the UI must recover the original confirmation … The form and pending retry identity must survive the upgrade." | COMPAT, REP | in one page: lose a committed response, export, reset, import, retry: the original reference is shown, current-user is still shown, and lookup finds the booking as confirmed. [test_upgrade_keeps_session_and_retry] |

## Not probed (judgement, not mechanically checkable, or ambiguous)
Visual-quality wording (warm character, contrast and focus quality) is left to the inspector's review. Not probed: the precedence between an unknown table inside `table_ids` and combination_not_allowed, and a pair across two restaurants.
