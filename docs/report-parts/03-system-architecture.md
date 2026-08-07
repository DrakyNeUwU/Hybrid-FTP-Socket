# 3. System Architecture

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Mô tả client/server, TCP–UDP–filesystem boundary và lifecycle.  
**Requirement:** RQ-01, RQ-03, RQ-04, RQ-07, RQ-10. **Owner:** C. **Reviewer:** A/B.  
**Source:** `api-contract.md`, role A/B/C docs.  
**Code:** `server/threaded_server.py`, `server/client_handler.py`, `common/`.

**Diagram/table:** TCP+UDP sequence, ownership table, context objects.  
**Test/evidence:** live sequence log (TODO).  
**TODO(C):** Vẽ diagram khớp wire contract được A/B xác nhận.  
**DoD:** Không có arrow ownership/cleanup trái với API contract.
