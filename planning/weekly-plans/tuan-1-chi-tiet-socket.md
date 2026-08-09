# TUẦN 1 — CHI TIẾT CÔNG VIỆC (26/7 CN → 1/8 Thứ 7)

> **Snapshot lịch sử, không phải trạng thái hiện tại.** Xem
> `docs/project-status.md` và `docs/requirement-checklist.md`.

**Mục tiêu tuần:** Mỗi module chạy được **độc lập**, chưa cần tích hợp với nhau. Cuối tuần mỗi role demo nhanh phần mình cho 2 bạn còn lại.

---

## 🔵 Role A — TCP Control & Session

| Ngày | Việc cụ thể |
|---|---|
| **26/7 (CN)** | Setup TCP server (bind/listen/accept) + TCP client (connect). Đọc lại `Shared Interface Definition` của B (control message format) để thống nhất cách parse — hỏi ngay nếu chưa rõ, đừng tự đoán. |
| **27/7 (Thứ 2)** | Viết parser lệnh (tách command + argument từ chuỗi nhận được). Implement `USER`, `PASS` với đúng reply code (220 service ready, 331 username OK cần password, 230 login successful, 530 not logged in). |
| **28/7 (Thứ 3)** | Implement `QUIT`, `NOOP`. Tạo object/class quản lý session cơ bản (trạng thái đã login hay chưa). |
| **29/7 (Thứ 4)** | Viết unit test cho auth flow: login đúng thứ tự, login sai password, gửi lệnh khi chưa login, gửi lệnh không tồn tại. |
| **30/7 (Thứ 5)** | Bắt đầu vẽ sequence diagram phần TCP (connect → USER → PASS → lệnh → QUIT) vào `docs/report.md`. |
| **31/7 (Thứ 6)** | Buffer — xử lý các vấn đề phát sinh từ buổi review giữa tuần (29/7). |
| **1/8 (Thứ 7)** | Demo cho B & C: connect → login → gửi vài lệnh → reply code đúng → quit. |

**⚠️ Cẩn trọng cho Role A:**
- Reply code phải khớp **chính xác** với bảng 2.3 trong đề — sai code sẽ bị hỏi xoáy lúc vấn đáp.
- Xử lý input dị dạng (lệnh rỗng, thiếu argument, ký tự lạ) mà **không được crash server** — đây là tiêu chí đầu tiên trong rubric ("Fails to compile or crashes" = 0 điểm).
- Session object nên thiết kế đơn giản nhưng **dễ mở rộng** — vì tuần sau C sẽ tích hợp vào server đa luồng, mỗi client cần 1 session riêng biệt.
- Không tự ý đổi format control message đã thống nhất với B — nếu thấy bất hợp lý, trao đổi lại thay vì tự sửa một mình.

---

## 🟠 Role B — UDP Data Channel & RDT

| Ngày | Việc cụ thể |
|---|---|
| **26/7 (CN)** | Hoàn thiện `RDTHeader` (đã định nghĩa lúc khởi công) — viết hàm serialize/deserialize (pack/unpack), test roundtrip đảm bảo dữ liệu không méo. |
| **27/7 (Thứ 2)** | Viết cơ chế chia file thành segment + gửi qua UDP socket. |
| **28/7 (Thứ 3)** | Viết cơ chế nhận + ráp lại file (test với trường hợp lý tưởng — chưa mô phỏng mất gói). |
| **29/7 (Thứ 4)** | Implement Stop-and-Wait: gửi 1 gói → chờ ACK → timeout thì gửi lại. |
| **30/7 (Thứ 5)** | Thêm checksum vào mỗi gói + logic phát hiện gói lỗi (corruption detection). Test bằng cách cố tình làm hỏng 1 gói xem có phát hiện được không. |
| **31/7 (Thứ 6)** | Test mô phỏng mất gói (drop ngẫu nhiên) và gói trùng (duplicate) — đảm bảo retransmit + loại trùng hoạt động đúng. |
| **1/8 (Thứ 7)** | Demo cho A & C: gửi 1 file binary nhỏ qua UDP có mô phỏng mất gói, vẫn nhận được file nguyên vẹn. Bắt đầu viết doc `RDTHeader` ở mức byte/field. |

**⚠️ Cẩn trọng cho Role B:**
- Đây là phần **rủi ro cao nhất** — nếu tuần này trễ, toàn bộ tiến độ tuần 2 (tích hợp) sẽ bị ảnh hưởng. 
- Chú ý **thứ tự byte (endianness)** khi pack/unpack `RDTHeader` — phải nhất quán giữa sender và receiver.
- Đặt **giới hạn số lần retransmit tối đa** — tránh vòng lặp vô hạn nếu mất gói liên tục (server/client phải báo lỗi và dừng, không treo).
- Dùng **socket timeout** khi `recv()` — không được chờ vô thời hạn, nếu không cả chương trình sẽ đứng khi không có phản hồi.
- Test bằng **file binary thật** (ảnh, archive) chứ không chỉ text — vì đây là yêu cầu Advanced tier ("binary file handling without corruption").
- Không tự tiện đổi format `RDTHeader` đã thống nhất lúc khởi công mà không báo A (A cũng cần biết vì liên quan control channel điều phối `PORT`/`PASV`).

---

## 🟢 Role C — File/Concurrency & Integration 

| Ngày | Việc cụ thể |
|---|---|
| **26/7 (CN)** | Viết module đọc/ghi file binary an toàn (test với file ảnh/archive, so sánh byte-by-byte trước/sau để đảm bảo không hỏng dữ liệu). |
| **27/7 (Thứ 2)** | Viết chức năng duyệt cây thư mục lồng nhau (list, tree) + validate path (chặn `../` đi ra ngoài thư mục gốc cho phép). |
| **28/7 (Thứ 3)** | Dựng khung server đa luồng (accept loop, spawn 1 thread/client) — **chỉ cần cấu trúc**, chưa cần logic session đầy đủ. |
| **29/7 (Thứ 4)** | Test khung đa luồng với nhiều kết nối giả lập đồng thời (dummy echo) — kiểm tra không bị race condition/crash khi nhiều client cùng lúc. |
| **30/7 (Thứ 5)** | Bắt đầu thiết kế CLI hiển thị (mock data trước: trạng thái kết nối, tiến trình transfer). |
| **31/7 (Thứ 6)** | Buffer — bắt đầu phác thảo flowchart thread-dispatch vào `docs/report.md`. |
| **1/8 (Thứ 7)** | Chủ trì buổi sync cuối tuần: nghe A & B demo, kiểm tra sơ bộ xem 2 module có khả năng ráp vào nhau tuần sau không (interface có khớp giả định ban đầu chưa). |

**⚠️ Cẩn trọng cho Role C:**
- Validate path kỹ — đây là lỗ hổng bảo mật cổ điển (path traversal); test với input ác ý như `../../etc/passwd`.
- Khi test đa luồng, cẩn thận **race condition** nếu nhiều thread cùng ghi log hoặc cùng truy cập 1 tài nguyên chung — dùng lock/mutex ngay từ đầu, đừng để "chạy được là xong" rồi sửa sau.
- Vì Python dùng GIL, `threading` sẽ không chạy song song thật ở tác vụ CPU-bound — nhưng đồ án này là I/O-bound (socket, đọc/ghi file) nên vẫn ổn; nên **ghi chú lại lý do này vào docs** để trả lời được khi vấn đáp hỏi tại sao chọn threading.

---

## 🔁 Review chéo cả 3 người

### Buổi review giữa tuần — 29/7 (Thứ 4), ~30 phút
Mỗi người đọc code của **1 bạn khác** (xoay vòng: A đọc code B, B đọc code C, C đọc code A), sau đó hỏi trực tiếp người viết (không chỉ chạy thử):
- "Đoạn này xử lý trường hợp X thì ra sao?"
- "Tại sao chọn cách làm này mà không phải cách khác?"
- Kiểm tra người viết có **giải thích được bằng lời**, không lệ thuộc đọc lại code hoặc đọc giải thích của AI.

**Lưu ý khi review — cần đối chiếu với thống nhất ban đầu:**
- A đọc code B: kiểm tra `RDTHeader` implement có đúng field như lúc khởi công thống nhất không.
- B đọc code C: kiểm tra khung đa luồng có chỗ nào sẽ khó nhét session/RDT logic vào tuần sau không.
- C đọc code A: kiểm tra reply code có đúng bảng 2.3 không, session object có dễ mở rộng cho multi-client không.

### Buổi sync cuối tuần — 1/8 (Thứ 7)
- Mỗi role demo 5-10 phút phần mình cho 2 bạn còn lại (không cần hoàn hảo, chỉ cần chạy được phần cốt lõi).
- Cả 3 cùng rà lại: có ai bị trễ tiến độ không, có phần nào cần điều chỉnh scope trước khi vào Tuần 2 (tuần nặng nhất) không.
- Ghi nhận nhanh vào `docs/genai-log-<role>.md` nếu tuần này có dùng AI hỗ trợ — làm ngay, đừng để dồn cuối kỳ.
