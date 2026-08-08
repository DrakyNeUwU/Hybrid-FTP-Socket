# 8. Concurrency and Integration

**Trạng thái:** Hoàn thành một phần
**Mục tiêu:** Thread-per-client, locks, A+B+C handoff and cleanup.  
**Requirement:** RQ-07, RQ-09, RQ-10. **Owner:** C. **Reviewer:** A/B.  
**Source:** `role-c-week-2.md`, `api-contract.md`.  
**Code:** `server/threaded_server.py`, `client_handler.py`, `transfer_manager.py`.

**Diagram/table:** thread dispatch and transfer lifecycle.  
**Test/evidence:** Ba client PASV upload + download song song đã pass, mỗi
client có session, remote filename và download directory riêng. Test kiểm tra
SHA-256 source/server/client: `docs/evidence/week-2.5-three-client.log`
(`1 passed in 5.34s`).

**Test/evidence bổ sung:** ABOR và TCP disconnect trong khi PASV worker chờ UDP
đều xóa `.part`, giữ file cũ và đưa active-session registry về đúng số client.
Toàn bộ nhóm E2E: `5 passed in 18.03s` trong
`docs/evidence/week-2.5-e2e-transfer.log`.

**TODO(C):** Thực hiện demo khác máy nếu yêu cầu nộp có mạng LAN.

**DoD:** Session/data/file isolation đã được kiểm chứng cho ba PASV client;
bounded cleanup khi ABOR/disconnect đã được kiểm chứng; cross-machine còn
pending.
