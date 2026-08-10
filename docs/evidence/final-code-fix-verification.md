# Role C Post-Handoff Verification — 10/08/2026

## Full regression

```bash
python3 -m pytest -q
```

```text
205 passed in 103.08s (0:01:43)
```

## Full regression after Role A MODE S/B/C + reliability hardening — 10/08/2026

```bash
python3 -m pytest -q
```

```text
256 passed, 357 subtests passed in 167.08s (0:02:47)
```

## Focused Role A MODE S/B/C

```bash
python3 -m pytest tests/test_mode_codec.py tests/test_commands.py -q
python3 -m pytest tests/test_transfer_manager.py -q
python3 -m pytest tests/test_rdt_fault_injection.py -q
python3 -m pytest tests/test_e2e_transfer.py -q
```

```text
83 passed, 338 subtests passed in 0.24s
12 passed in 0.12s
19 passed, 11 subtests passed in 71.99s
13 passed, 8 subtests passed in 77.13s
```

The MODE suite covers exact `MODE S/B/C/X` replies and session state, codec
round-trips (empty, binary, text, repeated runs, boundaries 63/64 · 127/128 ·
65535/65536), wire-chunk budget ≤1024, production-path decode for
STOR/APPE/STOU, malformed-stream → 426 with no partial file, B/C-encoded
payload recovery under RDT loss/corruption/ACK-loss/duplicate/out-of-order,
cancel and disconnect mid-block with old file preserved, PASV/ACTIVE SHA-256
round-trips, concurrent different-mode clients, server-stop mid-B-transfer
cleanup, and logical-byte progress that never exceeds 100%.

## Live demo smoke — Mode B through real server + CLI (10/08/2026)

Started `server.threaded_server` on 127.0.0.1:21212, then ran
`client.demo_transfer --transfer-mode B` on a 61024-byte mixed binary file.
Progress reached exactly `100.0% (59.59 KB / 59.59 KB)` and the three artifacts
(source, server FTP root, client downloads) share one SHA-256:

```text
de3240fa0020a9419e7b32a039eea58a97aef2b48ddb17baed12841190280a68  source.bin
de3240fa0020a9419e7b32a039eea58a97aef2b48ddb17baed12841190280a68  root/smoke-b.bin
de3240fa0020a9419e7b32a039eea58a97aef2b48ddb17baed12841190280a68  client/downloads/smoke-b.bin
```

```text
Success: PASV B upload + download for smoke-b.bin
```

## Focused Role C regression

```bash
python3 -m pytest tests/test_filesystem_service.py \
  tests/test_transfer_manager.py tests/test_threaded_server.py \
  tests/test_e2e_transfer.py -q
```

```text
24 passed in 33.80s
```

This verifies the retained Role C scope: shared filesystem ownership and locks,
thread/session lifecycle, Active/PASV, same-file APPE and FTP end-to-end
behavior. It does not claim completion of the reverted Role A final-fix.

## Active-session snapshot

```text
Client connected session=S000001 ip=127.0.0.1:57756 active=1
Active sessions=[{'session_id': 'S000001', 'ip': '127.0.0.1', 'port': 57756, 'alive': True}]
Active sessions=[{'session_id': 'S000002', 'ip': '127.0.0.1', 'port': 57768, 'alive': True}]
1 passed in 1.10s
```

Command:

```bash
python3 -m pytest tests/test_threaded_server.py::TestThreadedServer::test_client_handlers_share_filesystem_and_report_alive -q -s
```

## Same-file concurrent APPE

```bash
python3 -m pytest tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_two_clients_append_same_file_without_lost_update -q
```

```text
1 passed in 3.96s
```

Both real client sessions append different 16 KiB payloads to the same remote
file. The final file must contain the base plus both complete payloads in either
serialized order; a lost update fails the test.
