# 10. Testing Results

Current post-handoff WSL2 regression: `python3 -m pytest -q` reported **205
passed in 103.08s**. Focused Role C filesystem, transfer-manager, threaded-server
and FTP E2E tests reported **24 passed in 33.80s**. Protocol/fault tests and FTP
end-to-end tests also passed. Evidence is stored in
`docs/evidence/final-code-fix-verification.md` and the curated LAN logs and
SHA-256 artifacts.

The test suite covers TCP commands, session isolation, filesystem-root safety,
RDT checksum/retry/FIN/ABORT behavior, Active/PASV transfers, concurrent
clients, cancellation, disconnect cleanup, CLI progress, and log redaction.
The current pass covers shared server filesystem locks and two-client same-file
APPE without lost updates. Strict authentication, buffered TCP replies,
command-specific STAT/HELP/STOU behavior and functional MODE B/C are pending
fresh implementation/evidence from Role A.
