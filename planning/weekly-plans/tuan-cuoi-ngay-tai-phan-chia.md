# FINAL WEEK — HOÀN TẤT PROJECT 1: HYBRID FTP

> **Bảng điều hành final week.** Trạng thái dự án duy nhất nằm tại
> `docs/project-status.md`; checklist trước nộp ở `docs/requirement-checklist.md`.

## Dashboard họp mỗi tối

| Task | DRI cuối | Deadline | Trạng thái | Blocker / evidence |
|---|---|---|---|---|
| Command/E2E must-submit | A | Trước report freeze | In progress | AI-applied A fixes reverted; A must implement and provide fresh evidence |
| RDT must-submit | B | Trước report freeze | Done | RDT/fault tests trong full suite; hash Active/PASV |
| LAN two-machine evidence | C | Khi có hai máy | Done | PASV/ACTIVE upload+download; source/server/client SHA-256 và server log khớp |
| Final report + checklist + technical audit | B | Trước release check | In progress | C audit passed; A implementation/audit, contribution and Git release pending |
| Oral preparation + Git release check | B | Ngày trước nộp | In progress | Oral pack sẵn sàng; Git release check chưa có evidence |
| C-F01 Excellent flow/congestion control | C | Trước C-F02/C-F03 | Done | Go-Back-N window 4; 212 full tests + 28 subtests; B-F01 wire-contract verification complete |

**Thời gian:** 09/08/2026–12/08/2026  
**Mục tiêu:** hoàn tất, kiểm chứng, demo, nộp và vấn đáp được toàn bộ Project 1.
Không tick task chỉ vì code đã có; phải có test, log, hash hoặc demo thật.

**Nguồn chuẩn:**

- `planning/reference/Project1_SocketProgramming_2026.md` §§1–4.5 — requirement và tiêu chí nộp.
- `planning/Socket Role.md` — ownership gốc và format tuần 3.
- `planning/weekly-plans/tuan-1-chi-tiet-socket.md`,
  `planning/weekly-plans/tuan-2-chi-tiet.md`,
  `planning/weekly-plans/tuan-2.5-fix.md` — carry-over.
- `docs/api-contract.md`, `docs/project-status.md`, `docs/requirement-checklist.md`
  — contract/trạng thái cần cập nhật theo code cuối.

## 1. Trạng thái đầu tuần — fact đã có evidence

- `[x]` TCP control + session, filesystem sandbox, Active/PASV localhost,
  Go-Back-N window 4, hash, ABOR/disconnect cleanup, 3 client PASV đồng thời.
- `[x]` Post-handoff full WSL2 test: **205 passed in 103.08s**; Role C focused:
  **24 passed in 33.80s**; E2E localhost:
  **6 passed in 22.63s**.
- `[x]` Progress CLI, server log che password và hash/log PASV đã có.
- `[!]` `MODE S` trả `200`; `MODE B/C` hiện trả `502`. Functional block và
  compressed algorithms được trả lại Role A triển khai/test.
- `[x]` C-F01 dùng Go-Back-N window 4; protocol/fault/E2E/full regression đã
  pass. B wire-contract review được ghi nhận tại B-F01.
- `[x]` START metadata có ACK và retry hữu hạn; retry/lifecycle được kiểm tra
  trực tiếp trong `tests/test_rdt.py`.
- `[ ]` Chưa có contribution decision và clean Git release check; oral pack đã
  sẵn sàng, dry run không là gate nội bộ.

## 2. Carry-over / Outstanding Tasks

| Carry-over | Source | Trạng thái đầu tuần | Xử lý final week |
|---|---|---|---|
| `MODE S/B/C` command review | Week 2, requirement §2.2 | S có; B/C trả 502 | `A-F01`; Role A implement codec + command/session/E2E tests |
| Congestion/flow control hoặc equivalent | Requirement §1.3 Excellent | Go-Back-N window 4 đã chốt | `C-F01` |
| START metadata reliability | Role B Week 2 §4 | START ACK/retry hữu hạn đã chốt | `C-F01`, B review contract/test |
| Transfer RDT core heavy coding | Week 1/2 Role B | Core đã integrate; phần mở rộng chuyển ownership | **Replaced by:** `C-F01`; B review contract/docs/test black-box trong `B-F01` |
| Active/PASV LAN thật | Week 2.5 Role C | Launcher có, chưa có evidence | `C-F02` (evidence nâng chất lượng, không phải gate đề bài) |
| Full command lifecycle evidence | Week 2 | Unit nhiều, E2E chưa phủ toàn matrix | `A-F02` + `C-F02` |
| Report placeholders/stale claims | Week 1/2 report | Nội dung report đã ghép; final claim review và A/C sign-off còn chờ | `B-F02`, review theo owner A/C |
| GenAI, peer %, task matrix, evidence nhúng report | Requirement §2.4, §4.5 | Chưa chốt cuối | `B-F02` + `C-F03` |
| Oral và live-code readiness | Week 3 | Oral pack/locator đã có; dry run không là gate nội bộ | `B-F03` + toàn nhóm |

## 3. Dependency map

```text
A-F01 command/mode review ─┐
                           ├─> C-F01 Excellent RDT + flow control
B-F01 contract test ───────┘                    │
                                         ├─> A-F02 command matrix E2E
                                         ├─> C-F02 LAN + transfer matrix
                                         └─> C-F03 final regression/evidence
                                                    │
                         A/C technical inputs ─> B-F02 final report
                                                    │
                                      B-F03 oral/live-code dry run
                                                    │
                                           Final completion checklist
                                                    │
                                                Submission
```

**Quy tắc dependency:** không merge RDT flow-control chỉ vì unit test pass;
phải qua integration/fault-injection test trước khi update report/evidence.

---

## 4. Role A — TCP control, command lifecycle và mode negotiation

### [ ] A-F01 — Rà command compliance và `MODE` theo requirement

**Owner:** Role A  
**Dependency:** Không có; C-F01 chỉ nhận context RDT hiện có.  
**Input / prerequisite:** `Session.transfer_mode`, `CommandHandler.mode_cmd`,
`TransferContext`, `docs/api-contract.md`.
**Related requirement:** §2.2 `MODE {S|B|C}`, §2.3 reply codes, §2.4 data
structures.

**Goal**

Role A hoàn thiện command compliance và triển khai MODE B/C có semantics thật;
không chỉ đổi reply. Mode encoding nằm trước RDT và decoding nằm sau RDT để giữ
nguyên wire header B/C.

**Actions**

- [x] Xác nhận `MODE S` state/reply/transfer path; test input invalid và session isolation.
- [ ] Role A implement `MODE B` block framing và `MODE C` compression/decompression.
- [x] Bổ sung unit tests valid/invalid/unauthenticated/state isolation cho S/B/C.
- [x] Cập nhật phần control/session/command map trong report và GenAI log A.

**Review / Success checklist**

- [ ] `MODE S/B/C` trả reply đúng và cập nhật đúng session; invalid/unauthenticated
  input trả `501`/`530`.
- [ ] Một session đổi mode không ảnh hưởng session khác.
- [ ] Command matrix ghi rõ reply và status thực tế của MODE B/C.

**Definition of Done**

- [ ] Code + unit/E2E/fault tests pass.
- [ ] B/C round-trip giữ SHA-256 ở Active/PASV và không phá RDT retry.
- [ ] API contract/report/GenAI log A được Role A cập nhật.

**Output / Deliverable:** code Role A, tests command/session, contract mode và
phần report control channel.

**Oral knowledge:** giải thích MODE khác Active/PASV; S/B/C là control-plane
negotiation labels còn file payload dùng chung custom UDP/RDT data path.

### [ ] A-F02 — Command matrix qua TCP và transfer lifecycle cuối

**Owner:** Role A  
**Dependency:** A-F01; C-F01 cho transfer mode; `FilesystemService` C.  
**Input / prerequisite:** command handler hiện có, FTP reply mapping, test command
unit hiện tại.
**Related requirement:** §2.2 toàn bộ command, §2.3 reply codes, §4.5 live demo.

**Goal**

Chứng minh mọi command được đề duyệt parse/validate/reply đúng qua TCP; các
command transfer chạy xuyên suốt thay vì chỉ có unit dispatch.

**Actions**

- [x] Lập command matrix 28 lệnh: happy path, invalid syntax/state, expected reply.
- [x] Bổ sung TCP-level tests cho auth, directory, metadata, rename, LIST/NLST,
  HELP, PORT/PASV và MODE S/B/C.
- [x] Phối hợp C thêm E2E cho STOR/RETR/STOU/APPE/HASH/ABOR ở mode cần thiết.
- [x] Xác nhận `LIST/NLST` luôn trả text qua TCP; chỉ file payload đi UDP/RDT.
- [x] Ghi evidence/reply matrix vào report phần A và `docs/requirement-checklist.md`.

**Review / Success checklist**

- [x] Không command nào trong §2.2 thiếu handler hoặc reply ba chữ số.
- [x] `150 → 226` chỉ xuất hiện sau transfer thực; lỗi map đúng 4xx/5xx.
- [x] Matrix có link đến test/log, không dùng mô tả suông.

**Definition of Done**

- [x] Test matrix pass trên WSL2.
- [x] C review integration transfer; B review traceability matrix.
- [x] Report A và requirement checklist phản ánh code cuối.

**Output / Deliverable:** command/reply test matrix, source/tests, evidence TCP.

**Oral knowledge:** mô tả từ `COMMAND\r\n` qua parser/session/handler đến reply;
phân biệt 150, 226, 425, 426, 450 và 550.

---

## 5. Role B — protocol traceability, report, testing support và oral

### [x] B-F01 — RDT protocol contract verification và wire-trace test

**Owner:** Role B  
**Collaborators:** C review implementation; A review context/reply boundary.  
**Dependency:** A-F01 contract mode, C-F01 protocol implementation.  
**Input / prerequisite:** `common/RDTHeader.py`, sender/receiver, `TransferContext`,
`docs/api-contract.md`, fault-injection tests.
**Related requirement:** §§1.2, 2.1, 2.4 data structures, RDT Excellent level.

**Goal**

Sở hữu một verification artifact kỹ thuật chứng minh documentation RDT khớp wire
protocol thật, gồm START, DATA/ACK, FIN/ABORT, total bytes và mode behavior.

**Actions**

- [x] Viết test black-box nhẹ cho header/context/lifecycle; không sửa core RDT.
- [x] Kiểm tra START được xác nhận hoặc retry hữu hạn theo thiết kế C-F01.
- [x] Kiểm tra MODE reply/status được documentation phản ánh đúng, không có
  claim data-path B/C nếu code chưa implement.
- [x] Rà bảng byte-level: field, offset, length, endian, checksum coverage,
  transfer ID, flags, timeout/window policy.
- [x] Cập nhật `docs/api-contract.md`,
  `docs/report-parts/technical/05-data-channel-rdt.md` và GenAI log B.

**Review / Success checklist**

- [x] Test thất bại nếu header/doc contract bị lệch implementation.
- [x] Có trace hoặc output chứng minh START → DATA/ACK → FIN/ACK/ABORT.
- [x] C review test không mock sai production behavior.

**Definition of Done**

- [x] Test mới pass cùng full suite.
- [x] Protocol documentation không còn TODO/stale claim.
- [x] B tự giải thích được từng field header và một retry trên live code.

**Output / Deliverable:** RDT contract test, header/state-machine documentation,
protocol trace evidence.

**Oral knowledge:** UDP không reliable; Stop-and-Wait/window, checksum, sequence,
ACK, retry, duplicate/out-of-order, START, FIN và ABORT hoạt động thế nào.

### [~] B-F02 — Hoàn thiện report 7 section, requirement traceability và submission pack

**Owner:** Role B  
**Collaborators:** A duyệt control/command; C duyệt filesystem/concurrency/evidence.  
**Dependency:** A-F02, B-F01, C-F02, C-F03.  
**Input / prerequisite:** `docs/report.md`, `docs/report-parts/technical/`,
`docs/report-parts/submission/`, `docs/project-status.md`,
`docs/requirement-checklist.md`, evidence, code-change history và Git log.
**Related requirement:** §2.4 (7 report sections), §§4.2–4.5.

**Goal**

Tạo report thống nhất, đúng code cuối, có map mỗi requirement đến code/test/evidence
và đủ thông tin cho examiner kiểm tra đóng góp.

**Quy tắc merge bắt buộc**

Role B phải trực tiếp tổng hợp nội dung còn hợp lệ từ
`docs/report-parts/technical/01–09` và `docs/report-parts/submission/10–13`
vào một bản nộp duy nhất là `docs/report.md`. “7 section” là bảy section bắt
buộc theo đề §2.4, **không phải** chỉ chọn bảy trong mười bốn file draft để
merge. `submission/14-requirement-compliance.md` chỉ là mapping/reference lịch
sử; không dùng nó để copy claim trạng thái cuối.

**Actions**

- [x] **Merge/reconciliation:** đã rà từng report-part `01–13`, merge hoặc
  đối chiếu nội dung vào đúng section của `docs/report.md`; không để report chỉ
  link sang draft thay cho nội dung examiner cần đọc.
- [x] Đối chiếu bản merge với đủ bảy section §2.4: application scenario/protocol
  interaction, project-wide data structures, functional workflows, task
  assignment matrix, self/peer evaluation, GenAI appendix và demo evidence.
- [ ] Sau merge, rà lại caption/link ảnh-log-hash và requirement traceability;
  xin A/C technical audit cho phần thuộc ownership của họ.
- [x] Thay toàn bộ placeholder và câu "pending/unverified" cũ trong report.
- [x] Ghép sequence diagram TCP+UDP, header/session structures, 4 flowcharts,
  task assignment matrix, self/peer evaluation, GenAI appendix, demo evidence.
- [x] Tạo final requirement traceability: §1/§2.1/§2.2/§2.3/§2.4/§4.5 → task,
  file, test/evidence.
- [x] Chỉ dùng `docs/report-parts/submission/14-requirement-compliance.md` làm
  bảng mapping/reference để đối chiếu độ phủ requirement; mọi claim trạng thái
  cuối phải lấy từ `docs/project-status.md` và `docs/requirement-checklist.md`.
- [x] Chuẩn hoá kết quả test mới nhất, ngày chạy, command chạy và limitations thật.
- [ ] Chốt self-assessment của A/B/C, contribution percentage tổng chính xác 100%
  và ngày quyết định của cả nhóm.

**Review / Success checklist**

- [x] Cả bảy section §2.4 có nội dung thật, không chỉ link hoặc TODO.
- [x] Diagram/tables trùng code cuối, đặc biệt RDT header 20 byte và mode flow.
- [x] Mỗi ảnh/log/hash có caption nói rõ nó chứng minh gì.

**Definition of Done**

- [ ] A và C sign-off phần thuộc ownership của mình bằng record release checklist.
- [ ] B xác nhận report, status và checklist không còn claim trái evidence.
- [ ] Report có thể xuất/nộp sau khi các gate sign-off và release được tick.

**Checklist đóng các khoảng thiếu của report (Role B)**

- [ ] **§2.2 Session Structure:** thay snippet 3 field cũ bằng cấu trúc `Session`
  cuối cùng: `session_id`, `username`, `is_logged_in`, `ftp_root`,
  `current_dir`, `data_mode`, `data_host`, `data_port`, `data_socket`,
  `rename_from`, `current_transfer`, `transfer_cancel_event` và transfer ID.
  Xóa câu tương lai “Integration will extend...”; đối chiếu tên field với
  `server/session.py` trước khi ghi.
- [ ] **§6 GenAI mandatory appendix:** giữ link tới logs A/B/C, đồng thời yêu cầu
  A và B bổ sung các **exact prompt** và **raw AI output** cho các lần dùng GenAI
  quan trọng của họ. B chỉ tổng hợp/kiểm tra, không tự dựng prompt hoặc output
  thay cho A/B.
- [ ] **§7 demo evidence:** nhúng trực tiếp (không chỉ ghi path) các đoạn evidence
  ngắn: upload/download từ `final-lan-pasv.log` hoặc `final-lan-active.log`;
  SHA-256 PASV/ACTIVE từ `final-lan-*-sha256.txt`; IP, commands và
  `Active sessions=[...]` từ `final-lan-server.log`; concurrent PASV result từ
  `week-2.5-three-client.log`. Chỉ nhúng screenshot nếu chọn ảnh sạch; log/hash
  là evidence chính.
- [ ] **§5 contribution:** sau khi A/B/C quyết định thật, điền percentage từng
  người, tổng đúng 100%, ngày quyết định và record đồng thuận. Không tự suy ra
  số phần trăm.
- [ ] Rà lần cuối `docs/report.md`, `docs/project-status.md` và
  `docs/requirement-checklist.md`: mọi claim phải có evidence; chạy
  `git diff --check`. Chỉ ghi release-ready sau khi Git worktree sạch.

**Output / Deliverable:** report final, requirement traceability, task matrix,
self/peer evaluation, GenAI appendix và evidence index.

**Oral knowledge:** giải thích kiến trúc end-to-end, ownership ba role, test
strategy, rủi ro đã xử lý và evidence tương ứng.

### [x] B-F03 — Oral và live-code locator

**Owner:** Role B  
**Collaborators:** A và C tham gia/đánh giá chéo.  
**Dependency:** B-F01, B-F02 và code final ổn định.  
**Input / prerequisite:** code final, report final, Git history.
**Related requirement:** rubric §3 (Oral 30%, Live Coding 20%), §4.1–4.4.

**Goal**

Mỗi thành viên hiểu system flow và locate/fix được phần live code của mình;
Role B có material kỹ thuật rõ ràng, không chỉ làm hành chính.

**Actions**

- [x] Chuẩn bị oral pack: 20 câu hỏi, đáp án ngắn, file/line locator và câu hỏi phản biện.
- [x] Rà Git log/GenAI logs để mỗi người có locator giải thích thay đổi của mình.
- [x] Dry run và evidence dry run không là gate nội bộ; mỗi thành viên tự dùng oral
  pack để chuẩn bị cho oral defense/living coding theo rubric.

**Oral pack — chuẩn bị, chưa phải evidence dry run**

| # | Câu hỏi | Đáp án ngắn cần trình bày | Locator |
|---:|---|---|---|
| 1 | Vì sao control dùng TCP còn file payload dùng UDP/RDT? | TCP giữ command/reply theo thứ tự; UDP giảm phụ thuộc transport và RDT tự thêm reliability. | `docs/api-contract.md`; `server/transfer_manager.py:40` |
| 2 | Header RDT gồm gì và dài bao nhiêu? | 20 byte: transfer ID, sequence, ACK, flags, payload length, checksum; network byte order. | `common/RDTHeader.py:5` |
| 3 | Header bị sai flags hoặc length được chặn ở đâu? | Validate flags và packet length trước khi xử lý payload. | `common/RDTHeader.py:39`, `:66` |
| 4 | START giải quyết vấn đề gì? | Gửi metadata/total bytes trước DATA và phải nhận ACK(0). | `common/rdt_sender.py:237`, `:260` |
| 5 | Nếu ACK START bị mất thì sao? | Sender timeout và retry hữu hạn; quá giới hạn thì fail/cleanup. | `common/rdt_sender.py:260` |
| 6 | Go-Back-N window 4 hoạt động thế nào? | Tối đa bốn DATA in-flight; ACK tích lũy mở cửa sổ. | `common/rdt_sender.py:153` |
| 7 | Mất DATA hoặc ACK thì sao? | Timeout retransmit từ packet chưa ACK đầu tiên, không treo vô hạn. | `common/rdt_sender.py:153` |
| 8 | Receiver xử lý packet duplicate/out-of-order thế nào? | Chỉ nhận next expected sequence và re-ACK cumulative sequence. | `common/rdt_receiver.py:170` |
| 9 | Checksum bảo vệ phần nào? | Header (checksum đặt 0 khi tính) và payload; packet lỗi bị bỏ. | `common/RDTHeader.py:66` |
| 10 | FIN grace là gì? | Receiver còn lắng nghe ngắn để ACK lại FIN trùng khi ACK cuối bị mất. | `common/rdt_receiver.py:238` |
| 11 | ABORT khác FIN thế nào? | FIN kết thúc thành công; ABORT hủy transfer và cleanup lỗi. | `common/rdt_receiver.py:170` |
| 12 | MODE S/B/C hiện hỗ trợ đến đâu? | S trả 200; B/C đang 502 và là task Role A. | `server/command_handler.py` |
| 13 | PORT và PASV khác nhau ở đâu? | PORT công bố endpoint client; PASV công bố endpoint server qua TCP control. | `server/command_handler.py:258`, `:296` |
| 14 | Chặn path traversal bằng cách nào? | Resolve path rồi validate nằm trong FTP root trước thao tác. | `common/dir_manager.py:84` |
| 15 | STOR an toàn khi bị hủy giữa chừng thế nào? | Ghi `.part`, chỉ replace atomically khi thành công; lỗi thì cleanup. | `common/filesystem_service.py:95`, `server/transfer_manager.py:40` |
| 16 | APPE/STOU tránh đụng file ra sao? | APPE dùng lock theo path; STOU tạo unique name. | `common/filesystem_service.py:197`, `:207` |
| 17 | Server nhiều client tránh race/shutdown lỗi thế nào? | Registry có lock, snapshot trước cleanup và unregister an toàn. | `server/threaded_server.py:53`, `:165`, `:212` |
| 18 | Active session/progress được quan sát ở đâu? | Server log snapshot session; client hiển thị progress an toàn encoding. | `server/threaded_server.py:254`, `server/client_handler.py:137` |
| 19 | Bằng chứng LAN chứng minh gì? | ACTIVE/PASV hai máy và SHA-256 source/server/client khớp. | `docs/evidence/final-lan-*-sha256.txt` |
| 20 | Test cuối có ý nghĩa gì? | Post-handoff 205 passed; C focused 24 passed; A cần evidence mới. | `docs/evidence/final-code-fix-verification.md` |

## Role B Final Checklist

| Task | Status | Notes |
|---|---|---|
| B-F01: RDT protocol contract verification | Done | START/ACK retry, Go-Back-N, FIN/ACK, ABORT verified with production tests |
| B-F01: Wire-trace documentation | Done | `docs/report-parts/technical/05-data-channel-rdt.md` explicitly documents the trace |
| B-F02: Merge/reconcile `report-parts/01–13` into `docs/report.md` | In progress | B phải tổng hợp một report nộp được; 7 section là tiêu chí đề bài, không phải số draft được merge |
| B-F02: Remove placeholders and stale claims | In progress | Chỉ đóng sau khi bản report đã merge được đối chiếu với status/checklist/evidence |
| B-F02: Update API contract and GenAI log | Done | `docs/api-contract.md` and `docs/genai-log-b.md` were updated |
| B-F02: Final report technical audit | In progress | Technical claims audited; Session, GenAI appendix and embedded §7 evidence remain |
| B-F03: Oral / live-code locator preparation | Done | 20-question oral pack ready; dry run intentionally not a gate |
| A/C technical audit | In progress | C passed; A final implementation and fresh audit pending |
### [x] C-F01 — Hoàn tất RDT Excellent: Go-Back-N reliable lifecycle và flow control

**Owner:** Role C  
**Collaborators:** A cung cấp mode/context; B verify contract/test.  
**Dependency:** B-F01 wire-contract verification; implementation bắt đầu trên
baseline hiện tại.
**Input / prerequisite:** RDT sender/receiver, `TransferManager`, filesystem
atomic lifecycle, fault-injection suite.
**Related requirement:** §§1.2, 1.3 Excellent, 2.1, 2.4 flowcharts.

**Goal**

Hoàn tất đúng ba đặc tính Excellent của data path: RDT custom reliable đã có,
Go-Back-N sliding window **4 packet** có giới hạn và SHA-256 end-to-end vẫn đúng.

**Actions**

- [x] START ACK + retry hữu hạn sao cho receiver biết metadata; fail phải trả lỗi
  hữu hạn và cleanup đúng.
- [x] Implement Go-Back-N: tối đa 4 packet in-flight, ACK tích lũy, timeout
  retransmit từ packet chưa ACK đầu tiên và fallback/error handling rõ ràng.
- [x] Giữ nguyên RDT header wire layout hiện có; không đổi command grammar hoặc
  TCP reply ownership. Chỉ đổi ACK/START semantics khi cập nhật contract.
- [x] Bảo toàn peer lock, transfer ID, cancellation, FIN grace, `.part` cleanup.
- [x] Thêm fault injection loss/corruption/reorder/window exhaustion và binary,
  empty, chunk-boundary SHA-256 tests.
- [x] Cập nhật contract, các phần report kỹ thuật Role C (`03`, `08`) và GenAI
  log C; shared report diagrams vẫn cần B tổng hợp/review.

**Review / Success checklist**

- [x] File text, binary, empty và chunk boundary round-trip đúng SHA-256.
- [x] Loss/corruption/duplicate/out-of-order không ghi duplicate hoặc treo vô hạn.
- [x] Window bị giới hạn; không flood UDP và không giữ global/session lock khi chờ ACK.
- [x] ABOR/disconnect giữa transfer giữ file cũ, xóa `.part`.

**Definition of Done**

- [x] Unit + fault-injection + FTP integration tests pass.
- [x] A mode selection review và B wire-contract verification đã được ghi nhận
  tại A-F01/B-F01.
- [x] Không có regression Active/PASV; full final regression đạt 212 tests + 28 subtests.

**Output / Deliverable:** production RDT/data-pipeline code, test suite,
state-machine docs và reliability evidence.

**Oral knowledge:** window giới hạn in-flight packets thế nào; checksum, ACK,
retry và hash end-to-end phối hợp để giữ file đúng ra sao.

### [~] C-F02 — Final transfer matrix và LAN demo hai máy

**Owner:** Role C  
**Collaborators:** A xử lý command/reply lỗi; B kiểm tra protocol/evidence.  
**Dependency:** C-F01 hoàn tất và A-F02 command lifecycle ổn định.
**Input / prerequisite:** hai máy cùng LAN, IPv4 server, firewall TCP/UDP,
`README.md` launcher.
**Related requirement:** §§1.1–1.3, 2.1, 2.2, 4.5.2–4.5.3.

**Goal**

Chứng minh project chạy end-to-end ngoài loopback và phủ các transfer/file edge
cases đủ để demo, review và submit.

**Actions**

- [x] PASV hai máy LAN đã chạy; client output/progress lưu tại
  `docs/evidence/final-lan-pasv.log`, SHA-256 khớp tại
  `docs/evidence/final-lan-pasv-sha256.txt`, lifecycle server tại
  `docs/evidence/final-lan-pasv-server.log`.
- [x] ACTIVE hai máy LAN đã chạy; client log và SHA-256 source/server/client
  khớp tại `docs/evidence/final-lan-active.log` và
  `docs/evidence/final-lan-active-sha256.txt`.
- [x] Automated E2E covers STOU, APPE, HASH, TYPE, ABOR/disconnect and three
  concurrent PASV clients; remaining manual presentation cases are optional.
- [ ] Chụp server active-session table, command/reply, progress 0→100%, hash,
  concurrent sessions.
- [x] README includes clean LAN launcher and TCP/UDP firewall guidance.

**Review / Success checklist**

- [x] PASV LAN dùng endpoint ngoài loopback; client/server/download SHA-256 khớp.
- [x] Hash source/server/download bằng nhau cho cả PASV-LAN và ACTIVE-LAN.
- [x] Command/result và mode/hash evidence are recorded; the ACTIVE server-log
  copy is still useful for presentation, but not required to prove success.

**Definition of Done**

- [x] E2E matrix pass; no technical integration blocker remains for Role C.
- [ ] Evidence is stored under `docs/evidence/`; B still needs to select/embed
  it in the final report.
- [ ] A/B review demo log trước khi tick.

**Output / Deliverable:** LAN evidence, final E2E tests/log/hash,
README run guide.

**Oral knowledge:** flow TCP control + UDP data, khác nhau Active/PASV, cách
firewall/advertised IP ảnh hưởng PASV.

### [~] C-F03 — Final regression, clean repository và submission readiness

**Owner:** Role C  
**Collaborators:** A/B review code/docs ownership.  
**Dependency:** A-F02, B-F01, C-F01, C-F02.  
**Input / prerequisite:** final branch, report, evidence directory, `.gitignore`.
**Related requirement:** §§2.1, 2.4, 4.2–4.5.

**Goal**

Đảm bảo repo chạy từ đầu trên môi trường sạch, chỉ chứa deliverable cần nộp và
trạng thái/status/history không nói quá evidence.

**Actions**

- [x] Chạy full suite WSL2/Linux; lưu command, result vào
  `docs/evidence/final-week-rdt-gbn-verification.md`.
- [x] Chạy final server/client live demo trên máy LAN thứ hai (PASV và ACTIVE).
- [x] Rà `.gitignore` và Git status: demo binaries/downloads/cache bị ignore;
  curated `docs/evidence/final-*.log` được giữ cho submission.
- [x] Cập nhật `docs/project-status.md`, `docs/code-change-history.md`, các
  report-parts kỹ thuật/submission của Role C và GenAI log C theo evidence cuối.
- [x] Dùng `docs/requirement-checklist.md` làm final release checklist; A/B/C
  technical audit scopes đã được ghi, còn contribution/Git release gate.

**Review / Success checklist**

- [x] Post-handoff full test pass (`205 passed`); Role A final regression vẫn pending.
- [x] Final LAN run completed on a separate client machine, with no hidden
  localhost dependency.
- [ ] Git diff/commit history phản ánh đúng owner và không có generated transfer data.

**Definition of Done**

- [x] Technical audit A/B/C scopes trong source/docs đã được đối chiếu evidence.
- [ ] Repository clean, reproducible, ready to tag/submit.
- [ ] Status/history/report đều nhất quán với evidence mới nhất.

**Output / Deliverable:** final test log, clean-repo audit, status/history update,
submission-ready branch.

**Oral knowledge:** chỉ ra entry point, cách chạy test/demo, nơi log/evidence và
cách cleanup session/socket/file tạm.

---

## 7. Final Project Completion Checklist

### Functional

- [ ] Role A hoàn thiện command §2.2 và functional MODE B/C theo handoff.
- [x] Client và server chạy được bằng native low-level sockets, không FTP/RDT library.
- [x] TCP control và UDP/RDT payload tách đúng; LIST/NLST trả TCP text.
- [x] Active/PASV, TYPE A/I, STOR/RETR/STOU/APPE/HASH/ABOR hoạt động.
- [x] Error handling và cleanup trả reply chuẩn, không crash server.

### Integration / Excellent RDT

- [x] A/C code integrate qua contract final; không còn API mismatch.
- [x] RDT có header, ACK, sequence, checksum, timeout/retry, duplicate/reorder,
  FIN/ABORT và START lifecycle được kiểm chứng.
- [x] Sliding window hoặc equivalent flow/congestion control có giới hạn và có test.
- [x] Filesystem sandbox, atomic upload, STOU, APPE lock và session isolation đúng.
- [x] Không còn integration blocker.

### Testing / Demo Evidence

- [x] Full automated suite pass trên Linux/WSL2.
- [x] Happy path + invalid input + disconnect + ABOR + file edge cases pass.
- [x] Fault injection loss/ACK loss/corruption/duplicate/reorder/retry exhausted pass.
- [x] Active/PASV, 3 clients và hash comparison có evidence.
- [x] Có live upload và download theo §4.5; LAN evidence được thêm nếu có hai
  máy/môi trường phù hợp.
- [x] Server log có IP, command, active-session table, transfer outcome; password redacted.

### Documentation / Report

- [x] Đủ 7 section report §2.4, không placeholder/stale claim sau technical audit.
- [x] Sequence diagram, header table, session structure và tất cả flowcharts khớp code.
- [x] Requirement traceability map mọi requirement → code/test/evidence.
- [x] `submission/14` chỉ là bảng mapping/reference; status cuối trong report khớp
  `docs/project-status.md` và `docs/requirement-checklist.md`.
- [~] README setup/run guide, test/result docs, task matrix, self/peer evaluation:
  content đã có, contribution percentage chờ nhóm chốt.
- [x] GenAI logs A/B/C có prompt, raw output và refinement trung thực.

### Oral / Live Coding

- [ ] A có ownership TCP/mode/command và giải thích được live code.
- [ ] B có ownership RDT contract/report/test trace và giải thích được live code.
- [ ] C có ownership filesystem/concurrency/integration và giải thích được live code.
- [ ] Mỗi thành viên hiểu full system flow, test/risk/technical decisions.
- [x] Có oral pack và locator; dry run không là gate nội bộ.

### Submission

- [ ] Code clean; không cache, demo binary, credentials hay debug artifact thừa.
- [ ] Git history/commit ownership rõ, deliverable đúng yêu cầu.
- [x] Technical audit A/B/C scopes hoàn tất; không thay thế contribution/team release decision.
- [ ] Nhóm demo được project từ đầu đến cuối và repository sẵn sàng nộp.

## 8. Definition of Project Done

Project 1 chỉ được đánh dấu **100% complete** khi toàn bộ checklist §7 đều
tick, đặc biệt:

1. Mọi requirement trong đề được map tới task/deliverable và có evidence.
2. Không còn carry-over chưa có quyết định `done`, `replaced` hoặc limitation
   được examiner chấp nhận.
3. RDT flow/congestion control, report/oral và required demo evidence không
   còn là TODO; MODE B/C encoder/decoder phải nằm quanh shared RDT data path và
   được mô tả đúng theo evidence cuối.
4. A/C implementation đã integrate; B protocol/report/test artifact đã review.
5. Full test, demo live, report 7 section, GenAI appendix, peer percentage và
   clean repository đều sẵn sàng submit.
