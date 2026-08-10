# Role C Post-Handoff Verification — 10/08/2026

## Full regression

```bash
python3 -m pytest -q
```

```text
205 passed in 103.08s (0:01:43)
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
