# Stage-2 sealed probes (examiner)
Includes the stage-1 probe files unchanged (cross-cutting rules carried forward) plus test_s2_*.py.
One command runs all against a running stage-2 deliverable; TK_S1_URL points at a running frozen stage-1 service
(tag stage-1-frozen) for the stage-1 export -> stage-2 import probe:

    TK_BASE_URL=http://127.0.0.1:<port> TK_S1_URL=http://127.0.0.1:<s1port> PYTHONDONTWRITEBYTECODE=1 /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python -m pytest -q -p no:cacheprovider <this-dir>

Clause ids: S1-nn -> evidence/stage-1/clauses.md, S2-nn -> evidence/stage-2/clauses.md.
