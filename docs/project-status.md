# Project Status — Hybrid FTP

**Ngày cập nhật:** 07/08/2026  
**Phạm vi:** kiểm tra Role A và trạng thái tích hợp A/B/C

## Tóm tắt

Role A đã hoàn thành phần lớn TCP control, parser, authentication, session,
filesystem delegation và transfer orchestration. Tuy nhiên, toàn bộ Role A
chưa thể gọi là hoàn thành vì đường truyền UDP/RDT Active/PASV chưa có test
end-to-end và còn cần chốt contract với Role B/C.

## Tiến độ theo nhóm

| Hạng mục | Trạng thái | Ghi chú |
|---|---:|---|
| TCP framing và command parser | 100% | Đã xử lý command bị chia/gộp và UTF-8 lỗi |
| Authentication và session isolation | 100% | Có USER/PASS reset, session riêng |
| FTP command dispatch/reply | 90% | Có command chính; cần thêm lifecycle/integration evidence |
| Filesystem delegation | 90% | Client path đi qua `FilesystemService`; cần test security đầy đủ |
| Transfer orchestration | 85% | Có worker, result, cancel và guard transfer chồng nhau |
| Active/PASV endpoint | 50% | Unit validation có; end-to-end chưa chạy |
| UDP/RDT integration | 40% | Adapter có nhưng production workflow chưa được chứng minh |
| ABOR/disconnect cleanup | 70% | Có cleanup code; thiếu test chờ UDP thật |
| Automated verification | 60% | 52 test Role A pass; full pytest chưa chạy được |
| Demo/evidence/report | 50% | Cần log, hash, concurrent-client và screenshots thật |

## Việc đã làm trong vòng cập nhật này

- Thêm chống chạy nhiều transfer trên cùng một session.
- Khi transfer đang chạy, `RETR`, `STOR`, `STOU`, `APPE` trả mã `450` thay vì
  ghi đè state của worker trước.
- Thêm test cho transfer chồng nhau.
- Ghi lại rõ các phần còn phụ thuộc Role B/C, không đánh dấu pass chỉ dựa trên
  unit test.

## Việc tiếp theo theo owner

### Role A

- Viết integration test cho TCP → TransferManager → UDP → filesystem.
- Chốt lifecycle socket sau transfer và test ABOR/disconnect khi đang chờ UDP.
- Thống nhất data-channel behavior của LIST/NLST.

### Role B

- Chốt peer/transfer validation, FIN/ACK, timeout hữu hạn và fault injection.
- Cung cấp adapter production ổn định theo contract của `TransferManager`.

### Role C

- Xác nhận atomic STOR, APPE lock, STOU unique, path/symlink security và
  multi-client evidence.

## Bằng chứng kiểm tra

- Pass: `python -m unittest tests.test_command_parser tests.test_session tests.test_commands -q`
  — 52 tests.
- Chưa chạy: `python -m pytest -q` vì thiếu dependency `pytest`.
- Chưa xác minh: Active/PASV upload/download thật, SHA-256 end-to-end và
  multi-client UDP transfer.
