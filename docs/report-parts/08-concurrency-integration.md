# 8. Concurrency and Integration

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Thread-per-client, locks, A+B+C handoff and cleanup.  
**Requirement:** RQ-07, RQ-09, RQ-10. **Owner:** C. **Reviewer:** A/B.  
**Source:** `role-c-week-2.md`, `api-contract.md`.  
**Code:** `server/threaded_server.py`, `client_handler.py`, `transfer_manager.py`.

**Diagram/table:** thread dispatch and transfer lifecycle.  
**Test/evidence:** >=3 clients, conflict, disconnect and shutdown logs (TODO).  
**TODO(C):** Nối production adapters and prove no global lock during UDP wait.  
**DoD:** Session/data/file isolation and bounded cleanup verified.
