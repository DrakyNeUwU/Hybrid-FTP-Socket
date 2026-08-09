# 10. Testing Results

**Trạng thái:** Hoàn thành evidence Role C; phần RDT của Role B đã có verification thực tế.
**Owner:** C. **Reviewer:** A/B.
**Nguồn:** `tests/`, `../../requirement-checklist.md`, `../../evidence/`.

## Automated verification

| Command | Result | Coverage |
|---|---:|---|
| `pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q` | **45 passed / 61.13s** | Header, checksum, duplicate/reorder, fault injection, ACK loss, cancel/abort, chunk-boundary transfer |
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
