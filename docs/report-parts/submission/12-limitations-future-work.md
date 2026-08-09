# 12. Limitations and Future Work

**Trạng thái:** Cập nhật theo evidence final-week.
**Owner:** all. **Reviewer:** all.

| Item | Trạng thái / impact | Owner | Hành động trước nộp hoặc tiếp theo |
|---|---|---|---|
| `MODE B/C` | Hiện trả `502`; không có data-path/codec được chốt nên không claim support | A/B | Giữ reply trung thực, giải thích limitation trong report/oral |
| RDT wire-contract sign-off | Go-Back-N và START ACK/retry đã có test; B review contract còn pending | B, C review | So khớp header/state machine với `docs/api-contract.md` và ký review |
| Final report | Draft C đã có, nhưng B chưa tổng hợp 7 sections/evidence | B, A/C sign-off | B embed artifacts, A/C review phần kỹ thuật |
| Oral/release hygiene | Chưa có dry-run/sign-off cuối | All | Chạy oral, kiểm tra Git/history, clean-machine/release checklist |

LAN không còn là technical blocker: PASV và ACTIVE hai máy đã pass với SHA-256
khớp. Screenshot ACTIVE server-side chỉ là cải thiện trình bày, không làm thay
đổi kết quả functional. RDT dùng Go-Back-N window cố định 4; future work có thể
đánh giá adaptive congestion/window policy nếu requirement mở rộng.
