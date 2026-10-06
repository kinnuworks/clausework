You are the lead seat of this factory. This is a short run. Build the service below, stages 1 and 2 only, coordinating the other seats. This message is the only human input you will get: no human is available until your final report.

WORKSPACE
- Workspace root: /Users/kinnu/hackathon4
- Result repository (git, branch main, already holds mandates/): /Users/kinnu/hackathon4/band-work/toy-result-2
- Do not edit mandates/. Do not write outside the result repository except in scratch directories under the system temporary directory.

THE TASK
Track: toy. Four stages, each with its own written specification. Read each one in full when its stage starts, and paste it in full into every work order.
- Stage 1: /Users/kinnu/hackathon4/dark-factory-wearedevs/toy/spec/stage-1.md  ->  toy-result-2/stage-1/
- Stage 2: /Users/kinnu/hackathon4/dark-factory-wearedevs/toy/spec/stage-2.md  ->  toy-result-2/stage-2/
- Stage 3: /Users/kinnu/hackathon4/dark-factory-wearedevs/toy/spec/stage-3.md  ->  toy-result-2/stage-3/
- Stage 4: /Users/kinnu/hackathon4/dark-factory-wearedevs/toy/spec/stage-4.md  ->  toy-result-2/stage-4/
Later specifications extend earlier ones; everything in an earlier stage still applies.

DELIVERY RULES
1. Each stage folder is a complete service that builds on its own: a Dockerfile, a RUN.md with the command that builds and starts it, and the source. Language, framework and storage are the band's choice.
2. stage-2/ starts as a copy of stage-1/, stage-3/ as a copy of stage-2/, and so on. Remove any nested .git directory from a copy.
3. Each folder is judged against every stage's checks up to its own number. A stage that breaks an earlier stage counts for nothing.
4. Each folder holds that stage's solution and nothing from a later stage: do not implement a later stage's requirements early. A folder that also passes the whole of the next stage's checks earns nothing. Every later stage adds new entry points and rules, so a folder that implements only its own stage cannot pass the next stage's checks; never weaken, slow down or break correct behaviour to satisfy this rule. Once a stage is frozen its folder never changes.
5. The image may fetch dependencies while building. At run time there is no outbound network; fonts, scripts and styles must be inside the image. Limits: 2 CPU, 2 GiB memory, healthy within 60 seconds.
6. The repository is public. No credentials. No file may assign a literal value to a name ending in KEY, TOKEN, SECRET or PASSWORD in a Dockerfile or a configuration file. No symbolic links or submodules.
7. Build to the specification. The supplied checks are only a sample of the real suites . The rest is derived from the same specification and is run after submission. A green run on the supplied checks is not proof of a stage.

CHECKS (run from any directory; each run prints where its logs are)
- One stage, development mode:   /Users/kinnu/hackathon4/factory/bin/check run toy /Users/kinnu/hackathon4/band-work/toy-result-2 1
- One stage, judging conditions: /Users/kinnu/hackathon4/factory/bin/check run toy /Users/kinnu/hackathon4/band-work/toy-result-2 1 isolated
- A scratch copy of one folder:  /Users/kinnu/hackathon4/factory/bin/check build toy /path/to/folder 1
- Repository layout and credential scan: /Users/kinnu/hackathon4/factory/bin/check repo toy /Users/kinnu/hackathon4/band-work/toy-result-2
Replace 1 with the stage number. A stage run also runs every earlier stage's checks, then the next stage's checks as a probe that is supposed to FAIL. The line that matters is the last one: "claimed stage: N on the shipped checks". The repository scan will complain that README.md, FACTORY.md and room.json are missing; the humans add those afterwards, so ignore those three complaints and fix any other.
The final inspection of every stage uses judging conditions (isolated).

TOOLING FOR THE BAND'S OWN PROBES
/Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python has pytest, httpx and playwright with Chromium. Docker is on PATH.

TIME
Hard stop: 07:00 local time. Stop after stage 2. If the clock runs out, freeze what has been inspected and report.

FINAL REPORT
When stage 2 is frozen or time is up, post one report addressed to me, then close the room.

