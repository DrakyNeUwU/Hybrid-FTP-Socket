# 5. Data Channel — UDP/RDT

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Mô tả header, serialization, Stop-and-Wait, ACK, retry, FIN/ABORT.  
**Requirement:** RQ-04, RQ-06, RQ-10, RQ-12. **Owner:** B. **Reviewer:** A/C.  
**Source:** `role-b-week-2.md`, `api-contract.md`.  
**Code:** `common/RDTHeader.py`, `rdt_sender.py`, `rdt_receiver.py`.

**Diagram/table:** byte-level header and sender/receiver state machines.  
**Test/evidence:** deterministic fault injection and SHA-256 logs (TODO).  
**TODO(B):** Chốt header/transfer ID và thay simulated tests bằng production-path tests.  
**DoD:** Không claim reliability until corruption, reorder, FIN ACK loss and retry limit pass.
