# 11. Contribution and Peer Evaluation

**Trạng thái:** Role C scope đã ghi; phần trăm và sign-off chờ cả nhóm.
**Owner:** A/C. **Reviewer:** all members.
**Nguồn:** `../../../planning/Socket Role.md`, Git history, role docs, evidence.

| Thành phần | Owner chính | Đóng góp Role C | Evidence |
|---|---|---|---|
| Filesystem boundary | C | FTP-root validation, binary I/O, metadata, atomic `.part`, APPE lock, STOU | filesystem/transfer tests |
| Server concurrency | C | Thread-per-client, active-session registry, safe stop/unregister | threaded/E2E tests |
| Integration | C | `TransferContext` handoff, cleanup mapping, Active/PASV E2E | transfer manager và E2E logs |
| Reliability extension | C, B review | Go-Back-N window 4, START ACK/retry, bounded retransmission | final RDT verification |
| Demo/evidence | C | LAN PASV/ACTIVE, SHA-256, progress/logging evidence | `docs/evidence/final-*` |
| Report support | C | Technical drafts 01/03/06/08/09 và testing evidence | report-parts workspace |

Peer evaluation percentage phải do A/B/C cùng chốt, tổng đúng 100%, gắn commit
hash/review record và sign-off. Không suy đoán percentage chỉ từ số file hoặc
số test.
