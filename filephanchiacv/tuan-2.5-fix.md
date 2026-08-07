# TUẦN 2.5 — CHECKLIST SỬA LỖI VÀ TÍCH HỢP

**Thời gian:** 02/08/2026–08/08/2026  
**Mục tiêu:** biến các module rời rạc thành luồng Hybrid FTP chạy thật: TCP control + UDP/RDT data + filesystem an toàn.  
**Tài liệu yêu cầu gốc:** [`Project1_SocketProgramming_2026.md`](./Project1_SocketProgramming_2026.md)

## Cách dùng checklist

- `[ ]` Chưa làm · `[x]` Đã làm và có test · `[!]` Đang bị chặn.
- Mỗi mục chỉ được đánh `[x]` khi có test/log/evidence tương ứng.
- Không chuyển phase nếu **exit gate** của phase trước chưa đạt.
- Khi sửa shared contract (header, API, reply, cleanup), A/B/C phải xác nhận cùng nhau.

## 1. Bảng trạng thái nhanh

| Role | Phụ trách | Blocker cần xử lý trước |
|---|---|---|
| **A** | TCP command, reply, session, `TransferManager` | Import server, transfer đang `pass`, thiếu command/test |
| **B** | UDP/RDT, ACK, checksum, retry, cancellation | Import sender/receiver, dependency sai, test chưa chạy production |
| **C** | Filesystem, concurrency, integration, evidence | Chờ A/B chốt contract để ráp end-to-end |

### Role A — việc của A

- [x] Sửa import package trong `server/`; `server.threaded_server` import được từ repository root. Việc chạy server thực tế vẫn cần kiểm tra trên Linux/WSL2.
- [ ] Hoàn thiện `TransferManager.upload()` và `download()`; không còn `pass`.
- [ ] Hoàn thiện `RETR`, `STOR`, `STOU`, `APPE`, `HASH`, `ABOR` qua RDT thật.
- [x] Bổ sung `NOOP`, `STAT`, `SIZE`, `MDTM`, `HELP`.
- [ ] Đảm bảo reply `150 → 226`; lỗi trả `425`/`426`/`550` đúng nguyên nhân.
- [ ] Dùng filesystem service của C cho mọi client path.
- [ ] Sửa `PORT`, `PASV`, RNFR/RNTO, session isolation và cleanup.
- [x] Viết test cơ bản cho parser, session và command; các file test không còn rỗng. Coverage transfer/security vẫn thiếu.
- [x] Cập nhật `docs/genai-log-a.md` và phần TCP trong `docs/report.md`; cần chỉnh lại các claim transfer nếu chưa có E2E evidence.

### Role B — việc của B

- [ ] Thống nhất tên/import `RDTHeader`, sender, receiver và file helper.
- [ ] Chốt header: byte order, sequence, ACK, flags, length, checksum, `transfer_id`.
- [ ] Hoàn thiện Stop-and-Wait cho DATA/ACK/FIN/ABORT.
- [ ] Xử lý checksum lỗi, duplicate, out-of-order, sai peer/transfer.
- [ ] Giới hạn timeout/retry/receiver wait; không được treo vô hạn.
- [ ] Dọn socket/tài nguyên bằng `try/finally`; cancellation phải dừng thật.
- [ ] Viết fault-injection test gọi sender/receiver production thật.
- [ ] Test file rỗng, text, binary, nhỏ hơn chunk, một chunk và đúng bội chunk.
- [ ] Cập nhật bảng header, state machine và `docs/genai-log-b.md`.

### Role C — việc của C

- [ ] Chốt và cung cấp API filesystem dùng chung cho A/B; mọi client path phải
  đi qua `common.filesystem_service.FilesystemService`.
- [ ] Kiểm tra root confinement cho `CWD`, `LIST`, `NLST`, `STAT`, `SIZE`,
  `MDTM`, `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `HASH`, `RETR`, `STOR`, `STOU` và
  `APPE`; chặn `..`, absolute path ngoài root, symlink escape và prefix collision.
- [ ] Hoàn thiện atomic upload: ghi `.part`, chỉ `os.replace` sau FIN hợp lệ;
  lỗi, timeout hoặc ABOR phải xóa file tạm và giữ file cũ.
- [ ] Hoàn thiện chính sách ghi đồng thời: per-path lock cho `APPE`, tên duy nhất
  cho `STOU`, không trộn byte giữa các client và không giữ global lock khi chờ
  UDP ACK.
- [ ] Nối `TransferManager` với filesystem service và adapter RDT của B; ánh xạ
  `TransferResult`/`FilesystemOperationError` thành reply của A.
- [ ] Hoàn thiện threaded server: session ID, active-session registry, session
  isolation, một client lỗi không làm chết server, cleanup khi QUIT/disconnect/
  shutdown và join worker hữu hạn.
- [ ] Đảm bảo `ABOR`, timeout và disconnect đóng TCP/UDP socket, dừng worker,
  clear session state và không để `.part` hoặc session stale.
- [ ] Hoàn thiện CLI/log: connection state, command/reply, Active/PASV mode,
  transfer progress, timestamp, client IP, session ID, transfer ID và kết quả;
  không log password hoặc nội dung file.
- [ ] Viết test Role C cho traversal, symlink/prefix collision, atomic failure,
  APPE lock, STOU unique, nhiều client, cùng file, disconnect giữa transfer,
  server shutdown và active-session cleanup.
- [ ] Chạy integration test TCP control + UDP data + filesystem cho Active/PASV,
  upload/download, file rỗng/text/binary/chunk-boundary và SHA-256.
- [ ] Thu evidence: path-security log, `.part` cleanup, concurrent-client log,
  active-session table, CLI progress và command log đã redact password.
- [ ] Cập nhật `docs/role-c-week-2.md`, phần Role C trong `docs/report.md` và
  `docs/genai-log-c.md` bằng prompt/raw output/refinement/evidence thật.

## 2. Shared contract — phải chốt trước khi ráp

### TCP → transfer

- [ ] Input gồm session, operation (`RETR`/`STOR`/`STOU`/`APPE`), path đã validate, mode và endpoint.
- [ ] `150`: data channel sẵn sàng và transfer bắt đầu thật.
- [ ] `226`: chỉ trả sau khi truyền và commit file thành công.
- [ ] `425`: không mở/xác định được data channel.
- [ ] `426`: timeout, protocol error hoặc bị hủy.
- [ ] `550`: path/file không hợp lệ.

### RDT

- [ ] Chốt flags `START`, `DATA`, `ACK`, `FIN`, `ABORT`.
- [ ] Chốt chunk size, timeout, retry limit, inactivity timeout.
- [ ] Chốt checksum bao phủ phần nào và quy tắc duplicate/out-of-order.
- [ ] Chốt progress callback, cancellation và kết quả success/failure.

### Filesystem

- [ ] A không tự truy cập path từ client; mọi path đi qua C.
- [ ] Upload ghi `.part`, chỉ atomic replace sau FIN hợp lệ.
- [ ] `STOU` tạo tên server-generated không trùng.
- [ ] `APPE` có lock; ABOR/timeout/disconnect xóa file tạm nhưng giữ file cũ.

### API TransferManager đã chốt

`TransferManager` nằm ở `server/transfer_manager.py`. A gọi API này; C giữ
filesystem lifecycle; B cắm adapter RDT qua `sender`/`receiver`.

```python
manager = TransferManager(
    filesystem=filesystem_service,
    sender=rdt_sender,
    receiver=rdt_receiver,
)

result = manager.upload(
    session,
    validated_or_absolute_path,
    data_socket=session.data_socket,
    endpoint=(session.data_host, session.data_port),
)

result = manager.download(
    session,
    validated_or_absolute_path,
    data_socket=session.data_socket,
    endpoint=(session.data_host, session.data_port),
)
```

Adapter B tối thiểu:

```python
receiver.receive(data_socket, endpoint, cancel_event) -> Iterable[bytes]
sender.send(chunks, data_socket, endpoint, cancel_event) -> int | bool
```

`TransferResult` có `success`, `reply_code`, `bytes_transferred`, `path` và
`error`; object này vẫn dùng được với `if result`. `cancel(session)` đặt
`session.transfer_cancel_event`, đóng data socket và để filesystem dọn `.part`.
`append(...)` và `upload_unique(...)` dùng cho `APPE` và `STOU`.

## 3. Phase 0 — Khôi phục import và khả năng chạy

**Owner:** A (`server/`) · B (`common/rdt_*`) · C review package layout

### Role A

- [x] Sửa import trong `server/threaded_server.py`, `client_handler.py`, `command_handler.py`.
- [x] Không dùng `sys.path` để che lỗi package trong các module Role A hiện tại.
- [x] `server.threaded_server` import được từ repository root; chưa xác nhận startup/stop sạch trên Linux/WSL2.

### Role B

- [ ] Sửa `common.RDTHeader`/`common.rdt_header` thành một tên thống nhất.
- [ ] Thay `common.file_utils` bằng API thật trong `common/file_handler.py` hoặc contract mới.
- [ ] Import độc lập được header, sender, receiver và `rdt_utils`.

### Exit gate

- [ ] `python -c "import server.threaded_server"` pass.
- [ ] Import sender/receiver pass.
- [ ] Server start/stop sạch.
- [ ] Pytest đi qua collection; nếu lỗi thì ghi exception và owner.

## 4. Phase 1 — Role B: RDT core

**Owner:** B · **Review:** A kiểm tra reply/event, C kiểm tra file/cancel

- [ ] Serialize/deserialize network byte order cố định.
- [ ] Reject datagram ngắn, length sai, flags sai, transfer sai.
- [ ] Sender chỉ nhận ACK đúng sequence, transfer ID và UDP peer.
- [ ] Receiver chỉ ghi payload đúng checksum và đúng sequence.
- [ ] Duplicate gửi lại ACK nhưng không ghi lần hai.
- [ ] Out-of-order/sai transfer bị drop, không advance sequence.
- [ ] FIN là tín hiệu kết thúc; không suy luận EOF từ payload ngắn.
- [ ] Retry và receiver inactivity timeout đều hữu hạn.
- [ ] ABORT dừng hai phía; socket/worker được cleanup.
- [ ] Progress chỉ tính byte đã ACK/ghi thật.

### Fault-injection test

| Ca lỗi | Kết quả bắt buộc | Đã test |
|---|---|---:|
| Mất DATA | Retransmit hoặc fail hữu hạn | [ ] |
| Mất ACK | Không ghi duplicate; ACK được gửi lại | [ ] |
| Duplicate | Payload xuất hiện một lần | [ ] |
| Corruption | Payload lỗi không ghi | [ ] |
| Delay | Không ACK nhầm packet cũ | [ ] |
| Out-of-order | Không mất/đảo dữ liệu | [ ] |
| Hết retry | Failure + cleanup hữu hạn | [ ] |
| ABORT | Hai phía dừng, không còn tài nguyên | [ ] |

### Exit gate Role B

- [ ] Sender/receiver chạy bằng UDP thật.
- [ ] Hash file nhận giống file nguồn.
- [ ] Test file rỗng/text/binary/chunk-boundary pass.
- [ ] `docs/report.md` có header table + state machine.

## 5. Phase 2 — Role A: TCP control và session

**Owner:** A · **Review:** C kiểm tra path/session, B kiểm tra endpoint

### Parser và command

- [x] Input lỗi cơ bản, command lạ và UTF-8 lỗi không làm chết client thread; test framing đã có. Ma trận thiếu/thừa argument chưa đầy đủ.
- [x] Có đủ dispatcher cho toàn bộ command: `USER`, `PASS`, `QUIT`, `NOOP`, `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `LIST`, `NLST`, `STAT`, `SIZE`, `MDTM`, `TYPE`, `MODE`, `HELP`, `PORT`, `PASV`, `RETR`, `STOR`, `STOU`, `APPE`, `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`.
- [x] `MODE B/C` trả `502` nếu chưa hỗ trợ thật.
- [x] `LIST` là detailed listing; `NLST` là tên file; hỗ trợ optional path.

### Session và endpoint

- [ ] Mỗi client có login, cwd, TYPE, MODE, endpoint, RNFR và cancel state riêng; transfer ID/session isolation cho transfer thật chưa hoàn tất.
- [x] `RNTO` chỉ hợp lệ sau `RNFR`; reset state sau success/failure/QUIT/disconnect.
- [ ] `PORT` kiểm tra đủ 6 số, từng số `0..255`, port hợp lệ; policy IP chống FTP bounce chưa hoàn tất.
- [x] `PASV` dùng UDP endpoint và đóng endpoint cũ khi tạo PASV mới; cleanup khi đổi mode/shutdown cần bổ sung kiểm chứng.
- [ ] Không dùng trực tiếp path API ngoài filesystem service để bảo vệ FTP root; `SIZE`, `MDTM`, `HASH` vẫn còn thao tác filesystem trực tiếp.

### Transfer và cleanup

- [ ] `TransferManager` gọi RDT B + filesystem C.
- [ ] `STOU` không dùng tên cố định.
- [ ] `ABOR` đánh thức/dừng worker, đóng data socket và dọn file tạm.
- [x] `ClientHandler` có session ID và unregister khi cleanup.
- [ ] QUIT/disconnect/shutdown không để thread/socket/session stale.

### Test Role A

- [x] `tests/test_command_parser.py` có test thật.
- [x] `tests/test_session.py` có test thật.
- [x] `tests/test_commands.py` có test thật.
- [ ] Có test happy path, invalid argument/state/path, reply, isolation, disconnect và cleanup.

## 6. Phase 3 — Tích hợp A + B + C

**Owner tích hợp:** C · **Owner sửa lỗi:** role sở hữu module

- [ ] Tất cả command có path dùng filesystem service.
- [ ] Chặn traversal, absolute path ngoài root, symlink escape và prefix-collision.
- [ ] STOR atomic; APPE có lock; STOU unique; ABOR không phá file cũ.
- [ ] Reply/result có cấu trúc và không thoát exception khỏi client thread.
- [ ] Progress/log có client IP, session ID, transfer ID; không log password.
- [ ] Không giữ global lock trong lúc chờ UDP ACK.
- [ ] Active-session table loại client đã mất kết nối.

## 7. Phase 4 — End-to-end và demo

### Ma trận bắt buộc

| File | Active upload | Active download | PASV upload | PASV download |
|---|---:|---:|---:|---:|
| Rỗng | [ ] | [ ] | [ ] | [ ] |
| Text | [ ] | [ ] | [ ] | [ ] |
| Binary | [ ] | [ ] | [ ] | [ ] |
| Đúng bội chunk | [ ] | [ ] | [ ] | [ ] |

Mỗi ô chỉ đánh `[x]` khi có reply đúng, UDP thật, SHA-256 khớp và cleanup sạch.

### Multi-client

- [ ] Ít nhất 3 client đồng thời.
- [ ] Session/cwd/mode/endpoint độc lập.
- [ ] Không ACK nhầm, không trộn dữ liệu, không deadlock.
- [ ] Hai client ghi cùng file tuân thủ lock/conflict policy.
- [ ] Disconnect một client không làm chết client khác.

### Evidence cần lưu

- [ ] Upload/download log.
- [ ] SHA-256 nguồn/đích.
- [ ] Active-session table.
- [ ] Concurrent-client log.
- [ ] Command/reply log không lộ password.

## 8. Definition of Done

- [ ] Import/startup pass trên Linux/WSL2.
- [ ] Toàn bộ command đề bài có reply phù hợp.
- [ ] RDT xử lý ACK, sequence, checksum, timeout, retry, duplicate, corruption, out-of-order.
- [ ] Retry/receiver wait hữu hạn; ABOR/timeout/disconnect/shutdown cleanup đúng.
- [ ] Active và PASV upload/download pass cho file rỗng, text, binary và chunk-boundary.
- [ ] SHA-256 nguồn/đích giống nhau.
- [ ] `RETR`, `STOR`, `STOU`, `APPE`, `HASH`, `ABOR` chạy end-to-end.
- [ ] Ít nhất 3 client chạy đồng thời, session độc lập.
- [ ] CLI/log hiển thị trạng thái, progress, client/session/transfer và active sessions.
- [ ] `python -m pytest -v` pass toàn bộ trên Linux/WSL2.
- [ ] Diagram, header table, state machine, flowchart và self-assessment khớp code.
- [ ] GenAI log A/B/C có prompt, raw output và refinement.
- [ ] Demo evidence được lưu trong report.

## 9. Mẫu cập nhật sau mỗi vòng sửa

| Ngày | Role | Hạng mục | File sửa | Test/evidence | Kết quả | Blocker tiếp theo |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Commit theo mẫu `[role][module] short imperative description`; mỗi commit chỉ nên chứa một nhóm thay đổi liên quan.

## 10. Thứ tự xử lý trong tuần

1. **A/B:** sửa import và chứng minh server/RDT import được.
2. **B:** hoàn thiện RDT core + fault injection production.
3. **A/C:** hoàn thiện `TransferManager`, reply lifecycle và cancellation.
4. **A:** hoàn thiện command/session/test.
5. **C:** nối filesystem an toàn, atomic upload, lock, cleanup.
6. **A/B/C:** chạy Active/PASV end-to-end và SHA-256.
7. **C chủ trì:** chạy multi-client, full regression và thu evidence.

Không tối ưu Selective Repeat/sliding window trước khi toàn bộ checklist core ở trên đạt.

## 11. Kết quả kiểm tra lại Role A và Role B — 07/08/2026

Phần này ghi các thiếu sót tìm thấy khi đối chiếu code production với
`Project1_SocketProgramming_2026.md` và `tuan-2-chi-tiet.md`. Các mục dưới đây
chưa được xem là hoàn thành chỉ vì unit test đơn giản đang pass.

### 11.1 Role A — thiếu sót cụ thể cần sửa

#### TCP parser và vòng đời command

- [x] Thêm buffer theo từng client và tách command bằng `\r\n` trong
  `server/client_handler.py`; một lần `recv(1024)` có thể chứa nửa command hoặc
  nhiều command, không được đưa toàn bộ buffer thành một command duy nhất.
- [ ] Bắt `UnicodeDecodeError`, lỗi handler và lỗi ngoài `ConnectionResetError`
  theo từng command; một input xấu không được làm chết client thread mà không có
  reply/log phù hợp.
- [ ] Lập bảng số lượng tham số cho toàn bộ command: lệnh không nhận tham số phải
  từ chối tham số thừa; lệnh bắt buộc tham số phải trả `501` khi thiếu. Hiện các
  lệnh như `PASS`, `PORT`, `RNTO`, `NOOP`, `PASV`, `QUIT` chưa được kiểm tra đồng
  nhất.
- [x] Xóa command debug `HELLO`, `ECHO`, `TEST_MSG_*` khỏi dispatcher production,
  hoặc cô lập rõ vào chế độ test; đề chỉ cho phép danh sách command mục 2.2.
- [ ] Sửa authentication thành contract tài khoản rõ ràng; hiện mọi username
  không rỗng đều đăng nhập được bằng password hard-code `123456`. Reset state
  đăng nhập đúng khi `USER` mới, `QUIT` và disconnect.

#### Command, path và reply

- [ ] Thay toàn bộ `os.path.join`, `abspath`, `startswith`, `open`, `os.rename`,
  `os.remove`, `os.mkdir`, `os.rmdir`, `os.listdir` trực tiếp trong
  `server/command_handler.py` bằng filesystem service của C. Phải chặn prefix
  collision và symlink escape cho `CWD`, `LIST`, `NLST`, `SIZE`, `MDTM`, `HASH`,
  `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `RETR`, `STOR`, `STOU`, `APPE`.
- [x] Sửa `LIST` thành detailed listing có tối thiểu name, size, type và
  permissions; hiện code chỉ trả tên giống `NLST`. Chốt LIST/NLST đi trên data
  channel hay control channel và làm nhất quán với sequence diagram/reply
  `150 -> 226`.
- [x] Reset `rename_from` cả khi `RNTO` thiếu tham số, thất bại, có command phá
  chuỗi, `QUIT` hoặc disconnect; validate cả source và destination qua filesystem
  service.
- [ ] `PORT` phải kiểm tra đúng 6 số nguyên trong `0..255`, port khác 0 và IP theo
  policy chống FTP bounce (thường phải trùng IP TCP peer). Hiện code nhận số âm,
  số lớn và IP tùy ý.
- [ ] `PASV` phải đóng UDP socket/endpoint cũ trước khi tạo endpoint mới, quảng bá
  đúng server address thay vì luôn `127.0.0.1`, và cleanup socket khi đổi mode,
  `QUIT`, disconnect hoặc shutdown.
- [ ] Không dùng `except:` trống trong command path. Ánh xạ lỗi có cấu trúc sang
  `425`, `426`, `450/550` hoặc `451` để không biến mọi lỗi thành “file not found”.

#### Transfer và cancellation

- [ ] Nối `ClientHandler -> CommandHandler -> TransferManager` với filesystem,
  sender và receiver production thật. Hiện `ClientHandler` tạo
  `TransferManager()` không có adapter, nên `STOR/RETR` không thể truyền RDT.
- [ ] Sửa contract adapter: `TransferManager` đang cần `send(chunks, socket,
  endpoint, event)` và `receive(socket, endpoint, event) -> Iterable[bytes]`,
  nhưng Role B hiện cung cấp `send_file_rdt(filepath, ip, port, ...)` và
  `receive_file_rdt(socket, save_path, ...) -> bool`. Hai API chưa cắm được vào
  nhau.
- [ ] Mọi `RETR/STOR/STOU/APPE` phải trả `150` trước khi bắt đầu thật và chỉ trả
  `226` sau khi RDT + commit thành công. Hiện `STOR/RETR` chỉ trả kết quả cuối;
  `STOU/APPE` chỉ tạo state và trả `150` nhưng không chạy transfer.
- [ ] `STOU` phải gọi `upload_unique()` và trả tên duy nhất thật; không dùng cố
  định `upload_001`. `APPE` phải gọi `append()` với lock và lifecycle file tạm.
- [ ] `ABOR` phải gọi `TransferManager.cancel(session)`; hiện chỉ đặt boolean nên
  không đánh thức receiver, không đóng socket và không dọn file tạm.
- [ ] Chạy transfer trong worker/state machine phù hợp để TCP thread vẫn nhận được
  `ABOR` trong lúc transfer đang diễn ra; nếu transfer chạy đồng bộ trong chính
  vòng `recv`, client không thể hủy bằng control channel.
- [ ] Cleanup phải cancel transfer, đóng data socket, clear endpoint,
  `rename_from`, cancel event và current transfer; sau đó unregister và join
  worker hữu hạn. Hiện `ClientHandler.cleanup()` chỉ đóng TCP socket và
  unregister.
- [ ] Không dùng fallback bắt `TypeError` rồi gọi adapter lần hai trong
  `TransferManager._invoke`; cách này có thể che một bug `TypeError` phát sinh
  bên trong adapter. Chốt một protocol/signature và validate ngay khi inject.

#### Test và tài liệu Role A

- [x] Thêm test TCP framing: command bị chia qua hai `recv`, hai command trong một
  `recv`, CRLF thừa, UTF-8 lỗi và command dài hơn buffer.
- [ ] Thêm test cho mọi command về thiếu/thừa argument, login state, reply code,
  path traversal, prefix collision, symlink escape, `PORT` bounds/IP policy,
  PASV socket replacement và RNFR state reset.
- [ ] Thêm test production cho chuỗi `150 -> 226/425/426/550`, ABOR khi transfer
  đang chạy, disconnect giữa transfer và cleanup không còn thread/socket.
- [ ] Sửa `docs/report_role_a_week2.md` và `docs/report.md`: không được ghi “đã
  hoàn thành/đã test” cho transfer command khi code mới là skeleton hoặc chưa nối
  RDT production.

### 11.2 Role B — thiếu sót cụ thể cần sửa

#### Header và validation

- [ ] Thêm `transfer_id` vào `RDTHeader` để phân biệt datagram của nhiều transfer;
  cập nhật byte-level table, network byte order và test round-trip/giới hạn từng
  field.
- [ ] Chốt flag hợp lệ và tổ hợp flag hợp lệ. `FLAG_DATA = 0` hiện không thể được
  nhận diện bằng phép kiểm tra bit; `START` đã khai báo nhưng sender không gửi và
  receiver không xử lý.
- [ ] Validate datagram chính xác: `header.length` không vượt chunk/datagram,
  không lớn hơn số byte payload thật, không có trailing data ngoài contract và
  packet ngắn phải bị drop an toàn.
- [ ] Chốt checksum bao phủ header quan trọng + payload, hoặc giải thích rõ nếu
  chỉ bao phủ payload. Sender phải kiểm tra checksum/length/flags của ACK; hiện
  ACK giả hoặc ACK hỏng vẫn có thể được chấp nhận.

#### Stop-and-Wait và protocol correctness

- [ ] Receiver chỉ gửi ACK sau khi phân loại sequence. Hiện
  `common/rdt_receiver.py` gửi ACK trước khi kiểm tra `expected_seq`, vì vậy gói
  future/out-of-order cũng được ACK và sender có thể bỏ qua dữ liệu chưa ghi.
- [ ] Sender chỉ nhận ACK từ đúng UDP peer, đúng `seq_num/ack_num`, đúng
  `transfer_id`, đúng flag, length và checksum. Hiện địa chỉ trả về từ
  `recvfrom()` bị bỏ qua.
- [ ] Receiver khóa đúng peer + transfer sau START; drop packet từ peer/transfer
  khác và không gửi ACK gây nhiễu.
- [ ] Xử lý mất ACK của FIN: receiver không được thoát theo cách khiến FIN gửi lại
  không còn ai ACK. Cần FIN/ACK closing state với timeout hữu hạn hoặc handshake
  tương đương.
- [ ] Receiver phải có inactivity timeout/retry budget hữu hạn. Hiện
  `socket.timeout` chỉ `continue`, nên có thể chạy vô hạn khi sender chết hoặc
  mất FIN.
- [ ] ABORT phải có state rõ ràng ở cả hai phía, được xác nhận nếu contract yêu
  cầu, và mọi đường thoát phải cleanup bằng `try/finally`. Hiện receiver gặp
  ABORT trả `False` nhưng không tự đóng/dọn socket nhất quán.
- [ ] Quy định giới hạn sequence number và test wrap-around; hiện sequence tăng
  theo `enumerate()` đến khi `struct.pack('!I')` lỗi với file đủ lớn.
- [ ] Không `list(read_file_chunks(filepath))` toàn bộ file trong RAM. Sender phải
  stream chunk và dùng look-ahead/metadata để đánh FIN, bảo đảm file lớn vẫn
  truyền được.
- [ ] Progress callback phải có contract thống nhất; sender gọi
  `(transferred_bytes, total_size)` nhưng receiver chỉ gọi `(len(payload))`.

#### Fault injection, integration và tài liệu Role B

- [ ] Chuyển các test trong `tests/test_rdt.py` từ kiểm tra biến giả sang gọi
  sender/receiver production; các test hiện tại không chứng minh retransmit,
  duplicate handling, reorder hoặc max-retry của code thật.
- [ ] Bổ sung fault proxy deterministic cho từng ca riêng: mất DATA, mất ACK (đặc
  biệt ACK của FIN), delay, duplicate, reorder, corrupt header, corrupt payload,
  ACK sai peer/sequence/transfer, hết retry và ABORT. Dùng port động thay vì cố
  định `8888/9996/9997/9999` để tránh xung đột và test flaky.
- [ ] Test sender/receiver production với file nhỏ hơn chunk, đúng một chunk,
  đúng bội chunk, lớn hơn nhiều chunk, file rỗng và binary; mọi ca phải join
  thread hữu hạn, so SHA-256 và kiểm tra không còn socket/file tạm.
- [ ] Viết adapter đúng contract của `TransferManager` và test tích hợp qua
  `RETR/STOR` thật; test RDT độc lập chưa chứng minh hệ thống Hybrid FTP chạy
  end-to-end.
- [ ] Cập nhật `docs/report.md` với header thực tế, sender/receiver state machine,
  FIN closing state, timeout/retry, peer/transfer validation và cancellation;
  cập nhật `docs/genai-log-b.md` bằng nội dung thật thay cho template.

### 11.3 Bằng chứng kiểm tra hiện tại

- Lệnh `wsl python3 -m pytest -q` chưa chạy được vì WSL2 thiếu package `pytest`.
- Lệnh `wsl python3 -m unittest discover -s tests -v` chạy 27 test: 21 pass,
  1 fail và 5 lỗi import. Ca fail là
  `TestRDTFaultInjection.test_loss_and_corruption_recovery`: sender hết 10 lần
  retry ở packet FIN cuối và trả `False`.
- Năm lỗi import đến từ các module test cần `pytest`, không phải bằng chứng code
  production pass: `test_cli_display`, `test_dir_manager`, `test_file_handler`,
  `test_filesystem_service`, `test_threaded_server`.
- Các test Role A hiện pass trong lần chạy `unittest`, nhưng mới kiểm tra happy
  path cơ bản; chưa bao phủ framing TCP, RDT integration, cancellation thật,
  path/symlink attack và cleanup giữa transfer.

### 11.4 Exit gate bổ sung sau audit

- [ ] Cài dependency test theo README/AGENTS và chạy
  `python -m pytest -v` trên Linux/WSL2; collection phải sạch và toàn bộ suite
  pass ít nhất 3 lần liên tiếp (fault test không flaky).
- [ ] Có một test end-to-end đi qua đúng code production:
  `TCP command -> TransferManager -> RDT adapter -> UDP socket -> filesystem`,
  không gọi tắt helper test.
- [ ] Có trace/evidence cho ACK của FIN bị mất, out-of-order không được ACK sai,
  ABOR giữa transfer và receiver timeout; tất cả kết thúc hữu hạn, hash đúng và
  không còn worker/socket/file tạm.
