# 14. Requirement Compliance Matrix

**Trạng thái:** Chưa hoàn thành  
**Owner:** A. **Reviewer:** B/C. **Source:** `requirement-checklist.md`, official spec, `api-contract.md`.

| Requirement của đề | Mức độ | Role phụ trách | Report section | Code liên quan | Test/evidence | Trạng thái |
|---|---|---|---|---|---|---|
| TCP control, parser, replies, session | Basic/Advanced | A | 04 | `server/command_*`, `session.py` | parser/session/command tests; framing TODO | Implemented, not verified |
| Approved FTP command set | Basic/Advanced | A | 04 | `server/command_handler.py` | full command matrix TODO | In progress |
| UDP payload with custom RDT | Excellent | B | 05 | `common/rdt_*`, `RDTHeader.py` | production fault tests TODO | In progress |
| Binary transfer and SHA-256 | Advanced/Excellent | B/C | 05, 06, 10 | RDT + filesystem service | e2e hash TODO | Not started |
| Active and PASV | Advanced | A/B/C | 07 | command handler, `rdt_utils.py` | four-way matrix TODO | In progress |
| FTP-root/path/symlink security | Advanced | C/A | 06 | `dir_manager.py`, filesystem service | security tests/evidence TODO | Implemented, not verified |
| Atomic STOR, APPE lock, unique STOU | Advanced | C/A | 06, 08 | `filesystem_service.py`, transfer manager | production transfer TODO | Implemented, not verified |
| Multi-client isolated server | Advanced | C | 08 | `threaded_server.py`, `client_handler.py` | concurrent/shutdown tests; full suite blocked | Implemented, not verified |
| CLI state/progress and safe logging | General | C | 09 | `client/cli_display.py`, server log | live transfer log TODO | In progress |
| Unit, fault and integration tests | General/Excellent | C with A/B | 10 | `tests/` | pytest collection/e2e TODO | Blocked |
| Required diagrams and structures | Report | all | 03–08 | docs/report-parts | diagrams TODO | In progress |
| Task matrix, self/peer evaluation | Report | all | 11 | Git/docs | signed percentages TODO | Not started |
| GenAI exact prompt/raw/refinement | Report | all | 13 | `docs/genai-log-*.md` | complete logs TODO | In progress |
| Demo screenshots/logs/hash/client table | Submission | C | 10 | runtime artifacts | evidence TODO | Not started |

`Verified` is reserved for rows with real test/evidence artifacts. No row is
currently marked `Verified` in this scaffold.
