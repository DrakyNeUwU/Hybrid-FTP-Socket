# 10. Testing Results

Final WSL2 regression: `python3 -m pytest -q` reported **199 passed in
96.72s**. Focused protocol and fault tests, transfer-manager tests, and FTP
end-to-end tests also passed. Evidence is stored in
`docs/evidence/final-week-rdt-gbn-verification.md` and the curated LAN logs and
SHA-256 artifacts.

The test suite covers TCP commands, session isolation, filesystem-root safety,
RDT checksum/retry/FIN/ABORT behavior, Active/PASV transfers, concurrent
clients, cancellation, disconnect cleanup, CLI progress, and log redaction.
