# 10. Testing Results

**Trạng thái:** Hoàn thành evidence Role C; B chọn và embed artifact vào report.
**Owner:** C. **Reviewer:** A/B.
**Nguồn:** `tests/`, `../../requirement-checklist.md`, `../../evidence/`.

## Automated verification

| Command | Result | Coverage |
|---|---:|---|
| `python3 -m pytest tests/test_rdt.py -q` | 27 passed / 14.76s | Header, checksum, duplicate/reorder, window 4, START ACK retry |
| RDT fault + transfer manager + FTP E2E | 22 passed / 70.44s | Loss, ACK loss, corruption, retry limit, atomic lifecycle, Active/PASV, ABOR/disconnect |
| `python3 -m pytest tests/test_e2e_transfer.py -q` | 6 passed / 22.63s | STOU, APPE, HASH, TYPE và transfer matrix |
| Focused C audit | 135 passed / 86.22s | Filesystem, RDT, fault, transfer, E2E, CLI |
| `python3 -m pytest -q` | **199 passed / 96.72s** | Final WSL2 full regression |

Exact commands và output được lưu tại
`../../evidence/final-week-rdt-gbn-verification.md`.

## Two-machine LAN verification

Ngày 09/08/2026, server `172.18.0.48` và client `172.18.0.49` chạy PASV lẫn
ACTIVE upload/download. Mỗi mode có SHA-256 source, FTP-root và downloaded
client giống nhau (`b57b64b...ebb90934`).

- PASV: `../../evidence/final-lan-pasv.log`, `final-lan-pasv-server.log`,
  `final-lan-pasv-sha256.txt`.
- ACTIVE: `../../evidence/final-lan-active.log`,
  `final-lan-active-sha256.txt`.

## Evidence selection

Report cuối nên dùng full-regression log, một LAN hash table mỗi mode, một
server lifecycle excerpt đã redact và screenshot PASV progress. ACTIVE server
screenshot là artifact trình bày tùy chọn, không phải điều kiện functional pass.
