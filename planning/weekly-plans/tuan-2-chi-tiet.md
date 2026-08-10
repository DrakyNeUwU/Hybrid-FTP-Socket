# TUẦN 2 — CÔNG VIỆC THEO VAI TRÒ (2/8/2026 → 8/8/2026)

> **Snapshot lịch sử, không phải trạng thái hiện tại.** Xem
> `docs/project-status.md` và `docs/requirement-checklist.md`.

**Mục tiêu tuần:** Hoàn thiện các chức năng Advanced gồm truyền file binary, quản lý cây thư mục, Active/PASV và nhiều client đồng thời; hoàn thiện lớp truyền file UDP tin cậy; tích hợp ba module thành hệ thống chạy end-to-end.

> Theo `Project1_SocketProgramming_2026.md`, RDT có ACK, sequence number, timeout/retransmit và HASH thuộc tiêu chí Excellent. Tuy nhiên, đề cũng bắt buộc kênh UDP phải xử lý mất, lỗi, trùng và sai thứ tự, nên Stop-and-Wait vẫn là công việc cốt lõi cần hoàn thành trước khi tích hợp.

## 1. Ranh giới trách nhiệm

| Thành phần | Owner | Trách nhiệm chính |
|---|---|---|
| TCP control, command parser, reply code, session | **Role A** | Nhận và kiểm tra lệnh, quản lý trạng thái session, điều phối B/C, trả FTP reply |
| UDP data channel, Reliable Data Transfer | **Role B** | Packet, ACK, checksum, timeout, retransmit và vòng đời transfer |
| Filesystem, concurrency, integration | **Role C** | Thao tác file/thư mục an toàn, server đa luồng, CLI/log và tích hợp A+B |

Không role nào tự thay đổi shared interface, packet format hoặc quy ước lỗi mà chưa thống nhất với hai role còn lại.

---

## 2. Role A — TCP Control & Session

### Công việc cần làm

- Hoàn thiện session state riêng cho từng client:
  - Trạng thái đăng nhập.
  - Working directory hiện tại.
  - `TYPE A/I`.
  - `MODE S/B/C`.
  - Active/PASV endpoint.
  - Trạng thái `RNFR` chờ `RNTO`.
  - Transfer hiện tại và trạng thái hủy.
- Implement nhóm lệnh thư mục:
  - `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`.
  - `LIST`, `NLST`, `STAT`.
- Implement nhóm lệnh thông tin và cấu hình:
  - `SIZE`, `MDTM`, `TYPE`, `MODE`, `HELP`.
- Implement `PORT` và `PASV` để đàm phán UDP endpoint qua TCP control channel.
- Implement và điều phối nhóm lệnh truyền file:
  - `RETR`, `STOR`, `STOU`, `APPE`.
  - A chỉ xử lý command/state/reply; dữ liệu thật do B truyền và file do C quản lý.
- Implement nhóm lệnh thao tác file:
  - `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`.
- Trả đúng chuỗi reply cho data command:
  - `150` trước khi truyền.
  - `226` khi hoàn tất.
  - `425` khi không mở được data channel.
  - `426` khi transfer lỗi hoặc bị hủy.
  - `550` khi file/path không hợp lệ.
- Validate trạng thái và cú pháp của mọi lệnh:
  - `530` nếu lệnh yêu cầu đăng nhập nhưng client chưa login.
  - `500` cho command/syntax chung không hợp lệ.
  - `501` cho tham số không hợp lệ.
  - `502` nếu chức năng chưa được hỗ trợ thật; không trả thành công giả.
- Viết unit test cho happy path và các trường hợp:
  - Thiếu/thừa argument.
  - Chưa đăng nhập.
  - Path không hợp lệ.
  - Gọi lệnh sai thứ tự.
  - Command không tồn tại.
  - Client disconnect bất ngờ.
- Hoàn thiện tài liệu phần TCP:
  - Sequence diagram control lifecycle.
  - TCP control-message format.
  - Session structure và state transition.

### Điểm cần bảo đảm

- `RNTO` chỉ hợp lệ sau `RNFR`; state rename phải riêng cho từng session và được reset đúng lúc.
- `PORT` phải kiểm tra đủ sáu số trong khoảng `0..255` và có chính sách chống client chỉ định endpoint tùy ý.
- Trong hệ thống hybrid này, `PASV` đàm phán **UDP endpoint**, không mở TCP data connection như FTP truyền thống.
- `ABOR` phải gửi cancellation signal cho B/C và thật sự dừng transfer, đóng socket, dọn file tạm.
- `MODE B/C` chỉ được báo thành công nếu hệ thống thực sự hỗ trợ; nếu không phải trả `502`.

---

## 3. Role B — UDP Data Channel & Reliable Transfer

### Công việc cần làm

- Chốt và hiện thực `RDTHeader` dùng chung:
  - Sequence number.
  - ACK number hoặc ACK flag.
  - Packet flags như START, DATA, ACK, FIN, ABORT.
  - Checksum.
  - Payload length.
  - Transfer ID nếu hệ thống cần phân biệt nhiều transfer.
- Viết và kiểm thử serialize/deserialize bằng network byte order cố định.
- Hoàn thiện Stop-and-Wait cho cả upload và download:
  - Gửi một packet rồi chờ ACK.
  - Socket timeout.
  - Retransmit khi mất DATA hoặc ACK.
  - Giới hạn số lần retransmit.
  - Loại packet và ACK trùng.
  - Xử lý packet sai thứ tự hoặc sai transfer.
- Hoàn thiện checksum và corruption detection:
  - Không ghi payload lỗi xuống file.
  - Packet lỗi phải bị drop hoặc kích hoạt cơ chế gửi lại.
- Xây dựng transfer lifecycle rõ ràng:
  - Bắt đầu transfer.
  - Gửi/nhận DATA.
  - Kết thúc bằng FIN/ACK hoặc cơ chế tương đương.
  - Hủy bằng ABORT.
  - Báo success/failure cho A và C.
- Hỗ trợ đúng các trường hợp biên:
  - File rỗng.
  - File nhỏ hơn một payload.
  - File có kích thước đúng bội payload.
  - Sequence number wrap nếu có giới hạn trường.
- Tích hợp cả Active và PASV theo endpoint đã đàm phán bởi A/C.
- Cung cấp progress callback hoặc trạng thái tiến trình thật cho CLI của C.
- Thêm cơ chế cancellation để `ABOR` không để socket hoặc worker thread chạy nền.
- Viết fault-injection test cho:
  - Mất DATA.
  - Mất ACK.
  - Packet trễ.
  - Packet trùng.
  - Packet lỗi checksum.
  - Packet đến sai thứ tự.
  - Hết số lần retransmit.
- Test nhiều loại dữ liệu: text, ảnh, archive, video nhỏ và file rỗng; so sánh SHA-256 trước/sau.
- Hoàn thiện tài liệu UDP/RDT:
  - Bảng `RDTHeader` ở mức byte/field.
  - Sender state machine.
  - Receiver state machine.
  - Timeout, retry và duplicate-handling policy.

### Điểm cần bảo đảm

- Không suy luận EOF chỉ từ packet có payload ngắn; phải có FIN hoặc metadata xác định kết thúc.
- Validate header và `payload_length` trước khi xử lý payload.
- Checksum phải bao phủ đúng phần dữ liệu đã thống nhất.
- Hết retry phải trả lỗi hữu hạn, không treo vô thời hạn.
- Không dùng FTP/RDT/file-transfer framework hoặc thư viện truyền dữ liệu dựng sẵn.
- Chỉ bắt đầu Selective Repeat/sliding window khi Stop-and-Wait, Active/PASV, ABOR và multi-client đã ổn định.

---

## 4. Role C — Filesystem, Concurrency & Integration

### Công việc cần làm

- Hoàn thiện filesystem service để A gọi cho các lệnh:
  - `PWD`, `CWD`, `CDUP`.
  - `MKD`, `RMD`, `LIST`, `NLST`, `STAT`.
  - `SIZE`, `MDTM`.
  - `DELE`, `RNFR`, `RNTO`.
  - Mở file nguồn/đích cho `RETR`, `STOR`, `STOU`, `APPE` và `HASH`.
- Bảo vệ FTP root:
  - Resolve và validate mọi path do client cung cấp.
  - Chặn `..` thoát root.
  - Chặn absolute path ngoài root.
  - Chặn symlink trỏ ra ngoài root.
  - Không tin trực tiếp tên file/path từ client.
- Bảo đảm binary-safe I/O bằng `rb`, `wb`, `ab` và context manager.
- Dùng file tạm và atomic replace cho upload khi phù hợp, để transfer lỗi không phá file cũ hoặc tạo file hoàn chỉnh giả.
- Xác định chính sách khi nhiều client thao tác cùng file:
  - Serialize bằng file lock.
  - Hoặc từ chối transfer xung đột.
  - `STOU` phải luôn tạo tên không trùng.
  - `APPE` không được để dữ liệu từ nhiều client trộn byte.
- Hoàn thiện threaded server:
  - Một client có một session riêng.
  - Registry quản lý active sessions.
  - Một client lỗi không làm chết server.
  - Cleanup thread, session và socket khi `QUIT`, disconnect hoặc shutdown.
- Chỉ dùng lock cho tài nguyên chung cần thiết:
  - Session registry.
  - File đích đang được ghi.
  - Log hoặc output dùng chung.
  - Không giữ global lock trong lúc chờ UDP ACK.
- Tích hợp module A và B:
  - TCP command kích hoạt đúng filesystem/UDP operation.
  - Active/PASV chuyển đúng UDP endpoint.
  - `RETR`, `STOR`, `STOU`, `APPE` chạy end-to-end.
  - Success/failure của B được ánh xạ về reply của A.
  - `ABOR`, timeout và disconnect dọn sạch tài nguyên.
- Hoàn thiện CLI:
  - Trạng thái kết nối.
  - Command và reply.
  - Active/PASV mode.
  - Transfer progress thật.
  - Kết quả thành công/thất bại.
- Hoàn thiện server log:
  - Timestamp.
  - Client IP và session ID.
  - Command đã thực thi.
  - Transfer ID và kết quả.
  - Active-session table.
  - Không log password hoặc nội dung file nhạy cảm.
- Viết test cho:
  - Path traversal và symlink escape.
  - Nhiều client có `cwd`, mode và session độc lập.
  - Nhiều transfer đồng thời.
  - Nhiều client ghi cùng file.
  - Client disconnect giữa transfer.
  - Server shutdown và cleanup.
- Hoàn thiện tài liệu:
  - Thread-dispatch flowchart.
  - Active/PASV flowchart.
  - Concurrency/locking policy.
  - Luồng tích hợp TCP control + UDP data + filesystem.

### Điểm cần bảo đảm

- Mọi filesystem error phải được chuyển thành lỗi có cấu trúc để A ánh xạ sang FTP reply, không để exception thoát khỏi client thread.
- Session table phải loại client đã mất kết nối.
- Upload lỗi hoặc `ABOR` phải xóa file tạm nhưng không xóa nhầm file hợp lệ.
- Log và progress của nhiều transfer phải phân biệt được bằng session/transfer ID.
- Role C chủ trì integration test và tổng hợp demo evidence, nhưng A/B vẫn phải sửa lỗi thuộc module của mình.

---

## 5. Công việc chung của cả ba role

- Chốt shared contract trước khi tích hợp:
  - API A → C cho filesystem operation và error mapping.
  - API A/C → B để start, cancel và nhận kết quả transfer.
  - Format `PORT`, reply `PASV` và UDP endpoint lifecycle.
  - `RDTHeader`, chunk size, timeout và retry limit.
  - Quy tắc đóng socket, dọn file tạm và cleanup session.
- Ráp sequence diagram TCP + UDP chung:
  - A phụ trách TCP lifecycle.
  - B phụ trách UDP DATA/ACK/retransmit/FIN/ABORT.
  - C kiểm tra thread, filesystem và cleanup theo code tích hợp.
- Review chéo:
  - A review UDP events/reply mapping của B.
  - B review file lifecycle, lock và cleanup của C.
  - C review parser, reply code và session isolation của A.
- Không chỉnh đồng thời cùng một đoạn trong `docs/report.md`; chia section hoặc chỉ định một editor và hai reviewer.
- Cập nhật `docs/genai-log-<role>.md` ngay khi dùng AI, gồm prompt, raw output và phần tự kiểm tra/refactor.
- Test toàn hệ thống trên Linux/WSL2, không chỉ trên môi trường của một thành viên.
- Chuẩn bị demo evidence: upload, download, hash comparison, active-session table và concurrent clients.

---

## 6. Integration test bắt buộc

| Nhóm test | Trường hợp tối thiểu |
|---|---|
| Authentication/session | Chưa login, login đúng/sai, `QUIT`, disconnect bất ngờ |
| Directory/security | Nested directory, `..`, absolute path, symlink thoát root, `RMD` thư mục không rỗng |
| Transfer data | File rỗng, text, ảnh, archive/video nhỏ, kích thước đúng bội chunk |
| Operating mode | Upload/download bằng Active và PASV, chuyển mode nhiều lần |
| Reliability | Mất DATA/ACK, duplicate, corruption, delay, reorder và hết retry |
| File commands | `RETR`, `STOR`, `STOU`, `APPE`, `DELE`, `RNFR/RNTO`, `HASH`, `ABOR` |
| Concurrency | Ít nhất ba client, transfer đồng thời, session riêng và xung đột cùng file |
| Observability | Progress, command log và active-session table phản ánh dữ liệu thật |

---

## 7. Definition of Done tuần 2

- [ ] Toàn bộ command trong mục 2.2 của đề được parse và trả reply phù hợp.
- [ ] Truyền được file text và binary theo cả upload/download qua TCP control + UDP data.
- [ ] File nhận có SHA-256 giống file nguồn.
- [ ] Nested directory và mọi filesystem operation không thoát FTP root.
- [ ] Active và PASV đều hoạt động.
- [ ] Stop-and-Wait xử lý ACK, sequence, checksum, timeout/retransmit, duplicate và out-of-order.
- [ ] Retry có giới hạn; `ABOR`, timeout và disconnect cleanup đúng.
- [ ] Ít nhất ba client hoạt động đồng thời với session độc lập, không deadlock hoặc trộn dữ liệu.
- [ ] CLI/log hiển thị đúng trạng thái, progress, client và active sessions; không lộ password.
- [ ] Unit test và integration test chính pass trên Linux/WSL2.
- [ ] Sequence diagram, header table, state machines và flowcharts khớp code.
- [ ] GenAI log của từng role được cập nhật đầy đủ.
- [ ] Có demo evidence ban đầu và không còn lỗi blocker của Advanced/core reliable UDP.

Chỉ triển khai Selective Repeat, sliding window hoặc congestion-control nâng cao khi toàn bộ chức năng trên đã ổn định.
