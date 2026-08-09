# Final-week Role C Verification — 09/08/2026

Environment: WSL2/Linux, Python 3, repository root `/mnt/c/Code/Code/socket`.

| Command | Result | Coverage |
|---|---:|---|
| `python3 -m pytest tests/test_rdt.py -q` | 27 passed in 14.76s | Header, checksum, duplicate/reorder, Go-Back-N four-packet window, START ACK retry |
| `python3 -m pytest tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q` | 22 passed in 70.44s | Loss/ACK loss/corruption/retry limit, atomic lifecycle, Active/PASV, ABOR/disconnect |
| `python3 -m pytest tests/test_e2e_transfer.py -q` | 6 passed in 22.63s | STOU, APPE, HASH, TYPE plus existing transfer matrix |
| `python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q` | 50 passed in 85.01s | Final streaming-window focused rerun |
| `python3 -m pytest -q` | 192 passed in 93.06s | Final full regression after streaming-safe Go-Back-N change |
| `python3 -m pytest tests/test_command_parser.py tests/test_commands.py tests/test_session.py tests/test_threaded_server.py -q` | 63 passed in 5.71s | Final Role A control/session audit after RDT integration |
| `python3 -m pytest tests/test_file_handler.py tests/test_filesystem_service.py tests/test_dir_manager.py tests/test_transfer_manager.py tests/test_rdt.py tests/test_rdt_fault_injection.py tests/test_e2e_transfer.py tests/test_cli_display.py -q` | 135 passed in 86.22s | Final focused Role C filesystem/RDT/CLI/E2E audit |
| `python3 -m pytest tests/test_cli_display.py tests/test_e2e_transfer.py -q` | 13 passed in 23.09s | Windows CP1252 CLI fallback plus FTP E2E after ACTIVE-LAN diagnosis |
| `python3 -m pytest tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_active_upload_then_download_preserves_sha256 tests/test_cli_display.py -q` | 8 passed in 5.42s | ACTIVE download UDP probe plus CLI regression |
| `python3 -m pytest tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_active_upload_then_download_preserves_sha256 -q` | 1 passed in 5.47s | ACTIVE probe sent before RETR regression |
| `python3 -m pytest -q` | 199 passed in 96.72s | Final full regression after Windows CP1252-safe CLI output and ACTIVE pre-/post-RETR UDP probes |

Physical two-machine verification (09/08/2026): PASV and ACTIVE both completed
upload and download between server `172.18.0.48` and client `172.18.0.49`.
Source/server/client SHA-256 values match for both modes; see
`final-lan-pasv-sha256.txt` and `final-lan-active-sha256.txt`. The PASV server
lifecycle is retained in `final-lan-pasv-server.log`; the ACTIVE client log
contains the final success. An ACTIVE server screenshot/log copy remains an
optional presentation artifact, not a functional blocker.
