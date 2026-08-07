# 7. Active and PASV Modes

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Chốt UDP endpoint negotiation and lifecycle.  
**Requirement:** RQ-02, RQ-05, RQ-10. **Owner:** A/B. **Reviewer:** C.  
**Source:** `api-contract.md`, `tuan-2-chi-tiet.md`.  
**Code:** `server/command_handler.py`, `common/rdt_utils.py`.

**Diagram/table:** PORT/PASV sequence and endpoint ownership table.  
**Test/evidence:** Active/PASV upload/download matrix (TODO).  
**TODO(A/B):** Xác nhận advertised host, peer policy, socket replacement and real UDP trace.  
**DoD:** Four transfer directions pass with cleanup and no stale endpoint.
