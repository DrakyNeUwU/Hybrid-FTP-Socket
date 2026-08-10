# Role A Production Review — 10/08/2026

## Review baseline

Role A commit `af89a7d` implemented functional MODE S/B/C and reported 256
passing tests. The review traced each claim through the real client, TCP command,
session, TransferContext, UDP/RDT, codec and filesystem path instead of relying
on that test count.

## Issues reproduced before the fix

| Severity | Requirement | Production evidence |
|---|---|---|
| Critical | A-MODE01/03/05 | `FTPClient.command("MODE B")` left the client cached at S. A crafted S payload `40 00 03 61 62 63` was accepted as Block, returned `226`, and stored only `abc`. |
| High | A-MODE03/05 | A malformed Block download over an existing client file returned false and deleted the old destination. |
| High | Role A TCP/control handoff | The client used one `recv(4096)` per reply; split/coalesced/multiline replies had no persistent framing. |
| High | Project §2.2 control commands | An unknown username could authenticate with `123456`; STAT ignored its path; HELP ignored its argument; `STOU extra` reached endpoint validation instead of returning `501`. |
| Medium | A-MODE02/03 | Compressed filler was always NUL, so TYPE A did not use the RFC ASCII space filler; RETR logs reported encoded wire bytes instead of logical file bytes. |
| Medium | A-MODE04/06 | The E2E test named Block STOU/APPE actually ran APPE in Stream; legacy `server.server` failed to import a nonexistent `server.data_channel`. |

## Fix applied by Role C integration review

- FTPClient now buffers CRLF replies, handles FTP multiline/listing replies, and
  records successful MODE/TYPE negotiation for both convenience and raw command
  paths.
- RDT START metadata now carries logical size plus MODE and TYPE. The canonical
  `RDTHeader` remains exactly 20 bytes; only the START payload grows from 8 to
  10 bytes. Production receivers reject missing/mismatched metadata before file
  publication and map the failure to `426`.
- MODE C selects space filler for TYPE A and NUL filler for TYPE I.
- Client downloads use a same-directory `.part` and `os.replace`, preserving an
  existing destination on decode, timeout or socket failure.
- Strict authentication, STAT path metadata, HELP command usage and STOU syntax
  validation now match the shared contract.
- RETR transfer results/logging use logical file size. Broken unused legacy
  client/server modules were removed after confirming no production caller.

This does not pretend that Role A authored the review fixes. Role A owns the
affected control/MODE requirements; Role C applied the integration correction
after the production audit requested by the project owner.

## Verification

```text
wsl python3 -m pytest tests/test_ftp_client.py tests/test_mode_codec.py \
  tests/test_commands.py tests/test_transfer_manager.py tests/test_rdt.py -q
140 passed, 338 subtests passed in 18.82s

wsl python3 -m pytest tests/test_e2e_transfer.py -q
14 passed, 8 subtests passed in 83.50s

wsl python3 -m pytest tests/test_rdt_fault_injection.py -q
19 passed, 11 subtests passed in 80.57s

wsl python3 -m pytest -q
271 passed, 357 subtests passed in 192.88s
```

The first full run had one randomized MODE-B loss/corruption subtest exceed its
retry limit. Its isolated rerun passed (`1 passed, 2 subtests`), and the next
complete run passed as shown above. This flakiness is recorded rather than
hidden.

## Remaining gates

- Role B must review the backward-compatible START payload extension. The RDT
  header, flags, checksum and Go-Back-N behavior did not change.
- Role A must capture and embed the MODE B/C screenshots assigned in the final
  plan. Existing logs/hashes remain valid but do not visually prove the new
  modes.
- Contribution percentage and final team release approval remain pending.
