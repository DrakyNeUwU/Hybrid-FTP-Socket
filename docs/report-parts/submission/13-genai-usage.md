# 13. GenAI Usage and Refinement

**Trạng thái:** Role C hoàn thành provenance; A/B cần xác nhận phần của mình.
**Owner:** all. **Reviewer:** all.

Role C lưu exact prompt, raw-output summary, manual refinement, affected files
và evidence tại `../../genai-log-c.md`. Log ghi rõ GenAI chỉ hỗ trợ phân tích,
thiết kế và review; mọi thay đổi được kiểm tra lại bằng code review và test thật.

| Hạng mục Role C | Manual refinement | Verification |
|---|---|---|
| Filesystem/concurrency | Giữ filesystem boundary, atomic cleanup và lock ownership rõ ràng | Filesystem/server/E2E tests |
| Go-Back-N/START | Chọn window 4, ACK tích lũy, retry bounded; không đổi header/TCP contract | RDT 27 pass; final full suite 199 pass |
| LAN ACTIVE | Chẩn đoán CP1252 và server-initiated UDP; thêm output-safe/probe behavior | CLI/E2E regression; ACTIVE LAN hash |
| Documentation migration | Đồng bộ evidence vào report parts, status/checklist và changelog | Link/evidence audit |

Final report chỉ được nói GenAI-assisted ở mức có thể giải thích và truy vết
vào logs; không thay thế peer review, ownership hoặc verification độc lập.
