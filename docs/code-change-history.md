# Code Change History — Hybrid FTP

This history records evidence-backed changes. It does not replace end-to-end
demo evidence or `docs/project-status.md`.

## Week 1 — Foundation and module split

| Role | Work | Result |
|---|---|---|
| A | Split TCP server, parser, command handler, and session | Per-client command-processing structure |
| B | Created basic RDT header, sender, and receiver | Sequence, ACK, checksum, and FIN support |
| C | Built filesystem helpers/service and FTP root | Binary-safe file handling and basic path safety |

## Week 2 — Core functions

| Role | Work | Result |
|---|---|---|
| A | Added login, directory commands, PORT/PASV, RETR/STOR, and replies | Expanded TCP command matrix |
| B | Added retransmission, duplicate handling, and checksums | Basic Stop-and-Wait RDT |
| C | Added root confinement, atomic upload, and metadata | Filesystem cannot write outside the FTP root |

## Week 2.5 and final week — Integration and verification

The team added transfer guards, a shared `TransferContext`, strict RDT
flag/length/checksum/peer/transfer-ID validation, bounded receiver timeouts,
atomic failure/cancellation cleanup, Active/PASV end-to-end tests, concurrent
PASV-client coverage, ABOR/disconnect cleanup, LAN endpoint configuration, CLI
progress, server log redaction, total-size progress reporting, and Go-Back-N
window four with START ACK/retry.

Final evidence includes `python3 -m pytest -q` — **199 passed in 96.72s**,
protocol/fault/E2E evidence, and two-machine LAN source/server/client SHA-256
artifacts. See `docs/evidence/final-week-rdt-gbn-verification.md` and the
curated files under `docs/evidence/`.

## 10/08/2026 — Final A/C correctness pass

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| A | Unknown users could authenticate; STAT/HELP/STOU semantics were incomplete | Strict credential matching, path STAT, command HELP, STOU argument rejection | Command/framing focused suite |
| A | TCP client assumed one `recv()` equaled one reply; legacy modules failed clean imports | Buffered CRLF/multiline/listing replies; removed unused broken modules | FTP client tests, import smoke and compileall |
| C | Per-client filesystem services did not share path locks | Server-owned `FilesystemService`; all handlers borrow one lock registry | Same-file two-client APPE and handler identity tests |
| C | Active-session snapshot was emitted before handler start | Start handler before connection/session snapshot | Active sessions report `alive=True` |

Final verification: `python3 -m pytest -q` — **212 passed, 28 subtests passed
in 97.52s**. Detailed evidence: `docs/evidence/final-code-fix-verification.md`.

## 10/08/2026 — MODE S/B/C negotiation completion

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| A | MODE B/C returned 502 although the required command surface lists S/B/C | Accept S/B/C on TCP and keep selected mode per session | Command state, auth, invalid-input and session-isolation tests |
| C | MODE change needed integration proof without changing RDT contract | Added upload after MODE B and download after MODE C using the common RDT path | Focused 61 passed + 28 subtests; SHA-256 E2E assertion |

Final verification: `python3 -m pytest -q` — **213 passed, 28 subtests passed
in 108.71s**. The RDT 20-byte header, flags and Go-Back-N behavior are unchanged.

## 10/08/2026 — Role A final-fix reverted for owner handoff

| Role | Decision | Current result | Verification |
|---|---|---|---|
| A | Revert AI-applied auth/STAT/HELP/STOU, TCP reply framing, legacy cleanup and MODE B/C changes | Tasks returned to Role A; current MODE B/C reply is 502 | Fresh A implementation/evidence pending |
| C | Retain shared filesystem locks, thread/session ordering and transfer integration | C production path remains verified | Focused 24 passed in 33.80s |

Current post-handoff full regression: **205 passed in 103.08s**. Earlier
212/213-test records above describe superseded code and must not be used as the
current release claim.

## 10/08/2026 — Role C oral guide and evidence refresh

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| C | Oral material had to follow the live rubric/code and avoid filling unimplemented features from stale docs | Added a reproducible 20-section Vietnamese Word guide; its MODE B/C notes reflected the pre-pull handoff baseline and must be refreshed against the implementation below | Focused Role C suite: 24 passed in 31.37s; final Word render: 19/19 pages visually inspected |

This documentation-only change did not alter production code, public APIs or
the RDT wire format. The later Role A integration below supersedes the oral
guide's earlier MODE B/C pending note.

## 10/08/2026 — Role A functional MODE S/B/C (post-handoff)

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| A | Handoff left MODE as negotiation-only; B/C had no codec | `common/mode_codec.py` (Stream passthrough, RFC-959 Block, FTP RLE Compressed, streaming); `server/command_handler.py` `mode_cmd` (200/501/530, per-session); `server/transfer_manager.py` TransferContext mode, encode-before-RDT/decode-after-RDT, atomic `.part` kept | `tests/test_mode_codec.py`, `tests/test_commands.py` |
| A | Wire chunks must fit the RDT/receiver budget | `encode_chunks` batches Block and Compressed output to ≤1024-byte wire chunks; decoders buffer split headers/runs | `test_wire_chunks_never_exceed_budget`, one-byte-at-a-time decode tests |
| A | Client must negotiate once and count logical progress | `client/ftp_client.py` `_negotiated_mode`/`_ensure_transfer_mode`; `common/rdt_sender.py` and `common/rdt_receiver.py` report logical (decoded) bytes so progress never exceeds 100% | `tests/test_e2e_transfer.py::test_mode_progress_counts_logical_bytes` |
| A | B/C-encoded payloads must survive RDT faults and malformed streams must not commit partial files | Added mode-aware adapter fault tests (loss/corrupt/ACK-loss/duplicate/out-of-order); malformed stream → 426 with old file intact and no `.part`; cancel/disconnect mid-block tests | `tests/test_rdt_fault_injection.py`, `tests/test_transfer_manager.py` |
| A | PASV/ACTIVE × S/B/C must round-trip unchanged | E2E matrix, STOU/APPE block codec, concurrent different-mode clients, server-stop mid-B-transfer cleanup | `tests/test_e2e_transfer.py` |

## 10/08/2026 — C production audit of A-owned control/MODE path

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| A owner; C reviewer/fixer | Raw MODE could desynchronize client/server and silently decode valid-looking bytes with the wrong codec | FTPClient tracks successful raw/convenience MODE/TYPE; START payload carries logical size + MODE + TYPE and rejects mismatch with `426`; 20-byte RDT header unchanged | Crafted mismatch E2E returns `426`; E2E 14 passed + 8 subtests |
| A owner; C reviewer/fixer | Malformed client download deleted an existing destination; TCP client assumed one `recv()` per reply | Same-directory atomic `.part` + `os.replace`; persistent CRLF/multiline/listing reply buffer | `tests/test_ftp_client.py`; targeted 140 passed + 338 subtests |
| A owner; C reviewer/fixer | Unknown-user password fallback, STAT/HELP argument handling, STOU syntax and broken legacy modules contradicted the command contract | Strict credential lookup, filesystem-backed STAT, command-specific HELP, early STOU validation; removed unreferenced broken legacy modules | Command/compile/import checks; full 271 passed + 357 subtests in 192.88s |
| A/C/B shared | MODE C filler and transfer logging did not distinguish representation/logical bytes | TYPE A space filler, TYPE I NUL filler; RETR result logs logical size | Codec golden tests, transfer-manager assertions, fault 19 passed + 11 subtests |

The randomized full run initially had one MODE-B loss/corruption subtest exceed
its retry limit. The isolated rerun passed, followed by a complete all-green
run. Role B START-payload review and Role A screenshots remain pending.

Final verification: `python3 -m pytest -q` — **256 passed, 357 subtests passed
in 167.08s**. The RDT 20-byte header, flags and Go-Back-N behavior are unchanged
(RDT progress reporting order was adjusted only for logical-byte accounting).

## 11/08/2026 — Interactive terminal client

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| C | The repository exposed `demo_transfer` but had no terminal client that could execute control commands and route file commands through the real UDP/RDT path | Added `client/ftp_cli.py`: raw control commands use `FTPClient.command()`; `STOR`, `RETR`, `STOU`, and `APPE` call the existing production transfer methods using the selected PASV/ACTIVE data mode. README now documents server → login → interactive-command usage. | `python3 -m pytest tests/test_ftp_cli.py tests/test_ftp_client.py -v` — **7 passed**; `python3 -m pytest tests/test_e2e_transfer.py -v` — **14 passed + 8 subtests** |

This is a client usability addition only: no TCP reply, RDT header, MODE codec,
or A/B/C shared API contract changed.

## 11/08/2026 — Interactive demo login

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| C | Credentials were hard-coded; terminal users needed an interactive login path | Removed credential matching from the demo server. The interactive client sends visible `USER <name>` and `PASS <password>` commands, and the server accepts any non-empty pair for session access. This keeps the requirement command flow without storing credentials in source code. TCP/UDP/RDT wire behavior is unchanged. | `python3 -m pytest tests/test_ftp_cli.py tests/test_ftp_client.py tests/test_commands.py -q` — **66 passed in 0.97s**; `python3 -m pytest tests/test_e2e_transfer.py -v` — **14 passed + 8 subtests in 83.99s** |

Final regression: `python3 -m pytest -q` — **274 passed, 357 subtests passed
in 186.46s**.

## 12/08/2026 — CLI transfer-reply visibility

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| C | The interactive CLI hid the server's intermediate `150` reply, so a terminal demonstration showed only the final `226` result | `FTPClient` accepts an optional display callback for the received initial transfer reply; `ftp_cli` prints it for `STOR`, `RETR`, `STOU`, and `APPE` | Focused CLI/client suite: **7 passed in 1.86s**; localhost PASV upload/download showed `150 → 226` twice and matching source/server/download SHA-256 values |

The TCP reply lifecycle, RDT wire format and server behavior are unchanged.
Evidence: `.gitignore`, `docs/evidence/cli-transfer-replies-150-226.log`,
`docs/evidence/cli-transfer-replies-150-226-server.log`, and
`docs/evidence/cli-transfer-replies-150-226-sha256.txt`.

## 12/08/2026 — Documentation authority index

| Role | Problem | Files / behavior changed | Verification |
|---|---|---|---|
| C | Requirements, current status, report material, planning, and historical logs were spread across multiple folders with no explicit conflict rule | Added `docs/source-of-truth.md`; moved duplicate `docs/report-fix-a-c.md` to `planning/weekly-plans/`; retained `docs/screenshots.md` as a small compatibility index | Checked all Markdown headings under `docs/`, confirmed the moved report has the same content, and verified only ignored runtime artifacts were removed |

| C | The final team PDF needed a discoverable place in the documentation hierarchy | Added `docs/Hybrid_FTP_Technical_Report.pdf` to the source-of-truth submission links and restored the screenshot compatibility index to avoid delete/modify merge conflicts | Verified the PDF exists and all referenced screenshot files resolve under `docs/evidence/` |

| C | New contributors could miss the documentation authority page and final PDF from the repository landing page | Linked both items from `README.md` directory structure and documentation rules | `git diff --check` passed; README links resolve to tracked files |
