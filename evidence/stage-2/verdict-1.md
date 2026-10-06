# Stage 2: verdict, round 1

**ACCEPT**: revision `fbae59cf979ab2befbb7dec1add7d74496e74a95` (main), folder `stage-2/`, round 1.
The work order named c7275b7. The lead's ledger (07:06) amended the revision under review to fbae59c. Between the two, the only change is in `stage-2/ui/css/{base,search}.css` (the finisher's beec94c). The supplied checks were run on both. `stage-2/` at HEAD 80561c8 is identical to fbae59c.
Inspector, 2026-10-06. No blocking failures.

## Evidence

| Step | Result |
|---|---|
| Clean copies | `git archive` of c7275b7 and of fbae59c (`/tmp/insp-s2r1-K3C5`, `/tmp/insp-s2r1f-Vrb5`). Repo clone checked out at each revision for `check run` (`/tmp/insp-s2r1-repo-9Z9j`). |
| Rule 2: stage-1 frozen | `git diff stage-1-frozen c7275b7 -- stage-1` and `… fbae59c -- stage-1` are both empty. stage-2 is stage-1 plus src/screens.js and ui/. No nested .git, no node_modules, no symlinks. |
| Rule 1 | PASS. Dockerfile, RUN.md (builds, starts, lists the screens) and source are present. |
| `check run … 2 isolated`, c7275b7 | S1 **120/120** and S2 **25/25**. The stage-3 probe **FAILS**, as required. "claimed stage: 2 on the shipped checks" (report checks/1006-070527-12159). |
| `check run … 2 isolated`, fbae59c | S1 **120/120** and S2 **25/25**. The stage-3 probe FAILS. "claimed stage: 2 on the shipped checks" (report checks/1006-070727-12848). |
| `check build … stage-2 2` (clean exports) | stage 1 passes. Stage 2 has 24 passed and 1 error: `test_preceding_stage_accounts_survive_import` needs a preceding-stage service, which only `run` mode provides, and in `run` mode it passes. This is a harness limit, not a defect. |
| `check repo` | Only the 3 complaints that may be ignored. |
| Rule 4: no stage-3 work | PASS. No explain, history, policies, series, revision or accepted_terms endpoints or fields. The only matches are `window.history` and a local `explain` helper in the UI. Stage-3 checks fail. |
| Rule 5 | PASS. With `--cpus 2 --memory 2g` the service is healthy in under 1 s. With `--network none`, `/health` and `/` are served from inside the container. Fonts (Bricolage Grotesque, Instrument Sans, both with OFL licence files), scripts and CSS are all under ui/ in the image. |
| Rule 6 | PASS. No credentials. Dockerfile ENV is NODE_ENV, PORT, UV_THREADPOOL_SIZE. |
| Examiner probes | Seal recomputed: `6a3480c8…d4ca0`, which matches seal v2. Run against the fbae59c container, with TK_S1_URL set to a container built from `git archive stage-1-frozen stage-1`: **79/79 passed, 0 skipped** (compat probe ran). This includes the F1 depth-3000 regression probe. |

## Own attack: API (`/tmp/insp-s2r1-attack/api.py`)
All of these results match the spec:
- Request `[t_1,t_2]` against declared `[t_2,t_1]` → 201, stored as `["t_2","t_1"]`.
- Undeclared pair → 422 combination_not_allowed. Three tables → 422 combination_not_allowed. Duplicate id → 422 validation_failed. `table_id` and `table_ids` together → 422.
- Empty `table_ids` → 422. Wrong type (`"t_2"`, `[5]`) → 400.
- Party 9 on a pair that seats 8 → 422 party_exceeds_capacity.
- A pair is refused 409 when one member is taken, and a single is refused 409 when it is part of a booked pair.
- A response for a single table carries both `table_id` and `table_ids`. A response for a pair omits `table_id`.
- Pair replay → 200 with an identical body.
- PATCH: pair ↔ single works both ways, and both-fields and over-capacity are refused.
- Availability: `available_table_ids` lists singles only. `available_options` lists singles in fixture order, then pairs in `combinable` order. Members of a booked pair disappear, and cancelling frees both.
- Moves with `table_ids`: an atomic swap of a single and a pair → 201. A conflicting move → 409. An undeclared pair → 422. A wrong type → 400.
- Seeds: `table_ids` and `status: cancelled` are accepted. A seed overlapping a pair member → 422. In `combinable`, a self pair, a triple or a foreign table → 422.
- 50 concurrent mixed pair/single bookings on one slot → exactly 2 × 201 (t_2 and t_3 singles), 48 × 409, no overlap.
- F1 nesting 3000 → 422.
- Path traversal under /static/ (encoded and plain) → 404.

## Own attack: browser (`/tmp/insp-s2r1-attack/ui.py`, Chromium, real API, at 375, 768 and 1280)
At every width:
- Signed-out click on an open cell shows `auth-error`.
- `current-user` appears on `/`, `/signup`, `/login` and `/lookup`.
- `booking-summary` for a pair names both labels ("Window + Booth").
- **Lost response after commit, twice in a row, then success.** First `booking-uncertain` appears with no `booking-error` and no confirmation. Then the original reference appears, and the uncertain and error elements are removed. The service holds exactly one reservation, so the same key was retried.
- An unchanged resubmit returns the same reference with no error.
- **409 after another client took the table, with the form's party size edited first.** `booking-error` appears. The form stays open with the edited value (4). There is no confirmation, and the grid is refreshed (the cell now shows data-available=false).
- `confirmation-tables` and `reservation-tables` contain every label.
- Lookup: not found → `reservation-error`. Cancel → status `cancelled` and the cancel button is gone.
- A closed day → `no-slots`.
- **No sideways page scrolling** in any of the 18 states at any width. Keyboard focus shows a 2 px amber outline.

## Surface (54 captures in `/tmp/insp-s2r1-attack/shots/`, inspected by eye)
- **Mood:** ink-green background `#0E1A16`, warm off-white text `#F3ECDF`, one amber accent `#F4B04A`. There is no cream, no wine red and no pure black.
- **Type:** a display face for headings, times and the reference, and a text face for body copy. Times are large.
- **Seating tiles:** each tile's width follows its seat count, with seat dots. A joined pair is one linked tile ("Window 🔗 Booth", "Joined tables").
- **States are distinct without colour:**
  - Open: solid border, "● Open".
  - Taken: hatched, struck through, "⊘ Taken".
  - Too small: hatched, "↔ Too small".
  - Chosen: amber fill, "✓ Chosen".
  - Loading: ghost rows and "Checking tables…".
  - Refused: "⚠ Not booked".
  - Uncertain: dashed "? Outcome unknown".
  - Success: "✓ Booked · Confirmed" ticket.
- **Layout:** at 1280 the panel sits beside the chosen time and stays in view. At 375 it is a bottom sheet with a grip. The ticket shows the reference very large, with a Copy control.
- **Contrast (computed):** text 10.4–15.2:1. Muted 5.7–8.3:1. Faint is at least 4.8:1 on the surfaces where it is used. Amber 6.5–9.5:1. Button text on amber 9.8:1. Tile border against the surface 3.4:1.
- **Motion:** every transition and animation is 140 ms. `prefers-reduced-motion` sets them to 0 and turns them off. All inputs have visible labels.

## Clause rows: stage 2 (52 clauses in evidence/stage-2/clauses.md)

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S2-C1 | S1-13/14/15/16: error body; 400 for wrong JSON types; 422 for missing fields and bad … | PASS | probes see register; supplied S2 25/25 |
| S2-C2 | S1-30..35: idempotency (replay, key reuse, missing key) | PASS | probes see register; supplied S2 25/25 |
| S2-C3 | S1-56/60/69: other people's bookings give 404 | PASS | probes see register; supplied S2 25/25 |
| S2-C4 | S1-66/90: a failed write changes nothing | PASS | probes see register; supplied S2 25/25 |
| S2-C5 | S1-19/96, plus stage-2's "Concurrent requests must produce the same results as execut… | PASS | probes see register; supplied S2 25/25 |
| S2-C6 | S1-05 "Unknown fields … are ignored, never an error" plus S1-19 "must not produce 5xx… | PASS | probes see register; supplied S2 25/25 |
| S2-C7 | S1-97 (ruling): moves precedence by input order | PASS | probes see register; supplied S2 25/25 |
| S2-C8 | all stage-1 clauses S1-01..S1-96 | PASS | probes see register; supplied S2 25/25 |
| S2-05 | Each entry is an unordered pair of table ids | PASS | probes test_combo_booking_and_shape; supplied S2 25/25 |
| S2-06 | A pair not listed cannot be combined, whatever the table sizes are. Combining is not … | PASS | probes test_combo_errors; supplied S2 25/25 |
| S2-07 | A combination's capacity is the sum of its tables' capacities. | PASS | probes api; supplied S2 25/25 |
| S2-08 | Seeded reservations are confirmed unless they carry a status of cancelled | PASS | probes test_seeded_table_ids_and_status; supplied S2 25/25 |
| S2-09 | … may hold either table_id or table_ids | PASS | probes same; supplied S2 25/25 |
| S2-12 | available_table_ids stays exactly as it was — single tables only | PASS | probes test_available_options_basic; supplied S2 25/25 |
| S2-13 | available_options lists every single table and every declared pair with capacity >= p… | PASS | probes test_options_reference_model; supplied S2 25/25 |
| S2-14 | Singles first in fixture order, then pairs in combinable order. table_ids within a pa… | PASS | probes basic; supplied S2 25/25 |
| S2-15 | table_id is still accepted and means a set of one. | PASS | probes shape; supplied S2 25/25 |
| S2-16 | Sending both is 422 validation_failed. | PASS | probes errors, patch; supplied S2 25/25 |
| S2-17 | Responses always carry table_ids. They also carry table_id when the set has exactly o… | PASS | probes shape, patch, moves; supplied S2 25/25 |
| S2-18 | The booking occupies both tables for its full duration. | PASS | probes shape; supplied S2 25/25 |
| S2-19 | The pair is not in combinable → 422 combination_not_allowed | PASS | probes errors; supplied S2 25/25 |
| S2-20 | More than two tables → 422 combination_not_allowed | PASS | probes errors; supplied S2 25/25 |
| S2-21 | Any table in the set is taken for an overlapping interval → 409 table_unavailable | PASS | probes shape, patch; supplied S2 25/25 |
| S2-22 | Duplicate table id in the set → 422 validation_failed | PASS | probes errors, patch; supplied S2 25/25 |
| S2-23 | Existing single-table request formats remain supported. | PASS | probes shape; supplied S2 25/25 |
| S2-24 | Cancelling frees every table in the set. | PASS | probes test_cancel_frees_all; supplied S2 25/25 |
| S2-25 | PATCH … accepts table_ids under the same rules. | PASS | probes test_patch_table_ids; supplied S2 25/25 |
| S2-26 | (S1-65 carried) release the old tables and reserve the new ones together | PASS | probes patch; supplied S2 25/25 |
| S2-28 | Atomic reservation moves … also accept table_ids per move. No table may belong to ove… | PASS | probes test_moves_with_table_ids; supplied S2 25/25 |
| S2-41 | Concurrent requests must produce the same results as executing them one at a time in … | PASS | probes test_combo_concurrency; supplied S2 25/25 |
| S2-01 | / /signup /login /lookup … A screen route returns HTML | PASS | probes test_routes_are_html; supplied S2 25/25 |
| S2-50 | signup/login testids; "auth-error … Present only when there is one | PASS | probes test_signup_login_logout; supplied S2 25/25 |
| S2-51 | current-user — Visible on every screen when signed in. Text contains the display name | PASS | probes same; supplied S2 25/25 |
| S2-52 | logout-button | PASS | probes same; supplied S2 25/25 |
| S2-55 | slot-{table_id}-{HH:MM} — One cell per table per slot | PASS | probes test_grid_matches_api; supplied S2 25/25 |
| S2-56 | A cell is true exactly when its table_id is in that slot's available_table_ids … for … | PASS | probes same; supplied S2 25/25 |
| S2-57 | slot-{t_a}+{t_b}-{HH:MM} … Ids in combinable order … shown when a declared pair is av… | PASS | probes same; supplied S2 25/25 |
| S2-58 | no-slots — Shown instead of the grid when the day has no slots | PASS | probes same; supplied S2 25/25 |
| S2-59 | clicking an available cell while signed out shows auth-error or navigates to /login | PASS | probes test_signed_out_click; supplied S2 25/25 |
| S2-60 | booking-summary — Text contains the table label and the local start time" / "must nam… | PASS | probes flow, combination; supplied S2 25/25 |
| S2-61 | booking-party-size — pre-filled from the search | PASS | probes flow; supplied S2 25/25 |
| S2-62 | confirmation-reference — Text is exactly the reference"; "confirmation-details — rest… | PASS | probes flow; supplied S2 25/25 |
| S2-63 | Keep the booking form on screen after success. Submitting it again without changing a… | PASS | probes flow; supplied S2 25/25 |
| S2-64 | Changing a field makes the next submission a new booking request. | PASS | probes flow; supplied S2 25/25 |
| S2-31 | If another client takes a table after the form opens, a 409 … shows booking-error and… | PASS | probes test_conflict_shows_error_and_refreshes; supplied S2 25/25 |
| S2-34 | If a booking response is lost, including after the booking commits, show nonempty boo… | PASS | probes test_lost_response_then_retry; supplied S2 25/25 |
| S2-30 | If search A starts before search B but finishes after it, the grid, table labels and … | PASS | probes test_out_of_order_search; supplied S2 25/25 |
| S2-70 | combination cells, "confirmation-tables", "reservation-tables" contain every table la… | PASS | probes test_combination_booking_ui; supplied S2 25/25 |
| S2-67 | lookup: "reservation-status — exactly confirmed or cancelled"; "reservation-cancel-bu… | PASS | probes test_lookup_and_cancel; supplied S2 25/25 |
| S2-45 | usable at a 375 CSS-pixel viewport … without horizontal page scrolling | PASS | probes test_no_horizontal_scroll_375; supplied S2 25/25 |
| S2-35 | A stage-2 service must accept an export produced by the same team's stage-1 service. | PASS | probes test_s2_compat; supplied S2 25/25 |
| S2-38 | A browser signed in before that export/import upgrade must remain signed in afterward… | PASS | probes test_upgrade_keeps_session_and_retry; supplied S2 25/25 |

Stage-1 clauses S1-01…S1-97: all PASS. Evidence is the 53 carried stage-1 probes (79/79 run), supplied S1 120/120 on fbae59c, and the F1 regression probe.

## Rulings on the builder's doubts (none blocks)
1. **Unknown table 404 before combination_not_allowed:** accepted. The spec does not order them, and an unknown table is a missing resource under §5.
2. **Duplicate fixture pairs kept once; unknown table or self pair makes reset 422:** accepted. A fixture value out of range is 422 under §5, consistent with S1-07.
3. **[t_1,t_2] stored and returned as the declared [t_2,t_1]:** accepted. This matches the "table_ids within a pair is in combinable order" rule for availability, and the set is the same.
4. **A stage-1 receipt replays its original stage-1 body after import:** accepted. §7 says "body identical to the original response", consistent with the examiner's ruling S2-35. The compat probe passed.
5. **The finisher's behaviour suite has not been run against the real API:** covered. The probes (lost, out-of-order, 409, upgrade) passed, and my own real-API run above passed at all three widths, including double loss, a combined-table loss and an edited form across a 409.

## Observations (not blocking)
- O1. At 375 px a 2-seat tile is narrow. "Too small" wraps onto two lines, and the seat dots sit close to the label. On the 1280 capture the 2-seat Window tile shows no "2 seats" text (dots only).
- O2. Unavailable tiles render their label dimmed and struck through on a hatched fill. This is legible, but it is the lowest-contrast text on the grid. It is not a clause violation, because the state is also carried by the icon and the word.
- O3. The `check build` stage-2 error is a harness-mode limit (the upgrade check needs `run` mode). Lead: rely on `check run` for stage 2.
- O4. Structure is clean. Server modules are at most 242 lines (store.js) and UI modules at most 247 (search.js). There are no special cases keyed to checks, and a single request client sorts every outcome into ok, refused or lost.
