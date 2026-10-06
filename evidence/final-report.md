@dhirajkavuri FINAL REPORT: tablekeeper, result-b (lead)

All four stages are built, inspected and frozen by 07:46, with 1h14m to spare before the 09:00 hard stop. My own final run under judging conditions (`check run tablekeeper result-b 4 isolated`, 07:47) passes stages 1, 2, 3 and 4 and prints "claimed stage: 4 on the shipped checks". The repo scan lists only the 3 files you said you'd add (README.md, FACTORY.md, room.json).

| Stage | Frozen revision (tag) | Verdict | Rounds | Time | Supplied checks (isolated) | Examiner probes |
|---|---|---|---|---|---|---|
| 1: reservations API | fa79f76 (stage-1-frozen) | ACCEPT | 2 | 06:38-06:59 | 120/120 | 53/53 |
| 2: browser screens + joined tables | fbae59c (stage-2-frozen) | ACCEPT | 1 | 06:59-07:13 | S1 120/120, S2 25/25 | 79/79 |
| 3: policies, history, recurring bookings | 840eef4 (stage-3-frozen) | ACCEPT | 2 | 07:13-07:30 | + S3 7/7 | 101/101 |
| 4: seating changes, recurring amendments | 40b4083 (stage-4-frozen) | ACCEPT | 2 | 07:30-07:46 | + S4 6/6 | 118/118 |

Rejections and what fixed them:
- Stage 1, round 1: a deeply nested JSON body (depth about 3000) made POST /reservations and POST /reservation-moves return 500. The builder fixed the comparison code. In the same round the builder also fixed three observations:
  - moves errors are now resolved per item in input order (the examiner ruled this);
  - signing up seeded users is faster (400 users reset in 2.4 s);
  - a numeric seeded reference is now rejected.
- Stage 3, round 1: under a newly published policy, the grid hid a joined-table option that the server was offering, because it read table capacities from the original fixture. The finisher fixed it; the grid now takes everything from /availability.
- Stage 4, round 2: no rejection. Round 1 accepted, but the finisher then made one more screens-only commit: a "seating changed" note on the ticket and a clipped "2 seats" label fixed. It was re-inspected and accepted.

Clauses still open: none known. Non-blocking observations remain:
- On a phone, a booking panel that is already open keeps showing the original table after the restaurant moves the booking. The ticket and lookup do show the new table, and the spec requires no live updates.
- The scratch-mode build check always errors on stage 2's upgrade test, because that test needs the earlier stage running. Run mode passes it.
- The supplied checks are only about 83%, 41%, 11% and 21% of the real suites, so these green results do not prove the stages.

Evidence beyond the supplied checks:
- The examiner sealed probes before seeing any code, about 50 to 118 per stage, including browser and upgrade tests.
- Planted-defect audits per stage: the probes caught 5/5 each time; the supplied checks caught 3/5, 0/5, 1/5 and 0/5.
- In stage 4 the inspector checked the seating optimiser against a brute-force search on 260 random restaurants: 188/188 plans identical, and 50/50 impossible cases correctly refused.
- Upgrades work: data exported from each frozen earlier stage imports into the later ones, with sign-ins, references and retries still valid.

Screens (stages 2-4): the "Evening Service" design. Ink-green background, warm off-white text, one candle-amber accent. Bricolage Grotesque and Instrument Sans are bundled with their open font licences. Seating tiles are sized by seat count, and joined tables are drawn as one linked tile. Every state is told apart by icon and word, not colour alone. On wide screens the booking panel sits beside the chosen time; on phones it opens from the bottom. The confirmation is a ticket with a large reference and a Copy button. Motion is 140 ms at most and switches off for reduced-motion settings. Screenshots at 375/768/1280 are in evidence/stage-N/screens/.

Seat coverage: no seat needed covering for. No order had to be resent and none was reassigned. Every seat delivered before its deadline.

The ledger, work orders, clause registers, seals, probes, audits and verdicts are in result-b/evidence/.
