# FINAL WEEK — HOÀN TẤT PROJECT 1: HYBRID FTP

> **Bảng điều hành final week.** Trạng thái dự án duy nhất nằm tại
> `docs/project-status.md`; checklist trước nộp ở `docs/requirement-checklist.md`.

## Dashboard họp mỗi tối

| Task | DRI cuối | Deadline | Trạng thái | Blocker / evidence |
|---|---|---|---|---|
| Command/E2E must-submit | A | Trước report freeze | Done | 189 full tests; 5 FTP E2E tại `docs/evidence/` |
| RDT must-submit | B | Trước report freeze | Done | RDT/fault tests trong full suite; hash Active/PASV |
| LAN two-machine evidence | C | Khi có hai máy | In progress | Phụ thuộc LAN/firewall; localhost không bị block |
| Final report + checklist + sign-off | B | Trước release check | In progress | A/C sign-off technical sections |
| Oral dry run + Git release check | B | Ngày trước nộp | In progress | Chưa có evidence |
| C-F01 Excellent flow/congestion control | C | Sau must-submit gates | Deferred | Không được đẩy report/E2E xuống ưu tiên thấp hơn |

**Thời gian:** 09/08/2026–12/08/2026  
**Mục tiêu:** hoàn tất, kiểm chứng, demo, nộp và vấn đáp được toàn bộ Project 1.
Không tick task chỉ vì code đã có; phải có test, log, screenshot hoặc demo thật.

**Nguồn chuẩn:**

- `Project1_SocketProgramming_2026.md` §§1–4.5 — requirement và tiêu chí nộp.
- `Socket Role.md` — ownership gốc và format tuần 3.
- `tuan-1-chi-tiet-socket.md`, `tuan-2-chi-tiet.md`, `tuan-2.5-fix.md` —
  carry-over.
- `docs/api-contract.md`, `docs/project-status.md`, `docs/requirement-checklist.md`
  — contract/trạng thái cần cập nhật theo code cuối.

## 1. Trạng thái đầu tuần — fact đã có evidence

- `[x]` TCP control + session, filesystem sandbox, Active/PASV localhost,
  RDT Stop-and-Wait, hash, ABOR/disconnect cleanup, 3 client PASV đồng thời.
- `[x]` Full WSL2 test: **189 passed in 106.91s**; E2E localhost: **5 passed
  in 17.61s**.
- `[x]` Progress CLI, server log che password, hash/screenshot PASV đã có.
- `[!]` `MODE B/C` hiện trả `502`; §2.2 không có cột Level thực tế, nên chỉ
  review/ghi limitation trung thực, không tự thiết kế codec ngoài đề.
- `[ ]` Chưa có flow/congestion control; đây là tiêu chí Excellent §1.3.
- `[ ]` START metadata hiện best-effort; cần kiểm tra progress/lifecycle theo
  implementation cuối.
- `[ ]` Chưa có clean-machine run, report 7 section cuối
  và oral/live-coding evidence hoàn chỉnh.

## 2. Carry-over / Outstanding Tasks

| Carry-over | Source | Trạng thái đầu tuần | Xử lý final week |
|---|---|---|---|
| `MODE S/B/C` command review | Week 2, requirement §2.2 | S có; B/C trả 502; bảng đề không có cột Level | `A-F01`; không thêm codec nếu không có requirement rõ |
| Congestion/flow control hoặc equivalent | Requirement §1.3 Excellent | Chưa có | `C-F01` |
| START metadata reliability | Role B Week 2 §4 | START best-effort | `C-F01`, test do `B-F01` |
| Transfer RDT core heavy coding | Week 1/2 Role B | Core đã integrate; phần mở rộng chuyển ownership | **Replaced by:** `C-F01`; B review contract/docs/test black-box trong `B-F01` |
| Active/PASV LAN thật | Week 2.5 Role C | Launcher có, chưa có evidence | `C-F02` (evidence nâng chất lượng, không phải gate đề bài) |
| Full command lifecycle evidence | Week 2 | Unit nhiều, E2E chưa phủ toàn matrix | `A-F02` + `C-F02` |
| Report placeholders/stale claims | Week 1/2 report | `docs/report.md` còn placeholder và trạng thái cũ | `B-F02`, review theo owner A/C |
| GenAI, peer %, task matrix, evidence nhúng report | Requirement §2.4, §4.5 | Chưa chốt cuối | `B-F02` + `C-F03` |
| Oral và live-code readiness | Week 3 | Chưa có dry run evidence | `B-F03` + toàn nhóm |

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

Không trả thành công giả cho MODE chưa có data-path. Giữ `MODE S` hoạt động,
kiểm tra B/C và ghi limitation/reply đúng theo requirement, thay vì tự thêm
codec/format không được đề chỉ định.

**Actions**

- [ ] Xác nhận `MODE S` state/reply/transfer path; test input invalid và session isolation.
- [ ] Rà `MODE B/C`: nếu không có implementation đã được requirement/team chốt,
  giữ `502` và ghi rõ limitation trong HELP/report.
- [ ] Bổ sung unit tests valid/invalid/unauthenticated/state isolation cho S/B/C.
- [ ] Cập nhật phần control/session/command map trong report và GenAI log A.

**Review / Success checklist**

- [ ] `MODE S` trả 200; MODE B/C không bao giờ trả 200 nếu không có implementation thật.
- [ ] Một session đổi mode không ảnh hưởng session khác.
- [ ] Command matrix ghi rõ reply và status thực tế của MODE B/C.

**Definition of Done**

- [ ] Code + unit tests pass.
- [ ] Không có false-success cho MODE B/C.
- [ ] API contract/report/GenAI log A cập nhật.

**Output / Deliverable:** code Role A, tests command/session, contract mode và
phần report control channel.

**Oral knowledge:** giải thích MODE khác Active/PASV và lý do `502` trung thực
tốt hơn trả 200 cho chức năng chưa có.

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

- [ ] Lập command matrix 28 lệnh: happy path, invalid syntax/state, expected reply.
- [ ] Bổ sung TCP-level tests cho auth, directory, metadata, rename, LIST/NLST,
  HELP, PORT/PASV và MODE S/B/C.
- [ ] Phối hợp C thêm E2E cho STOR/RETR/STOU/APPE/HASH/ABOR ở mode cần thiết.
- [ ] Xác nhận `LIST/NLST` luôn trả text qua TCP; chỉ file payload đi UDP/RDT.
- [ ] Ghi evidence/reply matrix vào report phần A và `docs/requirement-checklist.md`.

**Review / Success checklist**

- [ ] Không command nào trong §2.2 thiếu handler hoặc reply ba chữ số.
- [ ] `150 → 226` chỉ xuất hiện sau transfer thực; lỗi map đúng 4xx/5xx.
- [ ] Matrix có link đến test/log, không dùng mô tả suông.

**Definition of Done**

- [ ] Test matrix pass trên WSL2.
- [ ] C review integration transfer; B review traceability matrix.
- [ ] Report A và requirement checklist phản ánh code cuối.

**Output / Deliverable:** command/reply test matrix, source/tests, evidence TCP.

**Oral knowledge:** mô tả từ `COMMAND\r\n` qua parser/session/handler đến reply;
phân biệt 150, 226, 425, 426, 450 và 550.

---

## 5. Role B — protocol traceability, report, testing support và oral

### [ ] B-F01 — RDT protocol contract verification và wire-trace test

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

- [ ] Viết test black-box nhẹ cho header/context/lifecycle; không sửa core RDT.
- [ ] Kiểm tra START được xác nhận hoặc retry hữu hạn theo thiết kế C-F01.
- [ ] Kiểm tra MODE reply/status được documentation phản ánh đúng, không có
  claim data-path B/C nếu code chưa implement.
- [ ] Rà bảng byte-level: field, offset, length, endian, checksum coverage,
  transfer ID, flags, timeout/window policy.
- [ ] Cập nhật `docs/api-contract.md`, `docs/role-b-week-2.md`, GenAI log B.

**Review / Success checklist**

- [ ] Test thất bại nếu header/doc contract bị lệch implementation.
- [ ] Có trace hoặc output chứng minh START → DATA/ACK → FIN/ACK/ABORT.
- [ ] C review test không mock sai production behavior.

**Definition of Done**

- [ ] Test mới pass cùng full suite.
- [ ] Protocol documentation không còn TODO/stale claim.
- [ ] B tự giải thích được từng field header và một retry trên live code.

**Output / Deliverable:** RDT contract test, header/state-machine documentation,
protocol trace evidence.

**Oral knowledge:** UDP không reliable; Stop-and-Wait/window, checksum, sequence,
ACK, retry, duplicate/out-of-order, START, FIN và ABORT hoạt động thế nào.

### [ ] B-F02 — Hoàn thiện report 7 section, requirement traceability và submission pack

**Owner:** Role B  
**Collaborators:** A duyệt control/command; C duyệt filesystem/concurrency/evidence.  
**Dependency:** A-F02, B-F01, C-F02, C-F03.  
**Input / prerequisite:** `docs/report.md`, `docs/report-parts/`, evidence, code
change history, Git log.
**Related requirement:** §2.4 (7 report sections), §§4.2–4.5.

**Goal**

Tạo report thống nhất, đúng code cuối, có map mỗi requirement đến code/test/evidence
và đủ thông tin cho examiner kiểm tra đóng góp.

**Actions**

- [ ] Thay toàn bộ placeholder và câu "pending/unverified" cũ trong report.
- [ ] Ghép sequence diagram TCP+UDP, header/session structures, 4 flowcharts,
  task assignment matrix, self/peer evaluation, GenAI appendix, demo evidence.
- [ ] Tạo final requirement traceability: §1/§2.1/§2.2/§2.3/§2.4/§4.5 → task,
  file, test/evidence.
- [ ] Chuẩn hoá kết quả test mới nhất, ngày chạy, command chạy và limitations thật.
- [ ] Thu self-assessment của A/B/C và contribution percentage tổng chính xác 100%.

**Review / Success checklist**

- [ ] Cả bảy section §2.4 có nội dung thật, không chỉ link hoặc TODO.
- [ ] Diagram/tables trùng code cuối, đặc biệt RDT header 20 byte và mode flow.
- [ ] Mỗi ảnh/log/hash có caption nói rõ nó chứng minh gì.

**Definition of Done**

- [ ] A và C sign-off phần thuộc ownership của mình.
- [ ] `docs/requirement-checklist.md` không còn trạng thái audit cũ trái evidence.
- [ ] Report có thể xuất/nộp mà không cần viết lại.

**Output / Deliverable:** report final, requirement traceability, task matrix,
self/peer evaluation, GenAI appendix và evidence index.

**Oral knowledge:** giải thích kiến trúc end-to-end, ownership ba role, test
strategy, rủi ro đã xử lý và evidence tương ứng.

### [ ] B-F03 — Oral, live-code locator và review chéo

**Owner:** Role B  
**Collaborators:** A và C tham gia/đánh giá chéo.  
**Dependency:** B-F01, B-F02 và code final ổn định.  
**Input / prerequisite:** code final, report final, Git history.
**Related requirement:** rubric §3 (Oral 30%, Live Coding 20%), §4.1–4.4.

**Goal**

Mỗi thành viên hiểu system flow và locate/fix được phần live code của mình;
Role B có material kỹ thuật rõ ràng, không chỉ làm hành chính.

**Actions**

- [ ] Tạo oral pack: 20 câu hỏi, đáp án ngắn, file/line locator và câu hỏi phản biện.
- [ ] Tổ chức 1 dry run: A giải thích TCP/MODE, B giải thích RDT, C giải thích
  filesystem/concurrency; sau đó đổi chéo 3 câu system-wide.
- [ ] Thực hành live edits an toàn: timeout/retry, checksum failure, reply code,
  path traversal, mode selection.
- [ ] Rà Git log/GenAI logs để mỗi người giải thích được thay đổi của mình.

**Review / Success checklist**

- [ ] Mỗi role trả lời được TCP vs UDP, Active vs PASV, RDT reliability,
  session isolation, atomic upload và cleanup.
- [ ] Mỗi role locate được ít nhất 3 file ownership trong dưới 1 phút.
- [ ] Dry run có checklist lỗi/sửa lại, không chỉ họp miệng.

**Definition of Done**

- [ ] Oral pack và dry-run record được lưu.
- [ ] A/B/C đều sign-off đã hiểu shared flow và own module.

**Output / Deliverable:** oral Q&A, live-code locator, dry-run checklist.

**Oral knowledge:** toàn bộ system flow; B ưu tiên wire protocol và test evidence.

---

## 6. Role C — data pipeline, integration và final evidence

### [ ] C-F01 — Hoàn tất RDT Excellent: reliable lifecycle và flow/congestion control

**Owner:** Role C  
**Collaborators:** A cung cấp mode/context; B verify contract/test.  
**Dependency:** B-F01 contract baseline.  
**Input / prerequisite:** RDT sender/receiver, `TransferManager`, filesystem
atomic lifecycle, fault-injection suite.
**Related requirement:** §§1.2, 1.3 Excellent, 2.1, 2.4 flowcharts.

**Goal**

Hoàn tất đúng ba đặc tính Excellent của data path: RDT custom reliable đã có,
flow/congestion control có giới hạn và SHA-256 end-to-end vẫn đúng.

**Actions**

- [ ] START handshake/ack hoặc retry hữu hạn sao cho receiver biết metadata;
  fail phải trả lỗi hữu hạn và cleanup đúng.
- [ ] Implement sliding window hoặc equivalent bounded flow-control, ACK/window
  state, timeout/retransmit và fallback/error handling rõ ràng.
- [ ] Bảo toàn peer lock, transfer ID, cancellation, FIN grace, `.part` cleanup.
- [ ] Thêm fault injection loss/corruption/reorder/window exhaustion và binary,
  empty, chunk-boundary SHA-256 tests.
- [ ] Cập nhật contract, state-machine/Active-PASV/concurrency diagrams, GenAI log C.

**Review / Success checklist**

- [ ] File text, binary, empty và chunk boundary round-trip đúng SHA-256.
- [ ] Loss/corruption/duplicate/out-of-order không ghi duplicate hoặc treo vô hạn.
- [ ] Window bị giới hạn; không flood UDP và không giữ global/session lock khi chờ ACK.
- [ ] ABOR/disconnect giữa transfer giữ file cũ, xóa `.part`.

**Definition of Done**

- [ ] Unit + fault-injection + FTP integration tests pass.
- [ ] A review mode selection; B review wire contract.
- [ ] Không có regression Active/PASV hoặc 189-test baseline.

**Output / Deliverable:** production RDT/data-pipeline code, test suite,
state-machine docs và reliability evidence.

**Oral knowledge:** window giới hạn in-flight packets thế nào; checksum, ACK,
retry và hash end-to-end phối hợp để giữ file đúng ra sao.

### [ ] C-F02 — Final transfer matrix và LAN demo hai máy

**Owner:** Role C  
**Collaborators:** A xử lý command/reply lỗi; B kiểm tra protocol/evidence.  
**Dependency:** C-F01 và A-F02.  
**Input / prerequisite:** hai máy cùng LAN, IPv4 server, firewall TCP/UDP,
`README.md` launcher.
**Related requirement:** §§1.1–1.3, 2.1, 2.2, 4.5.2–4.5.3.

**Goal**

Chứng minh project chạy end-to-end ngoài loopback và phủ các transfer/file edge
cases đủ để demo, review và submit.

**Actions**

- [ ] Nếu có hai máy cùng LAN, chạy PASV từ máy client khác: server `--host
  0.0.0.0 --advertise-host <LAN-IP>`, lưu output, screenshot và SHA-256.
- [ ] Nếu có môi trường phù hợp, chạy LAN ACTIVE; nếu firewall/NAT ngăn, ghi
  limitation trung thực và giữ evidence localhost ACTIVE đã pass.
- [ ] Mở rộng E2E: STOU, APPE, HASH, TYPE A/I, empty/text/binary/
  archive, boundary, invalid endpoint, ABOR/disconnect và 3 client.
- [ ] Chụp server active-session table, command/reply, progress 0→100%, hash,
  concurrent sessions.
- [ ] Cập nhật README với lệnh run sạch và xử lý firewall thực tế.

**Review / Success checklist**

- [ ] Nếu chạy LAN: client dùng IP thật, không phải `127.0.0.1`.
- [ ] Hash source/server/download bằng nhau cho mỗi demo transfer.
- [ ] Mọi evidence có tên file, ngày, mode và command chạy.

**Definition of Done**

- [ ] E2E matrix pass; không còn integration blocker.
- [ ] Evidence được lưu dưới `docs/evidence/`, được B đưa vào report.
- [ ] A/B review demo log trước khi tick.

**Output / Deliverable:** LAN evidence, final E2E tests/log/hash/screenshots,
README run guide.

**Oral knowledge:** flow TCP control + UDP data, khác nhau Active/PASV, cách
firewall/advertised IP ảnh hưởng PASV.

### [ ] C-F03 — Final regression, clean repository và submission readiness

**Owner:** Role C  
**Collaborators:** A/B review code/docs ownership.  
**Dependency:** A-F02, B-F01, C-F01, C-F02.  
**Input / prerequisite:** final branch, report, evidence directory, `.gitignore`.
**Related requirement:** §§2.1, 2.4, 4.2–4.5.

**Goal**

Đảm bảo repo chạy từ đầu trên môi trường sạch, chỉ chứa deliverable cần nộp và
trạng thái/status/history không nói quá evidence.

**Actions**

- [ ] Chạy full suite trên WSL2/Linux từ clean venv; lưu command, version,
  result vào evidence.
- [ ] Chạy final server/client live demo từ clean checkout hoặc máy khác.
- [ ] Rà `.gitignore` và Git status: bỏ demo binaries, downloads, cache, secret,
  debug artifact; giữ source/tests/docs/evidence được chọn.
- [ ] Cập nhật `project-status`, `code-change-history`, `tuan-2.5-fix`,
  role-C report, GenAI log C theo evidence cuối.
- [ ] Tạo final release checklist để A/B sign-off.

**Review / Success checklist**

- [ ] Full test pass và không có warning/traceback chưa giải thích.
- [ ] Fresh run tạo được server/client demo không phụ thuộc file local ẩn.
- [ ] Git diff/commit history phản ánh đúng owner và không có generated transfer data.

**Definition of Done**

- [ ] A/B sign-off source/docs của họ.
- [ ] Repository clean, reproducible, ready to tag/submit.
- [ ] Status/history/report đều nhất quán với evidence mới nhất.

**Output / Deliverable:** final test log, clean-repo audit, status/history update,
submission-ready branch.

**Oral knowledge:** chỉ ra entry point, cách chạy test/demo, nơi log/evidence và
cách cleanup session/socket/file tạm.

---

## 7. Final Project Completion Checklist

### Functional

- [ ] Tất cả command §2.2 có handler/reply phù hợp; MODE chưa có implementation
  data-path không được báo success giả.
- [ ] Client và server chạy được bằng native low-level sockets, không FTP/RDT library.
- [ ] TCP control và UDP/RDT payload tách đúng; LIST/NLST trả TCP text.
- [ ] Active/PASV, TYPE A/I, STOR/RETR/STOU/APPE/HASH/ABOR hoạt động.
- [ ] Error handling và cleanup trả reply chuẩn, không crash server.

### Integration / Excellent RDT

- [ ] A/C code integrate qua contract final; không còn API mismatch.
- [ ] RDT có header, ACK, sequence, checksum, timeout/retry, duplicate/reorder,
  FIN/ABORT và START lifecycle được kiểm chứng.
- [ ] Sliding window hoặc equivalent flow/congestion control có giới hạn và có test.
- [ ] Filesystem sandbox, atomic upload, STOU, APPE lock và session isolation đúng.
- [ ] Không còn integration blocker.

### Testing / Demo Evidence

- [ ] Full automated suite pass trên Linux/WSL2.
- [ ] Happy path + invalid input + disconnect + ABOR + file edge cases pass.
- [ ] Fault injection loss/ACK loss/corruption/duplicate/reorder/retry exhausted pass.
- [ ] Active/PASV, 3 clients và hash comparison có evidence.
- [ ] Có live upload và download theo §4.5; LAN evidence được thêm nếu có hai
  máy/môi trường phù hợp.
- [ ] Server log có IP, command, active-session table, transfer outcome; password redacted.

### Documentation / Report

- [ ] Đủ 7 section report §2.4, không placeholder/stale claim.
- [ ] Sequence diagram, header table, session structure và tất cả flowcharts khớp code.
- [ ] Requirement traceability map mọi requirement → code/test/evidence.
- [ ] README setup/run guide, test/result docs, task matrix, self/peer evaluation hoàn chỉnh.
- [ ] GenAI logs A/B/C có prompt, raw output và refinement trung thực.

### Oral / Live Coding

- [ ] A có ownership TCP/mode/command và giải thích được live code.
- [ ] B có ownership RDT contract/report/test trace và giải thích được live code.
- [ ] C có ownership filesystem/concurrency/integration và giải thích được live code.
- [ ] Mỗi thành viên hiểu full system flow, test/risk/technical decisions.
- [ ] Có oral pack, locator và dry run hoàn tất.

### Submission

- [ ] Code clean; không cache, demo binary, credentials hay debug artifact thừa.
- [ ] Git history/commit ownership rõ, deliverable đúng yêu cầu.
- [ ] Final review A/B/C sign-off.
- [ ] Nhóm demo được project từ đầu đến cuối và repository sẵn sàng nộp.

## 8. Definition of Project Done

Project 1 chỉ được đánh dấu **100% complete** khi toàn bộ checklist §7 đều
tick, đặc biệt:

1. Mọi requirement trong đề được map tới task/deliverable và có evidence.
2. Không còn carry-over chưa có quyết định `done`, `replaced` hoặc limitation
   được examiner chấp nhận.
3. RDT flow/congestion control, report/oral và required demo evidence không
   còn là TODO; MODE B/C không có success claim nếu chưa có data-path thật.
4. A/C implementation đã integrate; B protocol/report/test artifact đã review.
5. Full test, demo live, report 7 section, GenAI appendix, peer percentage và
   clean repository đều sẵn sàng submit.
