You are the lead seat of this factory. Build the service below, all four stages in order, coordinating the other seats. This message is the only human input you will get: no human is available until your final report.

WORKSPACE
- Workspace root: /Users/kinnu/hackathon4
- Result repository (git, branch main, already holds mandates/): /Users/kinnu/hackathon4/band-work/result-b
- Do not edit mandates/. Do not write outside the result repository except in scratch directories under the system temporary directory.

THE TASK
Track: tablekeeper. Four stages, each with its own written specification. Read each one in full when its stage starts, and paste it in full into every work order.
- Stage 1: /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-1.md  ->  result-b/stage-1/
- Stage 2: /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-2.md  ->  result-b/stage-2/
- Stage 3: /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-3.md  ->  result-b/stage-3/
- Stage 4: /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-4.md  ->  result-b/stage-4/
Later specifications extend earlier ones; everything in an earlier stage still applies.

DELIVERY RULES
1. Each stage folder is a complete service that builds on its own: a Dockerfile, a RUN.md with the command that builds and starts it, and the source. Language, framework and storage are the band's choice.
2. stage-2/ starts as a copy of stage-1/, stage-3/ as a copy of stage-2/, and so on. Remove any nested .git directory from a copy.
3. Each folder is judged against every stage's checks up to its own number. A stage that breaks an earlier stage counts for nothing.
4. Each folder holds that stage's solution and nothing from a later stage: do not implement a later stage's requirements early. A folder that also passes the whole of the next stage's checks earns nothing. Every later stage adds new entry points and rules, so a folder that implements only its own stage cannot pass the next stage's checks; never weaken, slow down or break correct behaviour to satisfy this rule. Once a stage is frozen its folder never changes.
5. The image may fetch dependencies while building. At run time there is no outbound network; fonts, scripts and styles must be inside the image. Limits are in the stage 1 specification (CPU, memory, start time, concurrency, per-request time).
6. The repository is public. No credentials. No file may assign a literal value to a name ending in KEY, TOKEN, SECRET or PASSWORD in a Dockerfile or a configuration file. No symbolic links or submodules.
7. Build to the specification. The supplied checks are only a sample of the real suites (about 83%, 41%, 11% and 21% for stages 1 to 4). The rest is derived from the same specification and is run after submission. A green run on the supplied checks is not proof of a stage.

CHECKS (run from any directory; each run prints where its logs are)
- One stage, development mode:   /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 1
- One stage, judging conditions: /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 1 isolated
- A scratch copy of one folder:  /Users/kinnu/hackathon4/factory/bin/check build tablekeeper /path/to/folder 1
- Repository layout and credential scan: /Users/kinnu/hackathon4/factory/bin/check repo tablekeeper /Users/kinnu/hackathon4/band-work/result-b
Replace 1 with the stage number. A stage run also runs every earlier stage's checks, then the next stage's checks as a probe that is supposed to FAIL. The line that matters is the last one: "claimed stage: N on the shipped checks". The repository scan will complain that README.md, FACTORY.md and room.json are missing; the humans add those afterwards, so ignore those three complaints and fix any other.
The final inspection of every stage uses judging conditions (isolated).

TOOLING FOR THE BAND'S OWN PROBES
/Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python has pytest, httpx and playwright with Chromium. Docker is on PATH.

PRODUCT BRIEF FOR THE BROWSER SCREENS (stage 2 onward)
The stage 2 specification asks for a warm, confident hospitality product. Meet every word of it, and aim higher than a tidy form: this must look like a product a good restaurant group would be proud to ship in 2026, not like generated boilerplate.
- Mood: evening service. A deep, dark background (ink green or charcoal, not pure black), warm off-white text, one candle-amber accent. No cream paper, no wine red, no default serif-and-beige look.
- Type: one distinctive display face for headings and times and one clean text face, both bundled in the image with their licences. Times are large and confident; this is a timetable people scan.
- The availability view is the signature. For each time, show the tables as a row of seating tiles whose width reflects how many they seat, with joined tables drawn as one linked tile, so a diner reads the room at a glance. Available, unavailable, chosen and loading must be unmistakable without colour alone.
- Wide screens: the booking panel sits beside the time that was chosen and stays in view. Phones: it opens as a sheet from the bottom. The confirmation is a ticket with the reference in very large type and a copy control.
- Motion is short and purposeful (150 ms or less) and respects reduced-motion settings.
- Every data-testid, route and behaviour in the specification is unchanged by any of this; the look never costs a requirement. No sideways page scrolling at 375 px. Visible labels, visible focus, checked contrast.

TIME
Hard stop: 09:00 local time. Divide the time across the four stages, weighting stages 2 and 3. If the clock runs out, freeze what has been inspected and report.

FINAL REPORT
When stage 4 is frozen or time is up, post one report addressed to me, then close the room.

