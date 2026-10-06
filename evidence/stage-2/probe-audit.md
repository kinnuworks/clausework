# Stage 2 probe audit (examiner)

Revision audited: `c7275b7433d6ab12c4f208af69382bb59c38b0d7` (`stage-2/`), clean `git archive` export into a scratch directory.
Probes: `evidence/stage-2/probes/`, revealed unchanged in df866d8. The recomputed seal matches v2 `6a3480c8…d4ca0`.
Stage-1 export source for the compatibility probe: tag `stage-1-frozen` (fa79f76), exported the same way and run as TK_S1_URL.

## Re-run on the frozen revision fbae59c (stage-2-frozen)
fbae59c's stage-2/ is c7275b7 plus finisher CSS polish (stage-2/ui/css/base.css and search.css only). I repeated the whole audit on a
clean export of fbae59c, applying the same 5 defects: identical results. Baseline 79/79 pass. D1 2 failed, D2 1, D3 1, D4 3, D5 8:
the same tests as below. Supplied checks: stage 1 "120 passed" on every copy; stage 2 "24 passed, 1 error" (the upgrade check, which
cannot run in scratch mode) on every copy, baseline included.

## Baseline
On the unmodified revision all **79/79 probes pass**, including the stage-1-frozen export → stage-2 import probe and the 11 Playwright
UI probes. No probe contradicted the specification, so there are no probe corrections.

## Planted defects (one per scratch copy; never in the repository)

| # | Family | Clause | Defect planted | Probes | Supplied checks (`check build … 2`) |
|---|---|---|---|---|---|
| D1 | repeated submission (UI behaviour) | S2-34, S2-38 | After a lost booking response, the UI drops its retry identity, so the retry sends a **new** Idempotency-Key | **caught**: 2 failed (test_lost_response_then_retry, test_upgrade_keeps_session_and_retry) | **missed** |
| D2 | order (UI behaviour) | S2-30 | Removed the "only the latest search may change the screen" guard, so a late search A overwrites search B | **caught**: 1 failed (test_out_of_order_search) | **missed** |
| D3 | order / precedence | S1-97 (ruling) | Moves resolve every reference for the whole batch (404) before the per-item checks: the builder's pre-ruling behaviour | **caught**: 1 failed (test_ruling_s1_97_moves_precedence) | **missed** |
| D4 | all or nothing | S1-66, S2-C4 | PATCH writes the amended record before the occupancy check, so a refused amendment (409) still persists | **caught**: 3 failed (test_patch_failures_leave_booking, test_patch_burst, test_patch_table_ids) | **missed** |
| D5 | behaviour (combined tables) | S2-18, S2-13 | Overlap compares only the first table of each set, so a pair does not block its second table | **caught**: 8 failed (options basic and reference model, combo shape, cancel frees, PATCH, moves, seeded, combo concurrency) | **missed** |

On the supplied checks: in scratch mode, every copy, the unmodified baseline included, gives the same summary: stage 1 pass; stage 2
"24 passed, 1 error". The one error is the upgrade check, which needs the preceding stage (`--previous-base-url`) and cannot run in
`check build` mode. It errors identically on the baseline, so it says nothing about the planted defects. None of the other 24 supplied
stage-2 checks failed on any defect.

## By family

| Family | Planted | Caught by probes | Caught by supplied checks |
|---|---|---|---|
| repeated submission (UI) | 1 | 1 | 0 |
| order (UI, out-of-order search) | 1 | 1 | 0 |
| order / precedence (API) | 1 | 1 | 0 |
| all or nothing | 1 | 1 | 0 |
| behaviour (combined occupancy) | 1 | 1 | 0 |
| **total** | **5** | **5** | **0** (1 upgrade check could not run in scratch mode) |

The probes missed no defect, so no new probe was needed.

## Weak spots
- Each of D2 and D3 is caught by exactly **one** probe, so the margin is thin. A second out-of-order variant (late response for a
  different party size on the same restaurant) and a second precedence variant (a different-restaurant 422 after an own cancelled
  item) would harden them. They are noted for stage 3. The stage-2 probe set is sealed and stays unchanged.
- Visual-quality requirements (warmth, contrast, focus visibility) are not mechanically probed. They are left to the inspector.

## Clean-up
Defect containers and images were removed. The scratch copies stay under the system temp dir (`examiner-s2-audit-*`), because the
factory forbids recursive delete. None of them is in the repository.
