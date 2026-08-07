# 9. Client, CLI and Logging

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Report network state, commands, replies, mode and progress safely.  
**Requirement:** RQ-01, RQ-08. **Owner:** C. **Reviewer:** A.  
**Source:** `api-contract.md`, `second-brain.md`.  
**Code:** `client/client.py`, `client/cli_display.py`, `server/threaded_server.py`.

**Diagram/table:** event/log schema and CLI progress sample.  
**Test/evidence:** sanitized logs with session/transfer IDs (TODO).  
**TODO(C):** Wire real progress callback and verify password/content redaction.  
**DoD:** Every displayed/logged transfer fact comes from live state.
