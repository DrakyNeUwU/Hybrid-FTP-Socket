# Requirement Checklist — Project1 Hybrid FTP

**Nguồn chuẩn:** `filephanchiacv/Project1_SocketProgramming_2026.md`  
**Kế hoạch triển khai:** `filephanchiacv/tuan-2-chi-tiet.md`  
**Quy tắc:** trạng thái bên dưới phản ánh code/test hiện tại; không đánh dấu
`Verified` nếu chưa có test hoặc evidence thật.

## RQ-01 — Chức năng và nền tảng

- [ ] Python/native low-level socket API; không dùng FTP framework, KCP, QUIC,
  libcurl FTP wrapper hoặc thư viện transfer dựng sẵn.
- [ ] Hybrid architecture: TCP control và UDP data độc lập.
- [ ] File payload thật đi qua UDP/RDT.
- [ ] CLI/GUI hiển thị network state, command và transfer progress.

## RQ-02 — Command bắt buộc qua TCP control

- [ ] `USER`, `PASS`, `QUIT`, `NOOP`.
- [ ] `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`.
- [ ] `LIST [path]`, `NLST [path]`, `STAT [path]`.
- [ ] `SIZE`, `MDTM`, `TYPE A/I`, `MODE S/B/C`.
- [ ] `PORT`, `PASV`.
- [ ] `RETR`, `STOR`, `STOU`, `APPE`.
- [ ] `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`, `HELP [command]`.
- [ ] Mọi command nhận reply ba chữ số qua TCP; có reply 1xx/2xx/3xx/4xx/5xx
  phù hợp, gồm tối thiểu 220, 221, 226, 230, 250, 331, 350, 425, 426, 450,
  500, 501, 502, 530, 550.

## RQ-03 — Control-message và session

- [ ] Control request có dạng `COMMAND [argument]\r\n`.
- [ ] TCP parser tách command/argument an toàn khi recv bị chia hoặc gộp.
- [ ] Session giữ auth, current working directory, TYPE, MODE, endpoint và
  transfer state riêng cho từng client.
- [ ] Client disconnect/QUIT kết thúc session sạch.

## RQ-04 — UDP data và RDT

- [ ] Chỉ dùng UDP socket cho payload.
- [ ] RDT tự xây dựng, xử lý mất gói, corruption, duplicate và out-of-order.
- [ ] Header có sequence number, ACK, checksum, flags và payload length; byte
  order cố định.
- [ ] Stop-and-Wait có timeout, retransmission và retry hữu hạn; ACK/sequence
  được kiểm tra đúng peer và transfer.
- [ ] FIN/EOF rõ ràng; không suy luận EOF chỉ từ payload ngắn.
- [ ] ABORT/cancellation dừng sender/receiver và cleanup.

## RQ-05 — Active/PASV

- [ ] `PORT h1,h2,h3,h4,p1,p2` có validation đầy đủ.
- [ ] `PASV` tạo endpoint server và trả IP/port qua TCP.
- [ ] Upload/download chạy được ở cả Active và PASV; đổi mode không để endpoint
  cũ hoặc socket stale.

## RQ-06 — Filesystem và integrity

- [ ] Binary-safe I/O cho text, image, archive, video nhỏ và file rỗng.
- [ ] Nested tree operations và metadata.
- [ ] Mọi path nằm trong FTP root; chặn `..`, absolute ngoài root, symlink escape
  và prefix collision.
- [ ] STOR atomic; lỗi/ABOR không phá file cũ.
- [ ] STOU tạo tên server-generated duy nhất.
- [ ] APPE có chính sách lock/conflict rõ ràng.
- [ ] SHA-256 trước/sau transfer giống nhau.

## RQ-07 — Client/server/concurrency

- [ ] TCP server/client chạy được trên môi trường sạch.
- [ ] Multi-thread hoặc multi-process server cô lập session.
- [ ] Ít nhất nhiều client đồng thời không deadlock, ACK nhầm hoặc trộn dữ liệu.
- [ ] Worker, TCP/UDP socket, session registry và file tạm cleanup hữu hạn.

## RQ-08 — Logging, CLI và evidence

- [ ] CLI hiển thị trạng thái kết nối, command, reply, mode và progress.
- [ ] Server log có timestamp, client IP, command, session/transfer ID và kết
  quả; không log password hoặc nội dung nhạy cảm.
- [ ] Evidence gồm upload, download, hash comparison, connected-client table và
  concurrent-session test.

## RQ-09 — Testing

- [ ] Unit test command/parser/session/filesystem.
- [ ] Fault injection: mất DATA/ACK, delay, duplicate, corruption, reorder và
  hết retry.
- [ ] Integration/e2e test TCP control + UDP data + filesystem.
- [ ] Test Active/PASV, text/binary/file-boundary, ABOR/disconnect và nhiều client.

## RQ-10 — Technical report và diagrams

- [ ] Application scenario và sequence diagram TCP+UDP.
- [ ] Data structures: TCP format, UDP header, session.
- [ ] Flowcharts: thread dispatch, RDT sender/receiver, Active/PASV toggle.
- [ ] Task assignment matrix.
- [ ] Self-assessment và peer evaluation, contribution tổng 100%.
- [ ] GenAI appendix gồm exact prompt, raw output và refinement.
- [ ] Demo evidence.

## RQ-11 — Academic integrity và cá nhân

- [ ] Code có version control và mỗi thành viên hiểu module của mình lẫn shared
  architecture.
- [ ] Không dùng code bên ngoài không khai báo.
- [ ] GenAI dùng phải ghi lại trung thực; không giữ code mà thành viên không thể
  giải thích khi viva.

## RQ-12 — Mức đánh giá

- **Basic:** auth, ASCII, một file upload/download, một mode cố định.
- **Advanced:** binary an toàn, directory tree, Active/PASV, multi-client session
  isolation.
- **Excellent:** custom RDT ACK/sequence/timeout-retransmit, congestion/flow
  control và end-to-end MD5/SHA-256.

## Trạng thái kiểm tra hiện tại

Đọc source và test cho thấy một số parser/session/filesystem unit path đã có,
nhưng RDT production integration, Active/PASV end-to-end, full command lifecycle,
SHA-256 transfer evidence và full pytest suite chưa được xác minh. Xem
`docs/api-contract.md`, `docs/role-b-week-2.md` và
`docs/report-parts/14-requirement-compliance.md` để biết owner/TODO cụ thể.
