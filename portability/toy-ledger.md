# Ledger — toy-result-2 (lead)

Workspace: /Users/kinnu/hackathon4 ; result repo: /Users/kinnu/hackathon4/band-work/toy-result-2 (branch main)
Stages in scope: 1 and 2 only (hard stop 07:00 local). Stages 3/4 not built.
Checks: /Users/kinnu/hackathon4/factory/bin/check run toy <repo> N [isolated]; check repo toy <repo>
Seats: all five present in room at 06:21 (builder, finisher, examiner, inspector, lead).

## Time shares
- Intake 06:21-06:24
- Stage 1: 06:24-06:40
- Stage 2: 06:40-06:56
- Final report: 06:56-07:00

## Decisions
- 06:23 Stage-2 folder must not add explicit stage-3 locking machinery, but must not introduce artificial races or delays (delivery rule 4: never weaken correct behaviour).
- 06:23 Look-ahead: finisher drafts stage-2 page in a scratch dir during stage 1 (nothing written to stage-2/ until stage 1 frozen).

## Events
- 06:21 intake; specs read.
- 06:24 Stage 1 opened; orders to examiner, builder, finisher.
- 06:23 builder committed stage-1 at 24dc0f8 (Python stdlib, in-memory, lock around counter). Lock kept: correct behaviour, rule 4 forbids weakening it; stage-1 cannot pass stage-2 checks anyway (no page).
- 06:24 examiner seal committed 6189023.
- 06:25 examiner asked to reveal + audit probes; inspector work order sent for 24dc0f8 (due 06:36).

- 06:27 examiner revealed probes fbcb24a (seal 931a8043 verified by inspector); inspector ACCEPT 24dc0f8 round 1 (22799e1): isolated check claimed stage 1, 25/25 probes.
- 06:28 Stage 1 FROZEN at 24dc0f8, tag stage-1-frozen. stage-1/ must never change again. Stage 2 opened.
- 06:28-06:29 stage 2: builder e000572 (copy) + 62be256 (route), finisher bdd3b33 (page) + 8e39779 (design brief, screens), examiner seal f82bf8b.
- 06:30 stage 2 inspection ordered on 62be256 (due 06:42); examiner asked to reveal + audit.
- 06:29 examiner revealed stage 2 probes 6174851 (seal ec007e85 verified by inspector).
- 06:32 inspector ACCEPT 62be256 round 1 (db2c11a): isolated check claimed stage 2 (100%), 36/36 probes, repo scan clean apart from the 3 human-added files.
- 06:33 Stage 2 FROZEN at 62be256, tag stage-2-frozen. Run ends (stages 3/4 out of scope). No seat needed covering; no RESENDs; no disputes.
- 06:34 examiner reports stage 2 reveal 6174851, 36/36 pass. Gap: the planted-defect probe audit was not run for either stage (stage 1 audit skipped by lead for time; run closed before stage 2 audit). No probe-audit.md exists.

## Stage status
| Stage | Step | Round | Revision | Owes | Verdict |
|---|---|---|---|---|---|
| 1 | FROZEN (tag stage-1-frozen) | 1 | 24dc0f8 | - | ACCEPT (22799e1), no open clauses |
| 2 | FROZEN (tag stage-2-frozen) | 1 | 62be256 | - | ACCEPT (db2c11a), no open clauses; non-blocking observations in verdict.md |
