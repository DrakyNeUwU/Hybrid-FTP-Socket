# TUẦN 2 — KẾ HOẠCH SỬA LỖI VÀ HOÀN THIỆN TÍCH HỢP

**Thời gian:** 02/08/2026–08/08/2026

**Mốc đánh giá lại:** 06/08/2026

**Nguồn yêu cầu cao nhất:** `filephanchiacv/Project1_SocketProgramming_2026.md`

## 1. Mục tiêu và nguyên tắc thực hiện

Mục tiêu tuần 2 là đưa hệ thống Hybrid FTP từ các module rời rạc thành một luồng chạy thật:

- TCP làm control channel cho command, reply và session.
- UDP làm data channel cho toàn bộ payload file.
- UDP dùng Reliable Data Transfer tự cài đặt để xử lý mất gói, lỗi dữ liệu, packet trùng và sai thứ tự.
- Upload và download hoạt động bằng cả Active và PASV.
- File text và binary sau truyền có SHA-256 giống file nguồn.
- Nhiều client có session và transfer độc lập.

Các nguyên tắc bắt buộc:

1. Không triển khai Selective Repeat, sliding window hoặc congestion control trước khi Stop-and-Wait, Active/PASV, ABOR và multi-client đã ổn định.
2. Không trả reply thành công nếu dữ liệu chưa được truyền và ghi file thành công.
3. Không dùng số test được collect, `compileall` hoặc phần trăm tự đánh giá làm bằng chứng hoàn thành.
4. Mọi client path đều là dữ liệu không tin cậy và phải đi qua filesystem service của Role C.
5. Không role nào tự thay đổi shared interface, packet format hoặc error contract. Thay đổi contract phải được A, B và C thống nhất trước.
6. Chỉ kết luận hoàn thành khi test gọi production code thật và workflow end-to-end chạy được trên Linux hoặc WSL2.

## 2. Trạng thái kỹ thuật tại mốc 06/08/2026

Các tỷ lệ dưới đây chỉ dùng để lập kế hoạch, không phải bằng chứng hoàn thành.

| Role | Mức tương đối | Đã có | Blocker hiện tại |
|---|---:|---|---|
| **Role A** | Khoảng 40% | Session, parser, phần lớn command handler, PORT/PASV cơ bản | Server lỗi import, transfer chưa triển khai, thiếu command và test A đang rỗng |
| **Role B** | Khoảng 25% | RDT header, checksum, Stop-and-Wait sơ bộ, helper PORT/PASV | Sender/receiver lỗi import, protocol còn lỗi và test chưa gọi code thật |
| **Role C** | Hỗ trợ tích hợp | Filesystem service, binary I/O, path protection, concurrency foundation | Chờ contract A/B ổn định để nối luồng transfer end-to-end |

Hiện chưa có bằng chứng upload/download end-to-end. Full test suite dừng ở bước collection vì lỗi import. Bảy test RDT đang pass không chứng minh sender/receiver chạy thật; ba file test Role A đang rỗng.

## 3. Ranh giới trách nhiệm và đầu ra

| Thành phần | Owner | Người phối hợp | Đầu ra bắt buộc |
|---|---|---|---|
| TCP control, parser, reply, session | **Role A** | C review integration | Server import/khởi động được; command/reply đúng; test parser/session/command |
| UDP data channel và RDT | **Role B** | A cung cấp endpoint; C cung cấp file lifecycle | Header contract; sender/receiver chạy thật; reliability/fault-injection test |
| Filesystem và concurrency | **Role C** | A/B sử dụng contract | Path an toàn; atomic upload; file lock; cancellation; cleanup |
| `TransferManager` và reply mapping | **Role A + C** | B cung cấp API RDT | `150 → transfer → 226/425/426/550`, không trả thành công giả |
| Active/PASV end-to-end | **A + B + C** | C chủ trì test | Upload/download hai mode, SHA-256 khớp |
| Integration, multi-client, demo evidence | **Role C** | A/B sửa lỗi module mình | Log/test cho ít nhất ba client, cleanup và hash comparison |

## 4. Shared contract phải chốt trước khi tích hợp

Trước khi sửa luồng transfer, cả ba role phải ghi rõ và thống nhất các contract sau trong code hoặc tài liệu tích hợp:

### 4.1 Contract TCP command → transfer

- Input: session, loại operation (`RETR`, `STOR`, `STOU`, `APPE`), path đã validate, data mode và endpoint.
- Output: trạng thái bắt đầu, tiến trình và kết quả cuối.
- Failure: phân biệt không mở được data channel, path/file sai, timeout, protocol error và cancellation.
- Reply mapping:
  - `150` khi data channel đã sẵn sàng và transfer thật sự bắt đầu.
  - `226` chỉ sau khi transfer và file commit hoàn tất.
  - `425` khi không mở hoặc không xác định được data channel.
  - `426` khi transfer lỗi, timeout hoặc bị hủy.
  - `550` khi file/path không hợp lệ.

### 4.2 Contract RDT

- Chốt tên module và cách import thống nhất.
- Chốt từng field của `RDTHeader`, network byte order, kích thước và phạm vi giá trị.
- Chốt flags START, DATA, ACK, FIN và ABORT.
- Chốt `transfer_id`, sequence number, ACK number, payload length và checksum coverage.
- Chốt chunk size, timeout, retry limit và receiver inactivity timeout.
- Chốt quy tắc packet đúng thứ tự, duplicate, out-of-order và packet thuộc transfer khác.
- Chốt callback progress, cancellation signal và kết quả success/failure.

### 4.3 Contract filesystem

- Role A không tự ghép client path để truy cập file.
- Download nhận path/file handle đã được Role C validate.
- Upload ghi vào file tạm; chỉ atomic replace khi nhận FIN hợp lệ và transfer thành công.
- `STOU` dùng tên server-generated không trùng.
- `APPE` giữ lock đúng phạm vi để dữ liệu nhiều client không trộn byte.
- ABOR, timeout và disconnect phải xóa file tạm nhưng không xóa file hợp lệ cũ.

## 5. Kế hoạch thực thi theo thứ tự ưu tiên

Không chuyển sang phase sau nếu exit gate của phase trước chưa đạt.

### Phase 0 — Khôi phục import và khả năng chạy

**Owner:** A cho `server/`; B cho `common/rdt_*`; C review package layout.

#### Role A

- Sửa package import trong:
  - `server/threaded_server.py`
  - `server/client_handler.py`
  - `server/command_handler.py`
- Bảo đảm chạy từ repository root bằng `python -m server.threaded_server`.
- Không sửa `sys.path` để che lỗi package nếu có thể dùng import package chuẩn.

#### Role B

- Thống nhất `common/RDTHeader.py` với import đang dùng trong:
  - `common/rdt_sender.py`
  - `common/rdt_receiver.py`
- Thay dependency `common.file_utils` không tồn tại bằng API thật trong `common/file_handler.py` hoặc contract đã thống nhất với C.
- Bảo đảm import độc lập được header, sender, receiver và `common/rdt_utils.py`.

#### Test/exit gate

- Import được `server.threaded_server`.
- Import được RDT sender và receiver.
- Server khởi động bằng `python -m server.threaded_server` và dừng sạch bằng Ctrl+C/test shutdown.
- `python -m pytest -v` đi qua collection; nếu còn lỗi, ghi rõ file, exception và owner.

### Phase 1 — Hoàn thiện Role B RDT core

**Owner:** Role B. **Reviewer:** A kiểm tra event/reply mapping; C kiểm tra file/cancellation lifecycle.

#### Công việc

- Hoàn thiện serialize/deserialize của `RDTHeader` theo network byte order cố định.
- Validate header trước khi xử lý:
  - Datagram đủ header.
  - `payload_length` đúng bằng payload thực nhận và không vượt chunk limit.
  - Flags hợp lệ.
  - `transfer_id` khớp transfer hiện tại.
- Hoàn thiện sender Stop-and-Wait:
  - Gửi một DATA/FIN rồi chờ đúng ACK.
  - Chỉ nhận ACK đúng sequence, transfer ID và UDP peer.
  - Xác minh checksum/nội dung ACK theo contract.
  - Timeout và retransmit có giới hạn hữu hạn.
- Hoàn thiện receiver:
  - Chỉ ghi payload có checksum đúng và sequence đang chờ.
  - Duplicate cũ không ghi lần hai nhưng được gửi lại ACK phù hợp.
  - Packet tương lai/out-of-order không được ACK như thể đã lưu thành công.
  - Packet sai transfer hoặc sai peer bị drop.
  - Receiver inactivity timeout phải trả lỗi hữu hạn, không lặp vô hạn.
- Hoàn thiện lifecycle START/DATA/FIN/ACK/ABORT.
- Khi cancellation xảy ra trong lúc chờ ACK, gửi/tiếp nhận ABORT theo contract.
- Dùng `try/finally` để dọn socket và tài nguyên do hàm sở hữu.
- Không suy luận EOF từ payload ngắn; file rỗng vẫn kết thúc bằng FIN hoặc metadata rõ ràng.
- Progress callback phản ánh byte đã ACK/ghi thật, không phản ánh byte mới chỉ gửi.

#### Đầu ra Role B

- `common/RDTHeader.py` và sender/receiver import, chạy được.
- Bảng byte/field của header và sender/receiver state machine cập nhật trong `docs/report.md`.
- `docs/genai-log-b.md` có prompt, raw output và refinement thật.
- Test production RDT cho file rỗng, text, binary, nhỏ hơn chunk, đúng một chunk và đúng bội chunk.

#### Fault-injection test bắt buộc

| Tình huống | Kết quả bắt buộc |
|---|---|
| Mất DATA | Sender retransmit; kết quả đúng hoặc fail hữu hạn |
| Mất ACK | Receiver không ghi duplicate; sender nhận ACK lại |
| Duplicate | Payload chỉ xuất hiện một lần |
| Corruption | Payload lỗi không được ghi; có cơ chế retry |
| Delay | Không ACK nhầm packet cũ; transfer không treo |
| Out-of-order | Không mất dữ liệu, không advance sai sequence |
| Hết retry | Trả failure hữu hạn và cleanup |
| ABORT | Hai phía dừng, không còn worker/socket/file tạm |

### Phase 2 — Hoàn thiện Role A TCP control và session

**Owner:** Role A. **Reviewer:** C kiểm tra path/session; B kiểm tra data endpoint.

#### Parser và command coverage

- Parser xử lý được input rỗng, whitespace, command không tồn tại, thiếu và thừa argument mà không làm chết client thread.
- Hoàn thiện toàn bộ command trong mục 2.2 của đề:
  - Authentication/control: `USER`, `PASS`, `QUIT`, `NOOP`.
  - Directory: `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `LIST`, `NLST`, `STAT`.
  - Metadata/config: `SIZE`, `MDTM`, `TYPE`, `MODE`, `HELP`.
  - Data mode: `PORT`, `PASV`.
  - Transfer: `RETR`, `STOR`, `STOU`, `APPE`.
  - File operations: `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`.
- `LIST` trả detailed listing; `NLST` trả tên; cả hai hỗ trợ optional path.
- `MDTM` trả định dạng `YYYYMMDDhhmmss`.
- `MODE B/C` trả `502` cho đến khi thật sự hỗ trợ.

#### Session, endpoint và security

- Mỗi client có session riêng gồm login, cwd, TYPE, MODE, Active/PASV endpoint, RNFR state, transfer ID, cancellation và worker state.
- `RNTO` chỉ hợp lệ sau `RNFR`; state được reset khi thành công, thất bại phù hợp, QUIT hoặc disconnect.
- `PORT` nhận đúng sáu số, từng số trong `0..255`, port hợp lệ và áp dụng chính sách chống client chỉ định IP tùy ý.
- `PASV` đàm phán UDP endpoint, đóng socket PASV cũ khi chuyển mode hoặc tạo endpoint mới.
- Không dùng `os.path.join` trực tiếp với client input để bỏ qua filesystem service.
- Không dùng kiểm tra prefix chuỗi đơn giản để xác định path nằm trong FTP root.

#### Transfer và cleanup

- `server/transfer_manager.py` phải điều phối RDT của B và filesystem service của C; `upload()`/`download()` không còn `pass`.
- `STOR`, `RETR`, `STOU`, `APPE` chạy transfer thật và trả reply đúng lifecycle.
- `STOU` trả tên duy nhất thật, không dùng tên cố định.
- `ABOR` gọi cancellation thật, đánh thức/dừng worker đang chờ, đóng data socket và yêu cầu C dọn file tạm.
- `ClientHandler` có `session_id`, unregister khi cleanup và đóng cả TCP/UDP socket.
- QUIT, disconnect bất ngờ và server shutdown không để session stale hoặc thread nền.

#### Đầu ra Role A

- Server TCP khởi động và nhận command từ client thật.
- `tests/test_command_parser.py`, `tests/test_commands.py`, `tests/test_session.py` không còn rỗng.
- Test kiểm tra happy path và invalid syntax/state/path, session isolation, reply code, disconnect và cleanup.
- Phần TCP format, session structure, state transition và self-assessment trong `docs/report.md` khớp code thật.
- `docs/genai-log-a.md` được cập nhật đầy đủ.

### Phase 3 — Tích hợp Role C với A/B

**Owner tích hợp:** Role C. **Owner lỗi module:** role sở hữu module tương ứng.

#### Công việc

- Nối `server/transfer_manager.py` với filesystem service và RDT theo shared contract.
- Dùng filesystem service của C cho mọi command có path:
  - `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `LIST`, `NLST`, `STAT`.
  - `SIZE`, `MDTM`, `DELE`, `RNFR`, `RNTO`, `HASH`.
  - `RETR`, `STOR`, `STOU`, `APPE`.
- Chặn traversal, absolute path ngoài root, symlink escape và prefix-collision.
- Giữ binary-safe I/O, file tạm, atomic replace và per-path lock.
- Không giữ global session lock trong lúc chờ UDP ACK.
- Nối progress callback thật vào CLI/log với session ID và transfer ID.
- Không log password hoặc nội dung file nhạy cảm.
- Ánh xạ exception/result có cấu trúc thành `425`, `426`, `550` hoặc reply phù hợp; không để exception thoát khỏi client thread.

#### Đầu ra Role C

- TransferManager dùng được API A/B/C đã thống nhất.
- Upload lỗi hoặc ABOR không phá file cũ và không để `.part`.
- Active-session table loại client đã mất kết nối.
- Log phân biệt được client, session và transfer đồng thời.
- Flowchart thread dispatch, Active/PASV, locking và TCP–UDP–filesystem trong tài liệu khớp code.

### Phase 4 — End-to-end, concurrency và demo evidence

**Owner:** Role C chủ trì. **Role A/B:** trực tiếp sửa lỗi thuộc module mình.

#### Ma trận end-to-end bắt buộc

| Operation | Active upload | Active download | PASV upload | PASV download |
|---|---:|---:|---:|---:|
| File rỗng | Pass | Pass | Pass | Pass |
| File text | Pass | Pass | Pass | Pass |
| File binary | Pass | Pass | Pass | Pass |
| File đúng bội chunk | Pass | Pass | Pass | Pass |

Mỗi ca phải có:

- TCP control reply đúng thứ tự.
- UDP data thực sự được truyền qua sender/receiver production.
- SHA-256 file nguồn và file đích giống nhau.
- Socket, thread và file tạm được cleanup.

#### Concurrency bắt buộc

- Ít nhất ba client kết nối đồng thời.
- CWD, TYPE, MODE, RNFR và endpoint không rò giữa session.
- Transfer ID/ACK không bị nhận nhầm giữa các transfer.
- Hai client ghi cùng file tuân theo lock/conflict policy, không trộn byte.
- STOU đồng thời tạo tên khác nhau.
- Một client lỗi hoặc disconnect không làm chết server hay transfer khác.
- Shutdown đóng listener, client sockets, UDP sockets và join worker hữu hạn.

## 6. Kế hoạch test và bằng chứng bàn giao

| Nhóm test | Owner chính | Test tối thiểu | Bằng chứng cần lưu |
|---|---|---|---|
| Import/startup | A/B | Import server, sender, receiver; start/stop server | Command và exit result |
| Parser/session | A | Empty input, syntax, login, RNFR order, isolation | Pytest test names/result |
| Commands/replies | A | Toàn bộ command mục 2.2, invalid state/argument | Expected/actual reply |
| RDT core | B | Header round-trip, checksum, ACK/sequence/retry | Production sender/receiver tests |
| Fault injection | B | Loss, duplicate, corruption, delay, reorder, retry exhausted | Kết quả hữu hạn và hash |
| Filesystem/security | C | Traversal, absolute path, symlink, prefix collision | Test path và exception mapping |
| File lifecycle | C | Atomic STOR, unique STOU, locked APPE, ABOR cleanup | Không còn `.part`, file cũ còn nguyên |
| Active/PASV E2E | A/B/C | Ma trận upload/download bốn loại file | Reply log và SHA-256 |
| Multi-client | C | Ít nhất ba client và transfer đồng thời | Active-session/log evidence |
| Full regression | C chủ trì | `python -m pytest -v` trên Linux/WSL2 | Toàn bộ suite pass |

Quy tắc test:

- Dùng `tmp_path` cho filesystem test và high ports riêng cho socket test.
- Luôn đóng socket và join thread.
- Không dùng `skip`, `xfail` hoặc mock bỏ qua toàn bộ protocol để che blocker.
- Fault-injection test phải đi qua sender/receiver production; mock chỉ được điều khiển mất/lỗi/trễ packet.
- Lưu command đã chạy, kết quả và demo evidence vào tài liệu phù hợp; không ghi runtime transfer data vào source directory.

## 7. Definition of Done tuần 2

Chỉ đánh dấu hoàn thành khi có bằng chứng cho từng mục:

- [ ] `server.threaded_server`, RDT sender và RDT receiver import được từ repository root.
- [ ] `python -m server.threaded_server` khởi động và shutdown sạch trên Linux/WSL2.
- [ ] Toàn bộ command trong mục 2.2 của đề được parse và trả reply phù hợp, gồm cả `NOOP`, `STAT`, `SIZE`, `MDTM` và `HELP`.
- [ ] Test Role A không còn rỗng và kiểm tra parser, session isolation, command/reply, invalid argument/state/path, disconnect và cleanup.
- [ ] Test Role B gọi sender/receiver production thật.
- [ ] Stop-and-Wait xử lý đúng ACK, sequence, checksum, timeout/retransmit, duplicate, corruption và out-of-order.
- [ ] Retry và receiver wait đều hữu hạn; hết retry trả failure và cleanup.
- [ ] Upload/download file rỗng, text, binary và file đúng bội chunk thành công bằng cả Active và PASV.
- [ ] Mọi ca truyền thành công có SHA-256 nguồn/đích giống nhau.
- [ ] Reply lifecycle đúng: `150 → 226`, hoặc `425`/`426`/`550` đúng nguyên nhân.
- [ ] `RETR`, `STOR`, `STOU`, `APPE`, `HASH` và `ABOR` chạy end-to-end; không trả thành công giả.
- [ ] Mọi filesystem operation bị giới hạn trong FTP root, gồm traversal, absolute path, symlink và prefix-collision.
- [ ] ABOR, timeout, disconnect và shutdown không để worker, socket, file tạm hoặc session stale.
- [ ] Ít nhất ba client hoạt động đồng thời với session/transfer riêng, không deadlock, ACK nhầm hoặc trộn dữ liệu.
- [ ] CLI/log hiển thị command, reply, mode, progress, client/session/transfer và active sessions; không lộ password.
- [ ] `python -m pytest -v` pass toàn bộ trên Linux/WSL2.
- [ ] Sequence diagram, header table, state machines, flowcharts và self-assessment khớp code đã chạy.
- [ ] `docs/genai-log-a.md`, `docs/genai-log-b.md` và `docs/genai-log-c.md` có prompt, raw output và refinement đầy đủ.
- [ ] Có demo evidence upload, download, SHA-256, active-session table và concurrent clients.

## 8. Quy trình báo cáo và bàn giao

Sau mỗi thay đổi, người thực hiện cập nhật bảng sau trong PR hoặc nhật ký làm việc:

| Hạng mục | Owner | File đã sửa | Test chứng minh | Kết quả | Blocker còn lại |
|---|---|---|---|---|---|
| _Điền sau mỗi vòng sửa_ | | | | | |

Mỗi lần bàn giao phải ghi:

- Input/output/exception của interface đã thay đổi.
- Ownership của socket, file handle và worker thread.
- Cancellation và cleanup behavior.
- Command test đã chạy và kết quả thật.
- Rủi ro hoặc dependency còn lại và role chịu trách nhiệm tiếp theo.

Không chỉnh đồng thời cùng một đoạn trong `docs/report.md`; chỉ định một editor và reviewer cho từng section. Commit theo mẫu `[role][module] short imperative description` và giữ mỗi commit trong phạm vi hẹp.

## 9. Thứ tự xử lý blocker ngắn gọn

1. **A/B:** Sửa import; chứng minh server và RDT import/chạy được.
2. **B:** Hoàn thiện RDT core và fault-injection test production.
3. **A/C:** Implement `TransferManager`, reply lifecycle và cancellation thật.
4. **A:** Hoàn thiện command còn thiếu, parser, session và test.
5. **C:** Nối filesystem an toàn, atomic upload, lock và cleanup.
6. **A/B/C:** Chạy Active/PASV end-to-end và SHA-256.
7. **C chủ trì:** Chạy multi-client, full regression và thu demo evidence.

Nếu một exit gate thất bại, quay lại bước tái hiện lỗi và sửa đúng owner. Không chuyển sang tối ưu nâng cao khi core transfer chưa đạt Definition of Done.

