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

- [ ] Sửa import package trong `server/` và chạy được `python -m server.threaded_server`.
- [ ] Hoàn thiện `TransferManager.upload()` và `download()`; không còn `pass`.
- [ ] Hoàn thiện `RETR`, `STOR`, `STOU`, `APPE`, `HASH`, `ABOR` qua RDT thật.
- [ ] Bổ sung `NOOP`, `STAT`, `SIZE`, `MDTM`, `HELP`.
- [ ] Đảm bảo reply `150 → 226`; lỗi trả `425`/`426`/`550` đúng nguyên nhân.
- [ ] Dùng filesystem service của C cho mọi client path.
- [ ] Sửa `PORT`, `PASV`, RNFR/RNTO, session isolation và cleanup.
- [ ] Viết test cho parser, session và command; không để file test rỗng.
- [ ] Cập nhật `docs/genai-log-a.md` và phần TCP trong `docs/report.md`.

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

- [ ] Sửa import trong `server/threaded_server.py`, `client_handler.py`, `command_handler.py`.
- [ ] Không dùng `sys.path` để che lỗi package nếu có thể dùng import chuẩn.
- [ ] `server.threaded_server` import được từ repository root.

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

- [ ] Input rỗng, whitespace, command lạ, thiếu/thừa argument không làm chết thread.
- [ ] Có đủ: `USER`, `PASS`, `QUIT`, `NOOP`, `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `LIST`, `NLST`, `STAT`, `SIZE`, `MDTM`, `TYPE`, `MODE`, `HELP`, `PORT`, `PASV`, `RETR`, `STOR`, `STOU`, `APPE`, `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`.
- [ ] `MODE B/C` trả `502` nếu chưa hỗ trợ thật.
- [ ] `LIST` là detailed listing; `NLST` là tên file; hỗ trợ optional path.

### Session và endpoint

- [ ] Mỗi client có login, cwd, TYPE, MODE, endpoint, RNFR, transfer ID và cancel state riêng.
- [ ] `RNTO` chỉ hợp lệ sau `RNFR`; reset state sau success/failure/QUIT/disconnect.
- [ ] `PORT` kiểm tra đủ 6 số, từng số `0..255`, port hợp lệ và policy IP.
- [ ] `PASV` dùng UDP endpoint, đóng endpoint cũ khi đổi mode.
- [ ] Không dùng string-prefix để bảo vệ FTP root.

### Transfer và cleanup

- [ ] `TransferManager` gọi RDT B + filesystem C.
- [ ] `STOU` không dùng tên cố định.
- [ ] `ABOR` đánh thức/dừng worker, đóng data socket và dọn file tạm.
- [ ] `ClientHandler` có session ID và unregister khi cleanup.
- [ ] QUIT/disconnect/shutdown không để thread/socket/session stale.

### Test Role A

- [ ] `tests/test_command_parser.py` có test thật.
- [ ] `tests/test_session.py` có test thật.
- [ ] `tests/test_commands.py` có test thật.
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
