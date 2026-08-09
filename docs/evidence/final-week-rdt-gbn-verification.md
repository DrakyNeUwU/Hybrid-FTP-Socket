# Final-week Role C Verification — 09/08/2026

Environment: WSL2/Linux, Python 3, repository root `/mnt/c/Code/Code/socket`.

| Command | Result | Coverage |
|---|---:|---|
| `python3 -m pytest tests/test_rdt.py -q` | 27 passed in 14.76s | Header, checksum, duplicate/reorder, Go-Back-N four-packet window, START ACK retry |
| `python3 -m pytest tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q` | 22 passed in 70.44s | Loss/ACK loss/corruption/retry limit, atomic lifecycle, Active/PASV, ABOR/disconnect |
| `python3 -m pytest tests/test_e2e_transfer.py -q` | 6 passed in 22.63s | STOU, APPE, HASH, TYPE plus existing transfer matrix |
| `python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q` | 50 passed in 85.01s | Final streaming-window focused rerun |
| `python3 -m pytest -q` | 192 passed in 93.06s | Final full regression after streaming-safe Go-Back-N change |

Not verified here: Active/PASV transfer between two physical LAN machines. That
requires the group-run server/client, firewall configuration, terminal output,
screenshots and SHA-256 artifacts; it must remain In progress until saved.
