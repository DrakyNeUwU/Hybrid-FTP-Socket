# 4. Control Channel — TCP

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Giải thích parser, session, command và FTP replies.  
**Requirement:** RQ-02, RQ-03, RQ-05, RQ-10. **Owner:** A. **Reviewer:** C.  
**Source:** `../../report_role_a_week2.md`, `../../api-contract.md`.  
**Code:** `server/command_parser.py`, `command_handler.py`, `session.py`, `ftp_reply.py`.

**Diagram/table:** USER/PASS/QUIT sequence; command/reply table.  
**Test/evidence:** split/coalesced CRLF and all-command reply trace (TODO).  
**TODO(A):** Bổ sung framing và đánh dấu command chưa nối RDT, không ghi skeleton là done.  
**DoD:** Reply mapping và session reset khớp API, có test thật.
