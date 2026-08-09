# 12. Limitations and Future Work

**Trạng thái:** Cập nhật theo evidence final-week.
**Owner:** all. **Reviewer:** all.

| Item | Trạng thái / impact | Owner | Hành động trước nộp hoặc tiếp theo |
|---|---|---|---|
| `MODE B/C` | Hiện trả `502`; không có data-path/codec được chốt nên không claim support | A/B | Giữ reply trung thực, giải thích limitation trong report/oral |
| RDT wire contract | Go-Back-N và START ACK/retry có test; B-F01 technical review complete | B/C | Giữ contract/header trace cho oral và final report |
| Final report | Release candidate đã được technical audit; không có claim vượt evidence | B, A/C audit | Chờ contribution decision và Git release check trước nộp |
| Demo evidence | LAN logs/hash và active-session server log đã có; không cần screenshot mới | C, B | Embed log/hash có caption rõ trong report |
| Oral/release hygiene | Oral pack sẵn sàng; dry run không là gate nội bộ | All | Tự chuẩn bị locator; kiểm tra Git/history và clean-machine/release checklist |

LAN không còn là technical blocker: PASV và ACTIVE hai máy đã pass với SHA-256
khớp. Curated server/client logs thay cho screenshot và không làm thay đổi kết
quả functional. RDT dùng Go-Back-N window cố định 4; future work có thể
đánh giá adaptive congestion/window policy nếu requirement mở rộng.
