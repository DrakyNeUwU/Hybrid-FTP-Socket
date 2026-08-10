# 10. Testing Results

Current full regression after the Role A MODE implementation:
`python3 -m pytest -q` reported **256 passed, 357 subtests in 167.08s** (the
post-handoff baseline was 205 passed in 103.08s). Focused Role C filesystem,
transfer-manager, threaded-server and FTP E2E tests reported **24 passed in
33.80s**. MODE-specific evidence: codec/command suite **83 passed, 338
subtests**; transfer-manager mode integration **12 passed**; RDT fault
injection over B/C-encoded payloads **19 passed, 11 subtests**; FTP E2E mode
matrix **13 passed, 8 subtests**. Evidence is stored in
`docs/evidence/final-code-fix-verification.md` and the curated LAN logs and
SHA-256 artifacts.

The test suite covers TCP commands, session isolation, filesystem-root safety,
RDT checksum/retry/FIN/ABORT behavior, Active/PASV transfers, concurrent
clients, cancellation, disconnect cleanup, CLI progress, log redaction, shared
server filesystem locks, two-client same-file APPE without lost updates, and
functional MODE S/B/C with PASV/ACTIVE SHA-256 round-trips, STOU/APPE codec
paths, concurrent different-mode clients, logical-byte progress that never
exceeds 100%, B/C payload recovery under loss/corruption/ACK-loss/duplicate/
out-of-order, cancel and disconnect mid-block with the old file preserved, and
server-stop mid-B-transfer cleanup. Strict authentication, buffered TCP replies
and command-specific STAT/HELP/STOU behavior remain pending fresh
implementation/evidence from Role A.
