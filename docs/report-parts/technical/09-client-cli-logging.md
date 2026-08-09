# 9. Client, CLI and Logging

**Trạng thái:** Hoàn thành một phần
**Mục tiêu:** Report network state, commands, replies, mode and progress safely.  
**Requirement:** RQ-01, RQ-08. **Owner:** C. **Reviewer:** A.  
**Source:** `../../api-contract.md`, `../../../second-brain.md`.  
**Code:** `client/client.py`, `client/cli_display.py`, `server/threaded_server.py`.

**Diagram/table:** event/log schema and CLI progress sample.  
**Test/evidence:** `FTPClient` receives real RDT progress for upload/download;
`client.demo_transfer` renders it with `cli_display`. Server logs connection IP,
redacted PASS command, reply, session/transfer ID, active-session table, mode,
byte count and result. Command/server/E2E/CLI tests: **62 passed in 22.16s**;
log `docs/evidence/week-2.5-cli-logging.log`.

**TODO(C):** Save one manual screenshot of the progress and sanitized server
log during final demo.
**DoD:** Every displayed/logged transfer fact comes from live state.
