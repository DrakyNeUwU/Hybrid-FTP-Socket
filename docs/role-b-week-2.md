# Role B — Week 2 Documentation Template

> Đây là khung thống nhất do nhóm chuẩn bị. Role B tự điền nội dung, trạng thái,
> test và evidence của mình. Không dùng file này để suy đoán thay cho self-report
> của Role B.

**Shared API:** [`api-contract.md`](api-contract.md)  
**Requirement checklist:** [`requirement-checklist.md`](requirement-checklist.md)  
**Trạng thái tài liệu:** `Chưa hoàn thành`

## 1. Phạm vi trách nhiệm

<!-- TODO(Role B): Tự mô tả phạm vi UDP data channel/RDT và ranh giới với A/C. -->

## 2. Requirement của đề liên quan đến Role B

<!-- TODO(Role B): Dẫn RQ-ID và trích yếu requirement mà Role B phụ trách. -->

## 3. Thành phần đã triển khai

<!-- TODO(Role B): Liệt kê module/class/function thật và commit tương ứng. -->

## 4. Thành phần chưa triển khai

<!-- TODO(Role B): Ghi rõ phần còn thiếu; không ghi thành công nếu chưa có evidence. -->

## 5. Blocker hiện tại

<!-- TODO(Role B): Ghi blocker, nguyên nhân, ảnh hưởng và dependency. -->

## 6. Công việc ưu tiên

<!-- TODO(Role B): Sắp xếp task theo thứ tự và owner/reviewer. -->

## 7. Module/file phụ trách

<!-- TODO(Role B): Ghi đường dẫn source/test và symbol phụ trách. -->

## 8. Shared API đang sử dụng

<!-- TODO(Role B): Dẫn tới api-contract.md; không định nghĩa header/signature khác ở đây. -->

## 9. RDT header và serialization

<!-- TODO(Role B): Mô tả byte order, field/flag, serialize/deserialize và trạng thái Existing/Needs change/Proposed. -->

## 10. Sender/receiver state machine

<!-- TODO(Role B): Bổ sung diagram sender và receiver khớp code thật. -->

## 11. Stop-and-Wait, ACK, sequence và checksum

<!-- TODO(Role B): Ghi policy ACK/sequence/checksum và các edge case đã test. -->

## 12. Timeout, retransmission và retry limit

<!-- TODO(Role B): Ghi timeout/retry constants, failure behavior và evidence. -->

## 13. Duplicate, out-of-order và payload-length validation

<!-- TODO(Role B): Ghi cách xử lý và test production-path tương ứng. -->

## 14. Transfer ID, FIN/EOF và ABORT/cancellation

<!-- TODO(Role B): Ghi lifecycle, cancellation signal, socket/worker cleanup và owner. -->

## 15. Active/PASV integration và progress callback

<!-- TODO(Role B): Ghi endpoint/progress contract đã dùng, không tự tạo contract riêng. -->

## 16. Cleanup và thread-safety

<!-- TODO(Role B): Ghi resource owner, cleanup owner, lock và bounded shutdown. -->

## 17. Test bắt buộc

<!-- TODO(Role B): Liệt kê unit, fault-injection, integration, binary/chunk-boundary và timeout tests. -->

## 18. Evidence cần bàn giao

<!-- TODO(Role B): Ghi test command, log path, SHA-256 evidence, diagram và reviewer. -->

## 19. Rủi ro kỹ thuật và dependency với role khác

<!-- TODO(Role B): Nêu dependency với A endpoint/reply/session và C filesystem/cleanup. -->

## 20. Definition of Done của Role B

- [ ] Role B tự xác nhận header/API khớp [`api-contract.md`](api-contract.md).
- [ ] Sender/receiver production path có test reliability và cleanup.
- [ ] Active/PASV adapter, progress, FIN và ABORT có evidence thật.
- [ ] SHA-256/binary evidence được lưu và reviewer xác nhận.

## 21. Self-assessment dựa trên bằng chứng

<!-- TODO(Role B): Role B tự viết self-assessment; không dùng phần trăm nếu chưa có commit/evidence. -->

## 22. Checklist requirement tương ứng

<!-- TODO(Role B): Tick RQ-ID chỉ khi có code/test/evidence; dùng trạng thái chuẩn trong compliance matrix. -->
