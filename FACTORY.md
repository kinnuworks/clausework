# FACTORY.md — Clausework

A factory of five coding-agent seats that turns a written specification into a working,
inspected service, stage by stage, from one dispatched message.

This file is enough to stand it up. Every number in it was measured from `room.json`, the
Git history, or the seats' Claude Code session logs. It describes the run in this
repository and, in §6, the three runs before it.

## 1. The idea

The unit of work is a **clause**, not a feature.

1. Before any code exists, one seat reads the specification sentence by sentence and
   writes every "must / must not / always / never" as a numbered clause with its family
   and the wrong answer a careless reading would produce.
2. The same seat writes executable checks from that register alone, never having seen the
   implementation, and commits a SHA-256 of them before the first inspection.
3. A different seat builds. A third inspects a clean export of the exact revision and
   returns one verdict with every problem in it.
4. The seat that wrote the checks then plants defects in a scratch copy to measure what
   its own checks would miss, and adds a check for every miss.

A clause is closed only by evidence from a seat that did not write the code. The supplied
acceptance checks are run as a black box and are never the definition of done: in this
event they cover 83%, 41%, 11% and 21% of the real suites.

## 2. Seats

All five are headless Claude Code seats owned by BAND Desktop, `claude-opus-5-5` at high
effort, on one Claude subscription.

| Seat | Owns | Never does |
|---|---|---|
| `lead` | Intake, work orders that paste the full specification, the on-disk ledger, freezing, recovery, the final report | Write product code, checks or verdicts |
| `builder` | The behaviour of the deliverable; build and run instructions; a design note | Accept its own work; touch the surface |
| `finisher` | The surface people use: a written brief, a token-based visual system, every screen and state, bundled assets, captures at several widths | Change behaviour |
| `examiner` | The clause register, sealed checks, rulings on disputed readings, the planted-defect audit | Read the implementation before its seal is committed; fix code |
| `inspector` | One verdict per reported revision from a clean export: delivery rules, supplied checks, the examiner's checks, a ten-minute attack, the screens, a maintainability read | Fix code |

## 3. Protocol for one stage

1. `lead` saves the complete work order, including the full specification text, to
   `evidence/stage-N/work-order.md`, and sends `examiner`, `builder` and `finisher` their
   own complete orders in parallel.
2. `examiner` commits `clauses.md` and `seal.txt`. `builder` copies the previous stage's
   folder forward unchanged, then extends it. `finisher` owns one directory of it.
3. Everyone builds and tests from a clean export of a commit, never the shared tree.
4. `builder` reports a revision to `lead`. `lead` confirms the seal is in, asks `examiner`
   to reveal the checks and start the audit, and sends `inspector` a complete order.
5. `inspector` returns ACCEPT or REJECT with a clause-level table. Only a violation of a
   written clause or a delivery rule blocks. A rejection carries the smallest input that
   shows the failure and goes straight to the seat that owns the fix.
6. At most three rounds. Then `lead` tags the best inspected revision as frozen, records
   open clauses, and opens the next stage. A frozen folder never changes.
7. While a stage is under inspection, `lead` may order look-ahead work for the next one,
   provided nothing is written into an active or frozen folder.

Rules that apply to the whole deliverable (error reporting, validation, authorisation,
repeated submissions) are carried into every later stage's register against each new
entry point.

## 4. Stand it up

Prerequisites: BAND Desktop 0.4.12+, Claude Code signed in, Docker, Python 3.12, a checkout
of the event's kickoff repository with its harness environment.

```sh
# 1. Sign in and install the Claude Code plugin
band init
band plugin install
band preflight

# 2. Create the five seats (repeat for lead, builder, finisher, examiner, inspector)
band agent create --session seat-lead --name lead \
  --description "Clausework factory seat: lead" \
  --transport claude-code-cli --runtime-auth subscription \
  --runtime-model claude-opus-5-5 --runtime-effort high \
  --claude-permission-mode bypassPermissions \
  --claude-context-mode local_config --claude-strict-mcp-config \
  --cwd /abs/path/to/workspace --instructions-file /abs/path/to/mandates/lead.md

# 3. Create the room from the lead seat, then add the other seats and yourself
band chat new --session seat-lead
band chat add --session seat-lead <room> <account>/builder <account>/finisher \
  <account>/examiner <account>/inspector <your-user-id>

# 4. Dispatch once, mentioning only the lead
band room send <room> "$(cat dispatch.md)" --mention <lead-participant-id>
```

Notes that cost us time to learn:

- **Let the lead own the room.** A seat's permission request is routed to the room owner.
  If the human owns the room, an unattended run waits on the human. With the lead as
  owner it is decided inside the band (`mandates/lead.md`, "Permission requests").
- **`--claude-strict-mcp-config`** drops the operator's own MCP servers. Without it each
  seat started with 325 tools and 17 servers; with it, 29 tools and BAND's relay only.
- **Create seats with the CLI** so the handle is exactly the seat name; the mandate file
  must be named after the seat.
- **Send the dispatch with `band room send`**, not the input box, which rewrites `--` and
  does not turn pasted `@name` text into a mention.
- The mandates are attached with `--instructions-file`, which is live-linked: editing the
  file changes the seat. Do not edit them during a run.

The dispatch we sent is [`kit/dispatch.md`](kit/dispatch.md), verbatim: 6.1 KB naming the
workspace, the four specification paths, seven delivery rules, the check commands, the
tooling available for the band's own checks, and a hard stop. It names no architecture,
language. It does carry a short product brief for the browser screens (mood, type,
the seating-tile idea, where the booking panel sits). The band chose Node with zero
dependencies itself. An earlier run with no product brief is described in §6.

## 5. What the run did

Room `dbb7e667…`, 6 Oct 2026. Dispatch 06:33:24 IST, final report 07:47:16.
2,056 room events. **One human message.** No error events, no permission requests.

| Stage | Frozen revision | Rounds | Time | Supplied checks (isolated) | Band's sealed checks (cumulative) | Clauses |
|---|---|---|---|---|---|---|
| 1 | `fa79f76` | 2 | 06:38–06:59 | 120/120 | 53 | 97 |
| 2 | `fbae59c` | 1 | 06:59–07:13 | 120 + 25/25 | 79 | 44 |
| 3 | `840eef4` | 2 | 07:13–07:30 | 120 + 25 + 7/7 | 101 | 61 |
| 4 | `40b4083` | 2 | 07:30–07:46 | 120 + 25 + 7 + 6/6 | 118 | 38 |

After the run, a fresh clone passed `harness run --all --mode isolated` with every folder
claiming its own stage.

### Work was shared

| Seat | Commits | Room text messages | Tool calls |
|---|---:|---:|---:|
| lead | 33 | 82 | 129 |
| finisher | 24 | 10 | 201 |
| examiner | 16 | 20 | 134 |
| builder | 11 | 12 | 128 |
| inspector | 7 | 7 | 151 |

`builder` and `finisher` both authored files under `stage-N/` (11 and 8 commits).

### Review that changed the product

- **Stage 1, round 1: REJECT** (`evidence/stage-1/verdict-1.md`). A JSON body nested about
  3,000 levels deep in an ignored field made two write paths return 500. The specification
  says requests must not produce 5xx. Every supplied check was green. The builder fixed
  the comparison code and, in the same pass, three logged observations.
- **Stage 3, round 1: REJECT** (`evidence/stage-3/verdict-1.md`). Under a newly published
  policy, the grid hid a joined-table option the server was offering, because the screen
  read table sizes from the original fixture. The interface, the supplied checks and the
  sealed checks all passed; the inspector found it by using the screens. The **finisher**
  fixed it: the grid now takes everything from the availability answer.
- **Stage 4:** round 1 accepted. The finisher then made one more screens-only commit, and
  the lead had it re-inspected (round 2) before freezing rather than freeze unreviewed code.

### How good were the band's own checks?

After each revision the examiner planted defects in a scratch copy, one at a time.

| Stage | Planted | Caught by the band's checks | Caught by the supplied checks |
|---|---:|---:|---:|
| 1 | 5 | 5 | 3 |
| 2 | 5 | 5 | 0 |
| 3 | 5 | 5 | 1 |
| 4 | 5 | 5 | 0 |
| **Total** | **20** | **20** | **4** |

Details per defect and clause family are in `evidence/stage-N/probe-audit.md`, including
which defects were caught by exactly one check (a thin margin, stated there). Separately,
the inspector compared the stage-4 seating optimiser with a brute-force search on 260
random restaurants: 188 of 188 feasible plans identical, 50 of 50 impossible cases refused.

## 6. Measured cost

From the five seats' Claude Code session logs for the room's time window
(`usage-report.py` in §9). Dollar figures are API list price for `claude-opus-5-5`
($4 / $20 per million input / output tokens, cache reads $0.20; cache writes assumed at
$5). The run was on a subscription, so nothing was billed per token.

| Seat | API calls | Cache write | Cache read | Output | API-equivalent |
|---|---:|---:|---:|---:|---:|
| examiner | 121 | 388,139 | 29,088,163 | 238,225 | $12.52 |
| finisher | 139 | 374,644 | 33,104,140 | 199,632 | $12.49 |
| inspector | 130 | 356,013 | 27,689,181 | 146,832 | $10.26 |
| builder | 122 | 318,583 | 23,975,875 | 188,707 | $10.16 |
| lead | 141 | 226,437 | 18,735,896 | 83,677 | $6.55 |
| **Total** | **666** | **1,669,952** | **133,488,429** | **858,823** | **$52.23** |

136.0 M tokens in total. Wall-clock 74 minutes. Checking (examiner + inspector) cost
$22.78, building (builder + finisher) $22.65, coordination $6.55. Thirteen short calls ($0.25) could not be attributed to a seat.

**Development before this run** (all on the same day, same five seats):

| Run | Problem | Mandates | Result | Time | API-equivalent |
|---|---|---|---|---|---|
| Rehearsal 1 | toy, stages 1–2 | first version | 2 of 2 frozen | 17 min | $10.23 |
| Full run 1 | tablekeeper | final (`1ee13e25…`) | 4 of 4 frozen, 1 rejection | 85 min | $47.21 |
| Rehearsal 2 | toy, stages 1–2 | final (`1ee13e25…`) | 2 of 2 frozen | 11 min | $5.05 |
| **This run** | tablekeeper | final (`1ee13e25…`) | 4 of 4 frozen, 2 rejections | 74 min | $52.23 |

Full run 1 is public and unedited at
https://github.com/kinnuworks/clausework-tablekeeper. Its dispatch had no product brief;
the band chose Python and a paper-and-ink look. We judged its interface too conservative,
added the brief, and ran again in a fresh room and repository. Nothing else changed.
Total for the day: about $115 at list price.

## 7. Design choices and what they cost

| Choice | Why | Cost |
|---|---|---|
| A separate examiner that never reads code before sealing | The unseen part of the suites is in the specification; a second, independent reading is the only way to cover it | The most expensive seat ($12.52, 24%) |
| Seal by hash, reveal at inspection | Shows the checks were not fitted to the code | The builder cannot use them in its first pass; one extra round when they find something |
| Planted-defect audit, capped at five defects and ten minutes | Puts a number on the checks instead of trusting them | Runs in parallel with inspection, so little wall-clock |
| One verdict with everything in it, three rounds at most | Open-ended review is what turns a 2-hour run into a 12-hour one | A stage can freeze with open clauses; they are recorded |
| Only written clauses block | Stops a stage being held up by inputs the specification never mentions | Some real oddities are logged, not fixed |
| Two product authors with disjoint directories | Lets the surface get real attention without two seats editing one file | A hand-off contract between them at the start of the first stage with screens |
| Everyone tests clean exports of commits | Five seats share one working tree | Extra builds |
| Lead keeps state in `evidence/ledger.md` | Survives a compacted context; gives judges a single timeline | 38 small commits |
| Bounded watch after every order, then one RESEND, then reassign | A lost reply otherwise stalls a dark run forever | Not triggered in this run |
| All seats on one model at high effort | Simple to stand up | No second model family as an independent reader |

## 8. What went wrong, and what we would change

Numbered so they can be cited.

1. **Rehearsal 1: the inspector accepted before the seal existed.** The builder's first
   mandate told it to report to both lead and inspector. Fixed: first revisions go to the
   lead only; the inspector starts only on the lead's order.
2. **Rehearsal 1: a permission prompt despite bypass mode.** A wildcard recursive delete
   triggered Claude Code's own safeguard. The lead approved it within seconds because it
   owned the room. Fixed: the mandates forbid such deletes and tell the lead to decide any
   request at once.
3. **Rehearsal 1: the lead weakened correct code on purpose.** Our dispatch said a stage
   folder must not pass the next stage's checks; on the toy the lead ordered a deliberate
   pause to make a race visible. That was our wording. The dispatch now says never to
   weaken correct behaviour.
4. **Full run 1: the interface was conservative**, and four of the examiner's sealed
   checks were themselves wrong. Corrections are recorded there.
5. **Rehearsal 2: the lead skipped the planted-defect audit** for one stage to save time
   and said so in its ledger. The mandate caps the audit; it does not make it mandatory.
   It should.
6. **Rehearsal 2: one seat started a background job** against rule 5; it failed and was
   logged as an error event. Not seen in the full runs.
7. **This run: seats kept posting after CLOSED.** Late status messages crossed with the
   close; the lead answered them without reopening anything. Rule 12 needs a hard stop.
8. **This run: a known rough edge was left in.** On a phone, an open booking panel keeps
   the original table after a seating change.
9. **Stall recovery was never exercised for real.** No order went unanswered in any run.
10. **One model family.** Every seat is the same model; the examiner is independent in
    what it has read, not in how it reasons.

With more time: a second model family for the examiner, a mandatory audit, and enough
full runs to put a spread on these numbers.

## 9. Reproducing the numbers

- Room facts: `room.json` (`senderType`, `messageType`, `insertedAt`).
- Commits by seat: `git shortlog -sn`; product authors: `git log --format=%an -- stage-1 stage-2 stage-3 stage-4 | sort | uniq -c`.
- Stage claims: `python -m harness run --track tablekeeper --repo . --all --mode isolated`.
- Seals: each `evidence/stage-N/seal.txt` holds the command that recomputes its hash.
- Token use: `kit/usage-report.py <claude projects dir> <start> <end>`.
- `kit/` also holds the seat-creation script and the small wrapper around the event
  harness that the dispatch names.

## 10. Human input, in full

| When | What |
|---|---|
| Before the run | Wrote the five mandates, the dispatch, a wrapper script around the event harness; created the seats and the room |
| 06:33:24 IST | The dispatch, one message |
| During the run | Nothing. No message, approval, restart or file change |
| After the run | Downloaded `room.json`; wrote `README.md` and this file; copied the rehearsal evidence into `portability/` |

**Mandates.** Every run in §6 except rehearsal 1 used the files in `mandates/`, combined
hash `1ee13e25…cfaa` (the command is in [`portability/`](portability/)). Rehearsal 1 began
with an earlier version; its three fixes are items 1 and 2 above plus a five-minute grace
rule for the seal. None of the edits mentions any problem domain.
