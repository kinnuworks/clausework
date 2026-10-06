# Stage-3 sealed probes (examiner)
Carries the stage-1 probe files and the stage-2 files (test_s2_api, test_s2_ui) unchanged. test_s2_compat is replaced by
test_s3_compat, which accepts the stage-3 additions on imported records. New: test_s3_*.py.
One command runs everything against a running stage-3 deliverable. TK_S1_URL and TK_S2_URL point at services built from tags
stage-1-frozen and stage-2-frozen for the export-compatibility probes (they are skipped if unset; set both):

    TK_BASE_URL=http://127.0.0.1:<port> TK_S1_URL=http://127.0.0.1:<s1> TK_S2_URL=http://127.0.0.1:<s2> PYTHONDONTWRITEBYTECODE=1 /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python -m pytest -q -p no:cacheprovider <this-dir>

Clause ids: S1-nn, S2-nn, S3-nn -> evidence/stage-N/clauses.md.
