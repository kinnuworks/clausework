# Stage-4 sealed probes (examiner)
Carries every stage-1, stage-2 and stage-3 probe file unchanged (cross-cutting rules), plus test_s4_*.py.
One command runs everything against a running stage-4 deliverable. TK_S1_URL, TK_S2_URL and TK_S3_URL point at services built from
the tags stage-1-frozen, stage-2-frozen and stage-3-frozen for the export-compatibility probes. Those probes are skipped if a URL is
unset, so set all three:

    TK_BASE_URL=http://127.0.0.1:<port> TK_S1_URL=... TK_S2_URL=... TK_S3_URL=... PYTHONDONTWRITEBYTECODE=1 /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python -m pytest -q -p no:cacheprovider <this-dir>
